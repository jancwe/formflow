import json
import logging
import os
import uuid
from datetime import date

from flask import Blueprint, Flask, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from ..services.draft_service import collect_form_data, delete_draft, list_drafts, load_draft, save_draft

logger = logging.getLogger(__name__)


def register_routes(app: Flask, engine) -> None:
    """Registriert die Flask-Routen für die FormEngine als Blueprint."""
    bp = Blueprint('main', __name__)

    @bp.route('/')
    def index():
        """Startseite - Weiterleitung zur Formularliste"""
        return redirect(url_for('main.list_forms'))

    @bp.route('/pdf/<filename>')
    def serve_pdf(filename):
        """Stellt PDF-Dateien zur Verfügung"""
        safe_filename = secure_filename(filename)
        return send_from_directory(os.path.abspath('pdfs'), safe_filename)

    @bp.route('/forms')
    def list_forms():
        """Zeigt eine Liste aller verfügbaren Formulare an"""
        drafts = list_drafts('drafts', engine.forms)
        return render_template('form_list.html', forms=engine.forms, drafts=drafts, app_config=engine.config)

    @bp.route('/form/<form_id>', methods=['GET', 'POST'])
    def show_form(form_id: str):
        """Zeigt ein bestimmtes Formular an"""
        if form_id not in engine.forms:
            return "Formular nicht gefunden", 404

        form_def = engine.forms[form_id]
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
                               app_config=engine.config)

    @bp.route('/preview/<form_id>', methods=['POST'])
    def preview_form(form_id: str):
        """Generiert eine Vorschau des ausgefüllten Formulars"""
        # Lazily bereinige verwaiste temp-Dateien (z.B. nach Browser-Abbruch)
        engine._cleanup_temp_files()
        if form_id not in engine.forms:
            return "Formular nicht gefunden", 404

        form_def = engine.forms[form_id]
        form_data = {}

        # Formulardaten sammeln
        for field in form_def.get('fields', []):
            field_name = field.get('name')

            # Bei 'select' mit 'multiple: true' müssen wir getlist() verwenden
            if field.get('type') == 'select' and field.get('multiple'):
                selected_options = request.form.getlist(field_name)
                form_data[field_name] = selected_options
            else:
                form_data[field_name] = request.form.get(field_name, '')

        # PDF generieren
        file_id = uuid.uuid4().hex
        temp_filename = f"pdfs/temp_{file_id}.pdf"
        engine.pdf_generator.generate(form_def, form_data, temp_filename, engine.config)

        return render_template('preview.html',
                               uuid=file_id,
                               form_id=form_id,
                               form_data=form_data,
                               app_config=engine.config)

    @bp.route('/confirm/<form_id>/<file_id>', methods=['POST'])
    def confirm_form(form_id: str, file_id: str):
        """Bestätigt das Formular und speichert das PDF"""
        if form_id not in engine.forms:
            return "Formular nicht gefunden", 404

        form_def = engine.forms[form_id]

        # Erzeuge Dateiname und speichere das PDF (lokal oder SMB)
        filename_parts = engine._generate_filename_parts(form_id, form_def, request.form)
        temp_filename = f"pdfs/temp_{file_id}.pdf"
        final_filename = f"pdfs/{'_'.join(filename_parts)}.pdf"

        if not os.path.exists(temp_filename):
            return "Fehler: Temporäre Datei nicht gefunden.", 400

        try:
            result = engine._store_pdf(temp_filename, final_filename, filename_parts)
            return render_template('success.html',
                                   app_config=engine.config,
                                   warning=result.get('warning'),
                                   filename=result.get('filename'))
        except Exception:
            logger.exception("Fehler beim Speichern des PDFs")
            return "Interner Serverfehler beim Speichern des PDFs.", 500

    @bp.route('/edit/<form_id>/<file_id>', methods=['POST'])
    def edit_form(form_id: str, file_id: str):
        """Zurück zum Bearbeiten des Formulars mit vorausgefüllten Daten"""
        if form_id not in engine.forms:
            return "Formular nicht gefunden", 404

        temp_filename = f"pdfs/temp_{file_id}.pdf"
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        form_def = engine.forms[form_id]

        # Standardwerte setzen (wie in show_form)
        for field in form_def.get('fields', []):
            if field.get('type') == 'date' and field.get('default') == 'today':
                field['default_value'] = date.today().isoformat()

        return render_template('dynamic_form.html',
                               form=form_def,
                               data=request.form,
                               date_today=date.today().isoformat(),
                               app_config=engine.config)

    @bp.route('/draft/<form_id>', methods=['POST'])
    def save_draft_route(form_id: str):
        """Speichert Formulardaten als Entwurf"""
        if form_id not in engine.forms:
            return "Formular nicht gefunden", 404

        form_def = engine.forms[form_id]
        form_data = collect_form_data(form_def, request.form)
        save_draft('drafts', form_id, form_data)
        return redirect(url_for('main.list_forms'))

    @bp.route('/draft/<form_id>/<draft_id>/load', methods=['GET'])
    def load_draft_route(form_id: str, draft_id: str):
        """Lädt einen Entwurf und öffnet das Formular vorausgefüllt"""
        try:
            draft = load_draft('drafts', draft_id)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"Entwurf {draft_id} konnte nicht geladen werden.")
            return redirect(url_for('main.list_forms'))

        delete_draft('drafts', draft_id)

        if form_id not in engine.forms:
            return "Formular nicht gefunden", 404

        form_def = engine.forms[form_id]
        data = draft.get('form_data', {})

        for field in form_def.get('fields', []):
            if field.get('type') == 'date' and field.get('default') == 'today':
                field['default_value'] = date.today().isoformat()

        return render_template('dynamic_form.html',
                               form=form_def,
                               data=data,
                               date_today=date.today().isoformat(),
                               app_config=engine.config)

    @bp.route('/draft/<draft_id>/delete', methods=['POST'])
    def delete_draft_route(draft_id: str):
        """Löscht einen Entwurf"""
        delete_draft('drafts', draft_id)
        return redirect(url_for('main.list_forms'))

    app.register_blueprint(bp)
