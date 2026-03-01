import os
import logging
import re
from datetime import date
from typing import Dict, Any
from flask import render_template, request, redirect, url_for, Flask, send_from_directory
import uuid
import time
import smbclient
from pdf_generator import PdfGenerator
import yaml

# Logger konfigurieren
logger = logging.getLogger(__name__)



from flask import current_app, render_template, request, redirect, url_for, Flask, send_from_directory

class FormEngine:
    def __init__(self, forms_dir: str = 'forms'):
        self.forms_dir = forms_dir
        self.forms: Dict[str, Any] = {}
        self.pdf_generator = PdfGenerator()
        self._load_forms()

    @property
    def config(self) -> Dict[str, Any]:
        return current_app.config.get("formflow", {})

    def init_app(self, app: Flask):
        self.app = app
        # Make sure the pdfs directory exists
        os.makedirs('pdfs', exist_ok=True)
        self._register_routes()

        
    
    def _load_forms(self) -> None:
        """Lädt alle YAML-Formulardefinitionen aus dem forms-Verzeichnis"""
        if not os.path.exists(self.forms_dir):
            os.makedirs(self.forms_dir)
            
        logger.info(f"Lade Formulare aus Verzeichnis: {self.forms_dir}")
        logger.info(f"Gefundene Dateien: {os.listdir(self.forms_dir)}")
        
        for filename in os.listdir(self.forms_dir):
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
        print(f"DEBUG: Geladene Formulare: {list(self.forms.keys())}")
    
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
            return render_template('form_list.html', forms=self.forms, app_config=self.config)
        
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
                # SMB-Logik ist ausgelagert, Methode behandelt Fallback selbst
                self._store_pdf(temp_filename, final_filename, filename_parts)
                return render_template('success.html', app_config=self.config)
            except Exception as e:
                logger.exception("Fehler beim Speichern des PDFs")
                return str(e), 500
        
        @self.app.route('/edit/<form_id>/<file_id>', methods=['POST'])
        def edit_form(form_id: str, file_id: str):
            """Zurück zum Bearbeiten des Formulars"""
            if form_id not in self.forms:
                return "Formular nicht gefunden", 404

            temp_filename = f"pdfs/temp_{file_id}.pdf"
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

            return redirect(url_for('show_form', form_id=form_id))

        @self.app.route('/hello')
        def hello():
            return "Hello, World!"

    # --- Hilfsfunktionen --------------------------------------------------
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

    def _store_pdf(self, temp_path: str, local_final: str, filename_parts: list[str]) -> None:
        """Speichert ein PDF entweder lokal oder auf dem SMB-Share.

        Wenn SMB deaktiviert ist, wird einfach umbenannt. Bei Netzwerk-Problemen
        wird eine Exception geworfen.
        """
        smb_config = self.config.get('smb', {})
        if not smb_config.get('enabled'):
            logger.info("SMB ist deaktiviert. Speichere PDF lokal.")
            os.rename(temp_path, local_final)
            return

        logger.info("SMB ist aktiviert. Versuche Upload.")

        server = smb_config.get('server')
        share = smb_config.get('share')
        folder = smb_config.get('folder', '')
        username = smb_config.get('username')
        password = smb_config.get('password')

        if not (server and share and username and password):
            raise RuntimeError("SMB ist aktiviert, aber Zugangsdaten/Pfade fehlen.")

        smbclient.register_session(server, username=username, password=password)
        folder_part = f"\\{folder}" if folder else ""
        remote_path = fr"\\{server}\{share}{folder_part}\{'_'.join(filename_parts)}.pdf"

        with open(temp_path, 'rb') as local_file:
            with smbclient.open_file(remote_path, mode='wb') as remote_file:
                remote_file.write(local_file.read())

        logger.info(f"PDF erfolgreich auf SMB-Share gespeichert: {remote_path}")
        os.remove(temp_path)
