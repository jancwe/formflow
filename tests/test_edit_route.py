"""Integration tests for the edit_form route and multi-select handling in FormEngine."""
import os
import pytest

from flask import Flask
from formflow.config import AppSettings
from formflow.form_engine import FormEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FORM_WITH_MULTISELECT = {
    "form_id": "test_form",
    "title": "Testformular",
    "submit_button": "Vorschau anzeigen",
    "fields": [
        {"type": "text", "name": "name", "label": "Name", "required": False, "placeholder": ""},
        {
            "type": "select",
            "name": "departments",
            "label": "Abteilungen",
            "required": False,
            "multiple": True,
            "options": ["IT", "HR", "Finance"],
        },
        {
            "type": "select",
            "name": "location",
            "label": "Standort",
            "required": False,
            "multiple": False,
            "options": ["Berlin", "Hamburg"],
        },
    ],
}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    flask_app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "formflow", "templates"),
    )
    flask_app.config["TESTING"] = True

    config = AppSettings().model_dump()
    flask_app.config["formflow"] = config

    engine = FormEngine(forms_dir="forms", config=config)
    engine.forms = {"test_form": FORM_WITH_MULTISELECT}
    engine.init_app(flask_app)

    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# POST /edit/<form_id>/<file_id>  – back to editing
# ---------------------------------------------------------------------------

class TestEditFormRoute:
    def test_edit_returns_200_with_form(self, client):
        """POST /edit/<form_id>/<file_id> should return 200 with the form HTML."""
        response = client.post(
            "/edit/test_form/abc123",
            data={"name": "Max"},
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Testformular" in html

    def test_edit_prefills_text_field(self, client):
        """POST /edit/<form_id>/<file_id> should render the form with previous text values."""
        response = client.post(
            "/edit/test_form/abc123",
            data={"name": "Erika Mustermann"},
        )
        html = response.get_data(as_text=True)
        assert "Erika Mustermann" in html

    def test_edit_returns_404_for_unknown_form(self, client):
        """POST /edit/<form_id>/<file_id> for an unknown form should return 404."""
        response = client.post("/edit/no_such_form/abc123", data={"name": "X"})
        assert response.status_code == 404

    def test_edit_deletes_temp_pdf(self, client, tmp_path):
        """POST /edit should delete the temporary PDF file if it exists."""
        pdfs_dir = tmp_path / "pdfs"
        pdfs_dir.mkdir(exist_ok=True)
        temp_file = pdfs_dir / "temp_abc123.pdf"
        temp_file.touch()
        assert temp_file.exists()

        client.post("/edit/test_form/abc123", data={"name": "Test"})

        assert not temp_file.exists()

    def test_edit_does_not_redirect(self, client):
        """POST /edit/<form_id>/<file_id> should NOT redirect (3xx)."""
        response = client.post(
            "/edit/test_form/abc123",
            data={"name": "Test"},
            follow_redirects=False,
        )
        assert response.status_code == 200

    def test_edit_prefills_multiselect_checkboxes(self, client):
        """POST /edit should mark previously selected multi-select options as checked."""
        response = client.post(
            "/edit/test_form/abc123",
            data={"name": "Test", "departments": ["IT", "HR"]},
        )
        html = response.get_data(as_text=True)
        # Both IT and HR checkboxes should be checked
        assert 'value="IT"' in html
        assert 'value="HR"' in html
        # The checked attribute should appear for the selected options
        assert html.count("checked") >= 2

    def test_edit_prefills_single_select(self, client):
        """POST /edit should pre-select the chosen option in a single-select dropdown."""
        response = client.post(
            "/edit/test_form/abc123",
            data={"name": "Test", "location": "Hamburg"},
        )
        html = response.get_data(as_text=True)
        assert 'value="Hamburg"' in html
        assert "selected" in html


# ---------------------------------------------------------------------------
# POST /preview/<form_id>  – multi-select stored as list
# ---------------------------------------------------------------------------

class TestPreviewMultiSelect:
    def test_preview_stores_multiselect_as_list(self, client, tmp_path, mocker):
        """preview_form should store multi-select values as a list, not a joined string."""
        mocker.patch("formflow.pdf_generator.PdfGenerator.generate")

        response = client.post(
            "/preview/test_form",
            data={"name": "Test", "departments": ["IT", "Finance"]},
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        # The preview page should render separate hidden fields for each option
        assert 'name="departments" value="IT"' in html
        assert 'name="departments" value="Finance"' in html
        # Should NOT have a single comma-separated hidden field
        assert 'value="IT, Finance"' not in html
        assert 'value="Finance, IT"' not in html
