import yaml
import os
import logging
import re
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
        
        # Titel (aus form_def.title oder form_def.pdf.title für Abwärtskompatibilität)
        pdf_title = form_def.get('pdf', {}).get('title', form_def.get('title', 'Formular'))
        
        pdf.set_font("helvetica", style="B", size=16)
        pdf.cell(0, 10, text=pdf_title, new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(10)
        
        # Felder direkt aus der 'fields'-Definition lesen
        pdf.set_font("helvetica", size=12)
        for field_def in form_def.get('fields', []):
            field_name = field_def.get('name')
            field_label = field_def.get('label', field_name)
            field_type = field_def.get('type', 'text')
            
            if field_type == 'signature':
                # Unterschrift
                pdf.cell(0, 10, text=f"{field_label}:", new_x="LMARGIN", new_y="NEXT")
                signature_data = form_data.get(field_name, '')
                
                if signature_data:
                    header, encoded = signature_data.split(",", 1)
                    temp_sig_filename = f"temp_sig_{uuid.uuid4().hex}.png"
                    with open(temp_sig_filename, "wb") as fh:
                        fh.write(base64.b64decode(encoded))
                    # Breite aus der alten pdf-Definition übernehmen, falls vorhanden, sonst Standard 80
                    width = 80
                    if 'pdf' in form_def and 'fields' in form_def['pdf']:
                        for pdf_field in form_def['pdf']['fields']:
                            if pdf_field.get('field') == field_name:
                                width = pdf_field.get('width', 80)
                                break
                    
                    pdf.image(temp_sig_filename, x=10, y=pdf.get_y(), w=width)
                    os.remove(temp_sig_filename)
            else:
                # Normales Textfeld, Datum, Select etc.
                value = form_data.get(field_name, '')
                pdf.cell(0, 10, text=f"{field_label}: {value}", new_x="LMARGIN", new_y="NEXT")
        
        return pdf