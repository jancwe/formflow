from flask import Flask
from form_engine import FormEngine
from pydantic import ValidationError
from config import AppSettings

def create_app():
    app = Flask(__name__)

    try:
        # Load settings from environment and store them in the app config
        settings = AppSettings()
        app.config["formflow"] = settings.model_dump()
    except ValidationError as e:
        # Print a user-friendly error message and exit
        print("!!! Konfigurationsfehler !!!")
        print("Die folgenden Umgebungsvariablen fehlen oder sind ungültig:")
        for error in e.errors():
            var_name = "APP_" + "__".join(error['loc']).upper()
            print(f"- {var_name}: {error['msg']}")
        exit(1)

    # Formular-Engine initialisieren und Konfiguration übergeben
    form_engine = FormEngine()
    form_engine.init_app(app)

    return app
