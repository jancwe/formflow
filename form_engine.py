import yaml
import os
import logging
from datetime import date
from flask import render_template, request, redirect, url_for
from fpdf import FPDF
import base64
import uuid
import time

# Logger konfigurieren
logger = logging.getLogger(__name__)

class FormEngine:
    def __init__(self, app, forms_dir='forms'):
        self.app = app
        self.forms_dir = forms_dir
        self.forms = {}
        self._load_forms()
        self._register_routes()
    
    def _load_forms(self):
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
    
    def _register_routes(self):
        """Registriert die Flask-Routen für jedes Formular"""
        
        @self.app.route('/forms')
        def list_forms():
            """Zeigt eine Liste aller verfügbaren Formulare an"""
            # Formulare neu laden, um Änderungen zu erkennen
            self._load_forms()
            return render_template('form_list.html', forms=self.forms)
        
        @self.app.route('/form/<form_id>', methods=['GET', 'POST'])
        def show_form(form_id):
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
                                  date_today=date.today().isoformat())
        
        @self.app.route('/preview/<form_id>', methods=['POST'])
        def preview_form(form_id):
            """Generiert eine Vorschau des ausgefüllten Formulars"""
            if form_id not in self.forms:
                return "Formular nicht gefunden", 404
                
            form_def = self.forms[form_id]
            form_data = {}
            
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
            pdf = self._generate_pdf(form_def, form_data)
            
            # Eindeutige ID für das temporäre PDF
            file_id = uuid.uuid4().hex
            temp_filename = f"pdfs/temp_{file_id}.pdf"
            pdf.output(temp_filename)
            
            return render_template('preview.html',
                                  uuid=file_id,
                                  form_id=form_id,
                                  form_data=form_data)
        
        @self.app.route('/confirm/<form_id>/<file_id>', methods=['POST'])
        def confirm_form(form_id, file_id):
            """Bestätigt das Formular und speichert das PDF"""
            if form_id not in self.forms:
                return "Formular nicht gefunden", 404
                
            form_def = self.forms[form_id]
            
            # Benutzernamen für den Dateinamen verwenden
            user = request.form.get('user', 'unbekannt')
            temp_filename = f"pdfs/temp_{file_id}.pdf"
            final_filename = f"pdfs/{form_id}_{user.replace(' ', '_')}_{int(time.time())}.pdf"
            
            if os.path.exists(temp_filename):
                os.rename(temp_filename, final_filename)
                return render_template('success.html')
            
            return "Fehler: Temporäre Datei nicht gefunden.", 400
        
        @self.app.route('/edit/<form_id>/<file_id>', methods=['POST'])
        def edit_form(form_id, file_id):
            """Zurück zum Bearbeiten des Formulars"""
            if form_id not in self.forms:
                return "Formular nicht gefunden", 404
                
            temp_filename = f"pdfs/temp_{file_id}.pdf"
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            
            return redirect(url_for('show_form', form_id=form_id))
    
    def _generate_pdf(self, form_def, form_data):
        """Generiert ein PDF basierend auf der Formulardefinition und den Daten"""
        pdf = FPDF()
        pdf.add_page()
        
        # Titel
        pdf.set_font("helvetica", style="B", size=16)
        pdf.cell(0, 10, text=form_def.get('pdf', {}).get('title', form_def.get('title', '')), 
                new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(10)
        
        # Felder
        pdf.set_font("helvetica", size=12)
        for field_def in form_def.get('pdf', {}).get('fields', []):
            field_name = field_def.get('field')
            field_label = field_def.get('label', field_name)
            field_type = field_def.get('type', 'text')
            
            if field_type == 'image' and field_name == 'signature':
                # Unterschrift
                pdf.cell(0, 10, text=f"{field_label}:", new_x="LMARGIN", new_y="NEXT")
                signature_data = form_data.get(field_name, '')
                
                if signature_data:
                    header, encoded = signature_data.split(",", 1)
                    temp_sig_filename = f"temp_sig_{uuid.uuid4().hex}.png"
                    with open(temp_sig_filename, "wb") as fh:
                        fh.write(base64.b64decode(encoded))
                    pdf.image(temp_sig_filename, x=10, y=pdf.get_y(), w=field_def.get('width', 80))
                    os.remove(temp_sig_filename)
            else:
                # Normales Textfeld
                value = form_data.get(field_name, '')
                pdf.cell(0, 10, text=f"{field_label}: {value}", new_x="LMARGIN", new_y="NEXT")
        
        return pdf