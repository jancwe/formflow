"""Integration tests for the draft routes in FormEngine."""
import json
import pytest

from formflow.services.form_engine import FormEngine
from formflow.services.draft_service import save_draft


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_FORM = {
    "form_id": "test_form",
    "title": "Testformular",
    "submit_button": "Vorschau anzeigen",
    "fields": [
        {"type": "text", "name": "name", "label": "Name", "required": False, "placeholder": "", "in_draft_title": True},
        {"type": "date", "name": "date", "label": "Datum", "required": False},
        {
            "type": "signature",
            "name": "signature",
            "label": "Unterschrift",
            "required": True,
            "height": "200px",
        },
    ],
}

FORM_WITH_MULTISELECT = {
    "form_id": "multi_form",
    "title": "Formular mit Mehrfachauswahl",
    "submit_button": "Vorschau anzeigen",
    "fields": [
        {"type": "text", "name": "name", "label": "Name", "required": False, "placeholder": ""},
        {
            "type": "select",
            "name": "accessories",
            "label": "Zubehör",
            "required": False,
            "multiple": True,
            "options": ["Netzteil", "Maus", "Tasche"],
        },
    ],
}


@pytest.fixture
def client(app, engine):
    """Client with draft/multi test forms registered via the shared app fixture."""
    engine.forms = {"test_form": SIMPLE_FORM, "multi_form": FORM_WITH_MULTISELECT}
    engine.init_app(app)
    return app.test_client()


@pytest.fixture
def drafts_dir(tmp_path):
    """Returns the path to the drafts directory used during tests."""
    return str(tmp_path / "drafts")


# ---------------------------------------------------------------------------
# POST /draft/<form_id>  – save draft
# ---------------------------------------------------------------------------

