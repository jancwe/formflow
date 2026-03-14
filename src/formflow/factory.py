import logging
import os
import shutil
from flask import Flask
from pydantic import ValidationError

from ._version import __version__
from .config import AppSettings
from .services.form_engine import FormEngine

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__, static_folder='/app/static')
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

    forms_dir = 'forms'
    pdf_templates_dir = None

    data_dir = settings.data_dir
    if data_dir:
        forms_dir = os.path.join(data_dir, 'forms')

        candidate_pdf_templates = os.path.join(data_dir, 'pdf_templates')
        if os.path.isdir(candidate_pdf_templates):
            pdf_templates_dir = candidate_pdf_templates

        logo_filename = settings.company.logo_filename
        if logo_filename:
            src_logo = os.path.join(data_dir, logo_filename)
            dst_logo = os.path.join(app.static_folder, logo_filename)
            if os.path.isfile(src_logo):
                try:
                    os.makedirs(os.path.dirname(dst_logo), exist_ok=True)
                    shutil.copy2(src_logo, dst_logo)
                    logger.info("Logo kopiert: %s → %s", src_logo, dst_logo)
                except OSError:
                    logger.warning("Logo konnte nicht kopiert werden: %s → %s", src_logo, dst_logo, exc_info=True)
            else:
                logger.debug("Kein Logo gefunden unter %s, Standardlogo wird verwendet.", src_logo)

    # Formular-Engine initialisieren und Konfiguration übergeben
    form_engine = FormEngine(forms_dir=forms_dir, pdf_templates_dir=pdf_templates_dir)
    form_engine.init_app(app)

    return app
