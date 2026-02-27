from flask import Flask, render_template, send_from_directory
import os
from form_engine import FormEngine

app = Flask(__name__)
os.makedirs('pdfs', exist_ok=True)

# Formular-Engine initialisieren
form_engine = FormEngine(app)

@app.route('/')
def index():
    """Startseite - Weiterleitung zur Formularliste"""
    return render_template('form_list.html', forms=form_engine.forms)

@app.route('/pdf/<filename>')
def serve_pdf(filename):
    """Stellt PDF-Dateien zur Verfügung"""
    return send_from_directory('pdfs', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
