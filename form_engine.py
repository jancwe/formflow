import glob
import json
import os
import logging
import re
import time
import uuid
from datetime import date
from typing import Dict, Any, Optional
import yaml
from flask import current_app, render_template, request, redirect, url_for, Flask, send_from_directory
from pdf_generator import PdfGenerator
from services import collect_form_data, save_draft, load_draft, list_drafts, delete_draft

# Logger konfigurieren
logger = logging.getLogger(__name__)

class FormEngine:
    def __init__(self, forms_dir: str = 'forms', config: Optional[Dict[str, Any]] = None):
        self.forms_dir = forms_dir
        self._config = config
        self.forms: Dict[str, Any] = {}
        self.pdf_generator = PdfGenerator()
        # SMB session is registered lazily on first use and reused for subsequent uploads.
        self._smb_session_registered: bool = False
        self._load_forms()

    @property
    def config(self) -> Dict[str, Any]:
        if self._config is not None:
            return self._config
        return current_app.config.get("formflow", {})

    @config.setter
    def config(self, value: Dict[str, Any]) -> None:
        self._config = value

    def init_app(self, app: Flask):
        self.app = app
        # Make sure the pdfs directory exists
        os.makedirs('pdfs', exist_ok=True)
        # Make sure the drafts directory exists
        os.makedirs('drafts', exist_ok=True)
        # Bereinige verwaiste temp-Dateien von vorherigen Läufen beim Start
        self._cleanup_temp_files()
        self._register_routes()

        
    
    def _load_forms(self) -> None:
        """Lädt alle YAML-Formulardefinitionen aus dem forms-Verzeichnis"""
        if not os.path.exists(self.forms_dir):
            os.makedirs(self.forms_dir)
            
        logger.info(f"Lade Formulare aus Verzeichnis: {self.forms_dir}")
        sorted_files = sorted(os.listdir(self.forms_dir))
        logger.info(f"Gefundene Dateien: {sorted_files}")
        
        for filename in sorted_files:
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                form_path = os.path.join(self.forms_dir, filename)
                try:
                    with open(form_path, 'r') as file:
                        form_def = yaml.safe_load(file)
                        form_id = form_def.get('form_id', os.path.splitext(filename)[0])
                        self.forms[form_id] = form_def
                        logger.info(f"Formular geladen: {form_id} aus {filename}")
                except Exception as e:
                    logger.error(f"Fehler beim Laden von {filename}: {str(e)}")
        
        logger.info(f"Insgesamt {len(self.forms)} Formulare geladen: {list(self.forms.keys())}")
    
    def _register_routes(self) -> None:
        """Registriert die Flask-Routen für jedes Formular"""
        
        @self.app.route('/')
        def index():
            """Startseite - Weiterleitung zur Formularliste"""
            return redirect(url_for('list_forms'))

        @self.app.route('/pdf/<filename>')
        def serve_pdf(filename):
            """Stellt PDF-Dateien zur Verfügung"""
            return send_from_directory('pdfs', filename)
        
        @self.app.route('/forms')
        def list_forms():
            """Zeigt eine Liste aller verfügbaren Formulare an"""
            drafts = list_drafts('drafts', self.forms)
            return render_template('form_list.html', forms=self.forms, drafts=drafts, app_config=self.config)
        
        @self.app.route('/form/<form_id>', methods=['GET', 'POST'])
        def show_form(form_id: str):
            """Zeigt ein bestimmtes Formular an"""
            if form_id not in self.forms:
                return "Formular nicht gefunden", 404
                
            form_def = self.forms[form_id]
            data = {}
            
            if request.method == 'POST':
                data = request.form
            
            # Standardwerte setzen
            for field in form_def.get('fields', []):
                if field.get('type') == 'date' and field.get('default') == 'today':
                    field['default_value'] = date.today().isoformat()
            
            return render_template('dynamic_form.html', 
                                  form=form_def, 
                                  data=data, 
                                  date_today=date.today().isoformat(),
                                  app_config=self.config)
        
        @self.app.route('/preview/<form_id>', methods=['POST'])
        def preview_form(form_id: str):
            """Generiert eine Vorschau des ausgefüllten Formulars"""
            # Lazily bereinige verwaiste temp-Dateien (z.B. nach Browser-Abbruch)
            self._cleanup_temp_files()
            if form_id not in self.forms:
                return "Formular nicht gefunden", 404
                
            form_def = self.forms[form_id]
            form_data: Dict[str, Any] = {}
            
            # Formulardaten sammeln
            for field in form_def.get('fields', []):
                field_name = field.get('name')
                
                # Bei 'select' mit 'multiple: true' müssen wir getlist() verwenden
                if field.get('type') == 'select' and field.get('multiple'):
                    selected_options = request.form.getlist(field_name)
                    form_data[field_name] = ", ".join(selected_options)
                else:
                    form_data[field_name] = request.form.get(field_name, '')
            
            # PDF generieren
            file_id = uuid.uuid4().hex
            temp_filename = f"pdfs/temp_{file_id}.pdf"
            self.pdf_generator.generate(form_def, form_data, temp_filename, self.config)
            
            return render_template('preview.html',
                                  uuid=file_id,
                                  form_id=form_id,
                                  form_data=form_data,
                                  app_config=self.config)
        
        @self.app.route('/confirm/<form_id>/<file_id>', methods=['POST'])
        def confirm_form(form_id: str, file_id: str):
            """Bestätigt das Formular und speichert das PDF"""
            if form_id not in self.forms:
                return "Formular nicht gefunden", 404
                
            form_def = self.forms[form_id]
            
            # Erzeuge Dateiname und speichere das PDF (lokal oder SMB)
            filename_parts = self._generate_filename_parts(form_id, form_def, request.form)
            temp_filename = f"pdfs/temp_{file_id}.pdf"
            final_filename = f"pdfs/{'_'.join(filename_parts)}.pdf"

            if not os.path.exists(temp_filename):
                return "Fehler: Temporäre Datei nicht gefunden.", 400

            try:
                result = self._store_pdf(temp_filename, final_filename, filename_parts)
                return render_template('success.html',
                                       app_config=self.config,
                                       warning=result.get('warning'),
                                       filename=result.get('filename'))
            except Exception:
                logger.exception("Fehler beim Speichern des PDFs")
                return "Interner Serverfehler beim Speichern des PDFs.", 500
        
        @self.app.route('/edit/<form_id>/<file_id>', methods=['POST'])
        def edit_form(form_id: str, file_id: str):
            """Zurück zum Bearbeiten des Formulars"""
            if form_id not in self.forms:
                return "Formular nicht gefunden", 404

            temp_filename = f"pdfs/temp_{file_id}.pdf"
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

            return redirect(url_for('show_form', form_id=form_id))

        @self.app.route('/draft/<form_id>', methods=['POST'])
        def save_draft_route(form_id: str):
            """Speichert Formulardaten als Entwurf"""
            if form_id not in self.forms:
                return "Formular nicht gefunden", 404

            form_def = self.forms[form_id]
            form_data = collect_form_data(form_def, request.form)
            save_draft('drafts', form_id, form_data)
            return redirect(url_for('list_forms'))

        @self.app.route('/draft/<form_id>/<draft_id>/load', methods=['GET'])
        def load_draft_route(form_id: str, draft_id: str):
            """Lädt einen Entwurf und öffnet das Formular vorausgefüllt"""
            try:
                draft = load_draft('drafts', draft_id)
            except (FileNotFoundError, json.JSONDecodeError):
                logger.warning(f"Entwurf {draft_id} konnte nicht geladen werden.")
                return redirect(url_for('list_forms'))

            delete_draft('drafts', draft_id)

            if form_id not in self.forms:
                return "Formular nicht gefunden", 404

            form_def = self.forms[form_id]
            data = draft.get('form_data', {})

            for field in form_def.get('fields', []):
                if field.get('type') == 'date' and field.get('default') == 'today':
                    field['default_value'] = date.today().isoformat()

            return render_template('dynamic_form.html',
                                   form=form_def,
                                   data=data,
                                   date_today=date.today().isoformat(),
                                   app_config=self.config)

        @self.app.route('/draft/<draft_id>/delete', methods=['POST'])
        def delete_draft_route(draft_id: str):
            """Löscht einen Entwurf"""
            delete_draft('drafts', draft_id)
            return redirect(url_for('list_forms'))

    # --- Hilfsfunktionen --------------------------------------------------
    def _cleanup_temp_files(self, max_age_seconds: int = 3600) -> None:
        """Löscht verwaiste temporäre PDFs, die älter als max_age_seconds sind.

        Notwendig, da temp_*.pdf-Dateien bei Browser-Abbrüchen oder Session-Timeouts
        nie bereinigt werden und den Disk-Speicher des Hosts erschöpfen können.
        """
        now = time.time()
        cleaned = 0
        for path in glob.glob("pdfs/temp_*.pdf"):
            try:
                if now - os.path.getmtime(path) > max_age_seconds:
                    os.remove(path)
                    logger.info(f"Verwaiste temp-Datei gelöscht: {path}")
                    cleaned += 1
            except OSError as e:
                logger.warning(f"Konnte temp-Datei nicht löschen {path}: {e}")
        if cleaned:
            logger.info(f"Cleanup: {cleaned} verwaiste temp-Datei(en) gelöscht.")

    def _sanitize_for_filename(self, value: str) -> str:
        """Bereinigt Text, sodass er in einem Dateinamen verwendet werden kann."""
        clean = value.replace(' ', '_')
        return re.sub(r'[^a-zA-Z0-9_-]', '', clean)

    def _generate_filename_parts(self, form_id: str, form_def: Dict[str, Any], form_data: Dict[str, Any]) -> list[str]:
        parts = [form_id]
        for field in form_def.get('fields', []):
            if field.get('in_filename'):
                name = field.get('name')
                value = form_data.get(name, '')
                if value:
                    cleaned = self._sanitize_for_filename(value)
                    if cleaned:
                        parts.append(cleaned)
        parts.append(str(int(time.time())))
        return parts

    def _store_pdf(self, temp_path: str, local_final: str, filename_parts: list[str]) -> dict:
        """Speichert ein PDF entweder lokal oder auf dem SMB-Share.

        Wenn SMB deaktiviert ist, wird einfach umbenannt.
        Bei Netzwerk-Problemen wird lokal gespeichert und eine Warnung zurückgegeben.

        Returns:
            dict mit 'stored_via' ('smb' oder 'local') und optional 'warning'.
        """
        smb_config = self.config.get('smb', {})
        if not smb_config.get('enabled'):
            logger.info("SMB ist deaktiviert. Speichere PDF lokal.")
            os.rename(temp_path, local_final)
            return {"stored_via": "local", "filename": os.path.basename(local_final)}

        # Lazy import: only load smbprotocol when SMB is actually used
        import smbclient  # noqa: PLC0415

        logger.info("SMB ist aktiviert. Versuche Upload.")

        server = smb_config.get('server')
        share = smb_config.get('share')
        folder = smb_config.get('folder', '')
        username = smb_config.get('username')
        password = smb_config.get('password')

        if not (server and share and username and password):
            raise RuntimeError("SMB ist aktiviert, aber Zugangsdaten/Pfade fehlen.")

        try:
            # Register the SMB session lazily on first use; skip if already registered.
            if not self._smb_session_registered:
                smbclient.register_session(server, username=username, password=password)
                self._smb_session_registered = True

            folder_part = f"\\{folder}" if folder else ""
            remote_path = fr"\\{server}\{share}{folder_part}\{'_'.join(filename_parts)}.pdf"

            try:
                with open(temp_path, 'rb') as local_file:
                    with smbclient.open_file(remote_path, mode='wb') as remote_file:
                        remote_file.write(local_file.read())
            except Exception:
                # Session may have expired or been disconnected; attempt to re-register once.
                logger.info("SMB-Verbindung unterbrochen oder Session abgelaufen. Versuche erneute Session-Registrierung.")
                self._smb_session_registered = False
                smbclient.register_session(server, username=username, password=password)
                self._smb_session_registered = True
                with open(temp_path, 'rb') as local_file:
                    with smbclient.open_file(remote_path, mode='wb') as remote_file:
                        remote_file.write(local_file.read())

            logger.info(f"PDF erfolgreich auf SMB-Share gespeichert: {remote_path}")
            os.remove(temp_path)
            return {"stored_via": "smb", "filename": os.path.basename(remote_path)}
        except Exception as e:
            logger.warning(f"SMB-Upload fehlgeschlagen ({e}). Speichere PDF lokal als Fallback.")
            os.rename(temp_path, local_final)
            local_name = os.path.basename(local_final)
            return {
                "stored_via": "local",
                "filename": local_name,
                "warning": f"Der SMB-Server konnte nicht erreicht werden. Die Datei wurde lokal gespeichert unter: {local_name}"
            }
