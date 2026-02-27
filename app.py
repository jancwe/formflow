from flask import Flask, render_template, send_from_directory, request
import os
from form_engine import FormEngine
import logging

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
os.makedirs('pdfs', exist_ok=True)

# Formular-Engine initialisieren
form_engine = FormEngine(app)

@app.route('/')
def index():
    """Startseite - Weiterleitung zur Formularliste"""
    # Formulare neu laden, um Änderungen zu erkennen
    form_engine._load_forms()
    
    # Debug-Ausgabe
    print("Verfügbare Formulare:", list(form_engine.forms.keys()))
    
    return render_template('form_list.html', forms=form_engine.forms)

@app.route('/pdf/<filename>')
def serve_pdf(filename):
    """Stellt PDF-Dateien zur Verfügung"""
    return send_from_directory('pdfs', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
