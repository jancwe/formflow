import yaml
import os
import logging
import re
from datetime import date
from typing import Dict, Any
from flask import render_template, request, redirect, url_for, Flask
import uuid
import time
from pdf_generator import PdfGenerator

# Logger konfigurieren
logger = logging.getLogger(__name__)

class FormEngine:
    def __init__(self, app: Flask, forms_dir: str = 'forms', config_file: str = 'config.yaml'):
        self.app = app
        self.forms_dir = forms_dir
        self.config_file = config_file
        self.forms: Dict[str, Any] = {}
        self.config: Dict[str, Any] = {}
        self.pdf_generator = PdfGenerator()
        self._load_config()
        self._load_forms()
        self._register_routes()
        
    def _load_config(self) -> None:
        """Lädt die globale Konfiguration (z.B. CI-Farben, Firmenname)"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as file:
                    self.config = yaml.safe_load(file) or {}
                logger.info(f"Konfiguration aus {self.config_file} geladen.")
            except Exception as e:
                logger.error(f"Fehler beim Laden der Konfiguration: {str(e)}")
        else:
            logger.warning(f"Konfigurationsdatei {self.config_file} nicht gefunden. Verwende Standardwerte.")
    
    def _load_forms(self) -> None:
        """Lädt alle YAML-Formulardefinitionen aus dem forms-Verzeichnis"""
        if not os.path.exists(self.forms_dir):
            os.makedirs(self.forms_dir)
            
        # Formulare bei jedem Aufruf neu laden
        self.forms = {}
        
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
    
    def _register_routes(self) -> None:
        """Registriert die Flask-Routen für jedes Formular"""
        
        @self.app.route('/forms')
        def list_forms():
            """Zeigt eine Liste aller verfügbaren Formulare an"""
            # Formulare neu laden, um Änderungen zu erkennen
            self._load_forms()
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
            
            # Dateinamen aus den markierten Feldern generieren
            filename_parts = [form_id]
            
            for field in form_def.get('fields', []):
                if field.get('in_filename'):
                    field_name = field.get('name')
                    value = request.form.get(field_name, '')
                    if value:
                        # Ersetze Leerzeichen durch Unterstriche
                        clean_value = value.replace(' ', '_')
                        # Entferne alle Zeichen, die nicht alphanumerisch, Bindestrich oder Unterstrich sind
                        # Das schützt vor problematischen Zeichen in Windows (\ / : * ? " < > |) und Linux
                        clean_value = re.sub(r'[^a-zA-Z0-9_-]', '', clean_value)
                        
                        if clean_value: # Nur hinzufügen, wenn nach der Bereinigung noch etwas übrig ist
                            filename_parts.append(clean_value)
            
            # Zeitstempel anhängen, um Eindeutigkeit zu garantieren
            filename_parts.append(str(int(time.time())))
            
            temp_filename = f"pdfs/temp_{file_id}.pdf"
            final_filename = f"pdfs/{'_'.join(filename_parts)}.pdf"
            
            if os.path.exists(temp_filename):
                os.rename(temp_filename, final_filename)
                return render_template('success.html', app_config=self.config)
            
            return "Fehler: Temporäre Datei nicht gefunden.", 400
        
        @self.app.route('/edit/<form_id>/<file_id>', methods=['POST'])
        def edit_form(form_id: str, file_id: str):
            """Zurück zum Bearbeiten des Formulars"""
            if form_id not in self.forms:
                return "Formular nicht gefunden", 404
                
            temp_filename = f"pdfs/temp_{file_id}.pdf"
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            
            return redirect(url_for('show_form', form_id=form_id))