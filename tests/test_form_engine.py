import pytest
import time
from form_engine import FormEngine

from config import AppSettings, SmbConfig

@pytest.fixture
def form_engine():
    """
    Provides a FormEngine instance with a default (empty) config for unit testing.
    Tests that need specific configurations can create their own instance.
    """
    # For most unit tests, an empty config is sufficient
    config = AppSettings().model_dump()
    engine = FormEngine(config=config)
    return engine

def test_sanitize_for_filename(form_engine):
    """Tests the filename sanitization logic."""
    assert form_engine._sanitize_for_filename("Simple Name") == "Simple_Name"
    assert form_engine._sanitize_for_filename("With/Special\\Chars:?*\"<>|") == "WithSpecialChars"
    assert form_engine._sanitize_for_filename("Umlaute-ÄÖÜ-ß") == "Umlaute--"
    assert form_engine._sanitize_for_filename(" leading and trailing ") == "_leading_and_trailing_"
    assert form_engine._sanitize_for_filename("file_name-123_ok") == "file_name-123_ok"

def test_generate_filename_parts(form_engine, monkeypatch):
    """Tests the logic for generating filename parts from form data."""
    form_def = {
        "fields": [
            {"name": "user_name", "in_filename": True},
            {"name": "department", "in_filename": True},
            {"name": "asset_tag", "in_filename": False},  # Should be ignored
            {"name": "empty_field", "in_filename": True},
        ]
    }
    form_data = {
        "user_name": "Max Mustermann",
        "department": "IT/Support",
        "asset_tag": "LAPTOP-123",
        "empty_field": ""
    }

    # Mock time.time() to have a predictable timestamp
    monkeypatch.setattr(time, "time", lambda: 1234567890)

    parts = form_engine._generate_filename_parts("my-form", form_def, form_data)

    # Expected: ['my-form', 'Max_Mustermann', 'ITSupport', '1234567890']
    assert parts == ["my-form", "Max_Mustermann", "ITSupport", "1234567890"]

def test_store_pdf_locally(form_engine, mocker, tmp_path):
    """Tests that the PDF is stored locally when SMB is disabled."""
    # Create a dummy temp file
    temp_file = tmp_path / "temp.pdf"
    temp_file.touch()

    # Mock os.rename to track its call
    mock_rename = mocker.patch("os.rename")

    # Provide a specific config for this test case
    form_engine.config = AppSettings(smb=SmbConfig(enabled=False)).model_dump()

    form_engine._store_pdf(str(temp_file), "/path/to/final.pdf", [])

    # Assert that os.rename was called with the correct arguments
    mock_rename.assert_called_once_with(str(temp_file), "/path/to/final.pdf")

def test_store_pdf_smb_success(form_engine, mocker, tmp_path):
    """Tests a successful PDF upload to an SMB share."""
    # Create a dummy temp file
    temp_file = tmp_path / "temp.pdf"
    temp_file.write_text("PDF content")

    # Mock SMB functions
    mock_register = mocker.patch("smbclient.register_session")
    m = mocker.mock_open()
    mock_smb_open = mocker.patch("smbclient.open_file", m)

    # Provide a specific config for this test case
    smb_config = SmbConfig(
        enabled=True,
        server="smb-server",
        share="pdfs",
        folder="forms",
        username="testuser",
        password="testpass"
    )
    form_engine.config = AppSettings(smb=smb_config).model_dump()

    filename_parts = ["notebook_handover", "test-user", "12345"]
    form_engine._store_pdf(str(temp_file), "", filename_parts)

    # Assert that the session was registered
    mock_register.assert_called_once_with("smb-server", username="testuser", password="testpass")

    # Assert that the file was opened on the SMB share with the correct path
    expected_path = r"\\smb-server\pdfs\forms\notebook_handover_test-user_12345.pdf"
    mock_smb_open.assert_called_once_with(expected_path, mode='wb')

    # Assert that content was written
    handle = m()
    handle.write.assert_called_once_with(b"PDF content")

def test_store_pdf_smb_missing_config_raises_error(form_engine):
    """
    Tests that a RuntimeError is raised if SMB is enabled but config is incomplete.
    """
    # Provide a specific incomplete config for this test case
    form_engine.config = AppSettings(smb=SmbConfig(enabled=True)).model_dump()

    with pytest.raises(RuntimeError, match="SMB ist aktiviert, aber Zugangsdaten/Pfade fehlen."):
        form_engine._store_pdf("/dummy/path.pdf", "", [])
