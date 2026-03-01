from flask import Flask
from form_engine import FormEngine

def create_app():
    app = Flask(__name__)

    # Formular-Engine initialisieren und Routen registrieren
    form_engine = FormEngine()
    form_engine.init_app(app)

    return app
