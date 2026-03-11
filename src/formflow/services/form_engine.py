import logging
import os
import re
from datetime import datetime
from typing import Any

import yaml
from flask import Flask, current_app

from ..routes.main import register_routes
from .pdf_generator import PdfGenerator
from .storage import PdfStorage

# Logger konfigurieren
logger = logging.getLogger(__name__)


class FormEngine:
    def __init__(self, forms_dir: str = "forms", config: dict[str, Any] | None = None):
        self.forms_dir = forms_dir
        self._config = config
        self.forms: dict[str, Any] = {}
        self.pdf_generator = PdfGenerator()
        self._storage = PdfStorage()
        self._load_forms()

    @property
    def _smb_session_registered(self) -> bool:
        return self._storage._smb_session_registered

    @_smb_session_registered.setter
    def _smb_session_registered(self, value: bool) -> None:
        self._storage._smb_session_registered = value

    @property
    def config(self) -> dict[str, Any]:
        if self._config is not None:
            return self._config
        return current_app.config.get("formflow", {})

    @config.setter
    def config(self, value: dict[str, Any]) -> None:
        self._config = value

    def init_app(self, app: Flask):
        self.app = app
        # Make sure the pdfs directory exists
        os.makedirs("pdfs", exist_ok=True)
        # Make sure the drafts directory exists
        os.makedirs("drafts", exist_ok=True)
        # Bereinige verwaiste temp-Dateien von vorherigen Läufen beim Start
        self._cleanup_temp_files()
        self._register_routes()

    def _load_forms(self) -> None:
        """Lädt alle YAML-Formulardefinitionen aus dem forms-Verzeichnis"""
        if not os.path.exists(self.forms_dir):
            os.makedirs(self.forms_dir)

        logger.info(f"Lade Formulare aus Verzeichnis: {self.forms_dir}")
        sorted_files = sorted(os.listdir(self.forms_dir))
        logger.info(f"Gefundene Dateien: {sorted_files}")

        for filename in sorted_files:
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                form_path = os.path.join(self.forms_dir, filename)
                try:
                    with open(form_path) as file:
                        form_def = yaml.safe_load(file)
                        form_id = form_def.get("form_id", os.path.splitext(filename)[0])
                        self.forms[form_id] = form_def
                        logger.info(f"Formular geladen: {form_id} aus {filename}")
                except Exception as e:
                    logger.error(f"Fehler beim Laden von {filename}: {str(e)}")

        logger.info(f"Insgesamt {len(self.forms)} Formulare geladen: {list(self.forms.keys())}")

    def _register_routes(self) -> None:
        """Registriert die Flask-Routen."""
        register_routes(self.app, self)

    # --- Hilfsfunktionen --------------------------------------------------
    def _cleanup_temp_files(self, max_age_seconds: int = 3600) -> None:
        """Delegates to PdfStorage.cleanup_temp_files()."""
        self._storage.cleanup_temp_files(max_age_seconds)

    def _sanitize_for_filename(self, value: str) -> str:
        """Bereinigt Text, sodass er in einem Dateinamen verwendet werden kann."""
        clean = value.replace(" ", "_")
        return re.sub(r"[^a-zA-Z0-9_-]", "", clean)

    def _generate_filename_parts(self, form_id: str, form_def: dict[str, Any], form_data: dict[str, Any]) -> list[str]:
        parts = [datetime.now().strftime("%Y-%m-%d_%H-%M"), form_id]
        for field in form_def.get("fields", []):
            if field.get("in_filename"):
                name = field.get("name")
                value = form_data.get(name, "")
                if value:
                    cleaned = self._sanitize_for_filename(value)
                    if cleaned:
                        parts.append(cleaned)
        return parts

    def _store_pdf(self, temp_path: str, local_final: str, filename_parts: list[str]) -> dict:
        """Delegates to PdfStorage.store_pdf()."""
        return self._storage.store_pdf(temp_path, local_final, filename_parts, self.config)
