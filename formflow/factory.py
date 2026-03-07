from flask import Flask
from pydantic import ValidationError

from ._version import __version__
from .config import AppSettings
from .form_engine import FormEngine

def create_app():
    app = Flask(__name__)
    app.config["VERSION"] = __version__

    try:
        # Load settings from environment and store them in the app config
        settings = AppSettings()
        app.config["formflow"] = settings.model_dump()
    except ValidationError as e:
        error_details = "\n".join(
            f"- APP_{'__'.join(str(loc) for loc in err['loc']).upper()}: {err['msg']}"
            for err in e.errors()
        )
        raise RuntimeError(
            f"Konfigurationsfehler – folgende Umgebungsvariablen fehlen oder sind ungültig:\n{error_details}"
        ) from e

    # Formular-Engine initialisieren und Konfiguration übergeben
    form_engine = FormEngine()
    form_engine.init_app(app)

    return app