class TestSaveDraftRoute:
    def test_save_draft_redirects_to_forms(self, client):
        """POST /draft/<form_id> should redirect to /forms on success."""
        response = client.post(
            "/draft/test_form",
            data={"name": "Max", "date": "2026-01-01"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.location.endswith("/forms")

    def test_save_draft_creates_file(self, client, tmp_path):
        """POST /draft/<form_id> should create a draft JSON file."""
        client.post("/draft/test_form", data={"name": "Erika", "date": "2026-03-01"})

        draft_files = list((tmp_path / "drafts").glob("draft_*.json"))
        assert len(draft_files) == 1

    def test_save_draft_persists_form_data(self, client, tmp_path):
        """The saved draft file should contain the submitted field values."""
        client.post(
            "/draft/test_form",
            data={"name": "Hans", "date": "2026-06-15"},
        )

        draft_files = list((tmp_path / "drafts").glob("draft_*.json"))
        with open(draft_files[0], encoding="utf-8") as f:
            draft = json.load(f)

        assert draft["form_id"] == "test_form"
        assert draft["form_data"]["name"] == "Hans"
        assert draft["form_data"]["date"] == "2026-06-15"

    def test_save_draft_unknown_form_returns_404(self, client):
        """POST /draft/<form_id> for an unknown form should return 404."""
        response = client.post("/draft/no_such_form", data={"x": "y"})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /draft/<form_id>/<draft_id>/load  – load draft
# ---------------------------------------------------------------------------

class TestLoadDraftRoute:
    def _create_draft(self, tmp_path, form_data=None):
        """Helper: writes a draft file directly and returns the draft_id."""
        if form_data is None:
            form_data = {"name": "TestUser", "date": "2026-01-15"}
        drafts_dir = str(tmp_path / "drafts")
        return save_draft(drafts_dir, "test_form", form_data)

    def test_load_draft_returns_200(self, client, tmp_path):
        """GET /draft/<form_id>/<draft_id>/load should return 200 with the form."""
        draft_id = self._create_draft(tmp_path)
        response = client.get(f"/draft/test_form/{draft_id}/load")
        assert response.status_code == 200

    def test_load_draft_prefills_field_values(self, client, tmp_path):
        """The rendered form should contain the saved field values."""
        draft_id = self._create_draft(tmp_path, {"name": "VorausgefülltUser", "date": "2026-02-20"})
        response = client.get(f"/draft/test_form/{draft_id}/load")

        html = response.get_data(as_text=True)
        assert "VorausgefülltUser" in html

    def test_load_draft_preserves_file(self, client, tmp_path):
        """The draft file should NOT be removed after it is loaded (persists for re-saves)."""
        draft_id = self._create_draft(tmp_path)
        client.get(f"/draft/test_form/{draft_id}/load")

        draft_path = tmp_path / "drafts" / f"draft_{draft_id}.json"
        assert draft_path.exists()

    def test_load_draft_redirects_for_missing_draft(self, client):
        """Loading a non-existent draft should redirect gracefully to /forms."""
        response = client.get(
            "/draft/test_form/nonexistent_draft_id/load",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.location.endswith("/forms")

    def test_load_draft_returns_404_for_unknown_form(self, client, tmp_path):
        """Loading a draft for an unknown form_id should return 404."""
        drafts_dir = str(tmp_path / "drafts")
        draft_id = save_draft(drafts_dir, "no_such_form", {"k": "v"})

        response = client.get(f"/draft/no_such_form/{draft_id}/load")
        assert response.status_code == 404

    def test_load_draft_includes_draft_id_in_form(self, client, tmp_path):
        """The rendered form should contain the draft_id as a hidden field."""
        draft_id = self._create_draft(tmp_path)
        response = client.get(f"/draft/test_form/{draft_id}/load")

        html = response.get_data(as_text=True)
        assert draft_id in html

    def test_load_draft_restores_multiselect_checkboxes(self, client, tmp_path):
        """Loading a draft should restore multi-select checkboxes that were saved."""
        drafts_dir = str(tmp_path / "drafts")
        draft_id = save_draft(drafts_dir, "multi_form", {"name": "Test", "accessories": ["Netzteil", "Maus"]})

        response = client.get(f"/draft/multi_form/{draft_id}/load")
        assert response.status_code == 200

        html = response.get_data(as_text=True)
        # Both selected options should be checked (checked> marks the end of checkbox input)
        assert html.count("checked>") == 2
        # Verify the values appear in the form
        assert 'value="Netzteil"' in html
        assert 'value="Maus"' in html
        assert 'value="Tasche"' in html

# ---------------------------------------------------------------------------
# POST /draft/<draft_id>/delete  – delete draft
# ---------------------------------------------------------------------------

class TestDeleteDraftRoute:
    def test_delete_draft_redirects_to_forms(self, client, tmp_path):
        """POST /draft/<draft_id>/delete should redirect to /forms."""
        drafts_dir = str(tmp_path / "drafts")
        draft_id = save_draft(drafts_dir, "test_form", {"x": "y"})

        response = client.post(f"/draft/{draft_id}/delete", follow_redirects=False)

        assert response.status_code == 302
        assert response.location.endswith("/forms")

    def test_delete_draft_removes_file(self, client, tmp_path):
        """POST /draft/<draft_id>/delete should remove the draft file."""
        drafts_dir = str(tmp_path / "drafts")
        draft_id = save_draft(drafts_dir, "test_form", {"x": "y"})
        draft_path = tmp_path / "drafts" / f"draft_{draft_id}.json"
        assert draft_path.exists()

        client.post(f"/draft/{draft_id}/delete")

        assert not draft_path.exists()

    def test_delete_nonexistent_draft_still_redirects(self, client):
        """Deleting a non-existent draft should not crash; it should redirect to /forms."""
        response = client.post("/draft/no_such_draft/delete", follow_redirects=False)
        assert response.status_code == 302
        assert response.location.endswith("/forms")


# ---------------------------------------------------------------------------
# GET /forms  – list forms with drafts
# ---------------------------------------------------------------------------

class TestListFormsWithDrafts:
    def test_list_forms_shows_draft_section(self, client, tmp_path):
        """GET /forms shows the 'Offene Entwürfe' section when drafts exist."""
        drafts_dir = str(tmp_path / "drafts")
        save_draft(drafts_dir, "test_form", {"name": "DraftUser"})

        response = client.get("/forms")
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "Offene Entwürfe" in html

    def test_list_forms_hides_draft_section_when_empty(self, client):
        """GET /forms does not show 'Offene Entwürfe' when there are no drafts."""
        response = client.get("/forms")
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "Offene Entwürfe" not in html

    def test_list_forms_shows_draft_form_title(self, client, tmp_path):
        """GET /forms displays the form title for each draft."""
        drafts_dir = str(tmp_path / "drafts")
        save_draft(drafts_dir, "test_form", {})

        response = client.get("/forms")
        html = response.get_data(as_text=True)

        assert "Testformular" in html

    def test_list_forms_shows_weiterbearbeiten_link(self, client, tmp_path):
        """GET /forms includes a 'Weiterbearbeiten' link for each draft."""
        drafts_dir = str(tmp_path / "drafts")
        draft_id = save_draft(drafts_dir, "test_form", {})

        response = client.get("/forms")
        html = response.get_data(as_text=True)

        assert "Weiterbearbeiten" in html
        assert f"/draft/test_form/{draft_id}/load" in html

    def test_list_forms_shows_delete_button(self, client, tmp_path):
        """GET /forms includes a delete form/button for each draft."""
        drafts_dir = str(tmp_path / "drafts")
        draft_id = save_draft(drafts_dir, "test_form", {})

        response = client.get("/forms")
        html = response.get_data(as_text=True)

        assert f"/draft/{draft_id}/delete" in html
        assert "Löschen" in html

    def test_list_forms_shows_draft_subtitle(self, client, tmp_path):
        """GET /forms shows field values for in_draft_title fields as the subtitle."""
        drafts_dir = str(tmp_path / "drafts")
        save_draft(drafts_dir, "test_form", {"name": "Max Mustermann", "date": "2026-01-01"})

        response = client.get("/forms")
        html = response.get_data(as_text=True)

        assert "Max Mustermann" in html

    def test_list_forms_no_subtitle_when_field_empty(self, client, tmp_path):
        """GET /forms does not show a subtitle when in_draft_title field has no value."""
        drafts_dir = str(tmp_path / "drafts")
        save_draft(drafts_dir, "test_form", {"name": "", "date": "2026-01-01"})

        response = client.get("/forms")
        html = response.get_data(as_text=True)

        # The subtitle span should not be rendered (empty string is falsy in Jinja2)
        assert "fw-semibold" not in html


# ---------------------------------------------------------------------------
# POST /preview/<form_id>  – auto-save draft
# ---------------------------------------------------------------------------

class TestPreviewAutosaveDraft:
    def test_preview_creates_draft_when_no_draft_id(self, client, tmp_path, mocker):
        """POST /preview/<form_id> without draft_id should create a new draft file."""
        mocker.patch("formflow.services.pdf_generator.PdfGenerator.generate")

        client.post("/preview/test_form", data={"name": "AutoSave", "date": "2026-06-01"})

        draft_files = list((tmp_path / "drafts").glob("draft_*.json"))
        assert len(draft_files) == 1
        with open(draft_files[0], encoding="utf-8") as f:
            draft = json.load(f)
        assert draft["form_data"]["name"] == "AutoSave"

    def test_preview_updates_draft_when_draft_id_given(self, client, tmp_path, mocker):
        """POST /preview/<form_id> with draft_id should update the existing draft."""
        mocker.patch("formflow.services.pdf_generator.PdfGenerator.generate")

        drafts_dir = str(tmp_path / "drafts")
        draft_id = save_draft(drafts_dir, "test_form", {"name": "OldName", "date": "2026-01-01"})

        client.post(
            "/preview/test_form",
            data={"name": "NewName", "date": "2026-06-01", "draft_id": draft_id},
        )

        # Still exactly one draft file (updated, not duplicated)
        draft_files = list((tmp_path / "drafts").glob("draft_*.json"))
        assert len(draft_files) == 1
        with open(draft_files[0], encoding="utf-8") as f:
            draft = json.load(f)
        assert draft["form_data"]["name"] == "NewName"
        assert draft["draft_id"] == draft_id

    def test_preview_includes_draft_id_in_response(self, client, tmp_path, mocker):
        """POST /preview/<form_id> should include the draft_id in the response HTML."""
        mocker.patch("formflow.services.pdf_generator.PdfGenerator.generate")

        response = client.post("/preview/test_form", data={"name": "Test"})
        html = response.get_data(as_text=True)

        draft_files = list((tmp_path / "drafts").glob("draft_*.json"))
        assert len(draft_files) == 1
        with open(draft_files[0], encoding="utf-8") as f:
            draft = json.load(f)
        assert draft["draft_id"] in html


# ---------------------------------------------------------------------------
# POST /confirm/<form_id>/<file_id>  – deletes draft on success
# ---------------------------------------------------------------------------

class TestConfirmDeletesDraft:
    def test_confirm_deletes_draft_on_success(self, client, tmp_path, mocker):
        """POST /confirm/<form_id>/<file_id> should delete the draft after successful PDF save."""
        mocker.patch(
            "formflow.services.form_engine.FormEngine._store_pdf",
            return_value={"filename": "test.pdf"},
        )

        pdfs_dir = tmp_path / "pdfs"
        pdfs_dir.mkdir(exist_ok=True)
        (pdfs_dir / "temp_abc123.pdf").write_bytes(b"%PDF-1.4")

        drafts_dir = str(tmp_path / "drafts")
        draft_id = save_draft(drafts_dir, "test_form", {"name": "WillBeDeleted"})
        draft_path = tmp_path / "drafts" / f"draft_{draft_id}.json"
        assert draft_path.exists()

        client.post(
            "/confirm/test_form/abc123",
            data={"name": "WillBeDeleted", "draft_id": draft_id},
        )

        assert not draft_path.exists()

    def test_confirm_without_draft_id_does_not_crash(self, client, tmp_path, mocker):
        """POST /confirm/<form_id>/<file_id> without draft_id should succeed without error."""
        mocker.patch(
            "formflow.services.form_engine.FormEngine._store_pdf",
            return_value={"filename": "test.pdf"},
        )

        pdfs_dir = tmp_path / "pdfs"
        pdfs_dir.mkdir(exist_ok=True)
        (pdfs_dir / "temp_abc123.pdf").write_bytes(b"%PDF-1.4")

        response = client.post(
            "/confirm/test_form/abc123",
            data={"name": "NoDraft"},
        )
        assert response.status_code == 200
