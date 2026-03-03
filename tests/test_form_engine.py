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

    result = form_engine._store_pdf(str(temp_file), "/path/to/final.pdf", [])

    # Assert that os.rename was called with the correct arguments
    mock_rename.assert_called_once_with(str(temp_file), "/path/to/final.pdf")
    assert result["stored_via"] == "local"
    assert result["filename"] == "final.pdf"

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
    result = form_engine._store_pdf(str(temp_file), "", filename_parts)

    # Assert that the session was registered
    mock_register.assert_called_once_with("smb-server", username="testuser", password="testpass")

    # Assert that the file was opened on the SMB share with the correct path
    expected_path = r"\\smb-server\pdfs\forms\notebook_handover_test-user_12345.pdf"
    mock_smb_open.assert_called_once_with(expected_path, mode='wb')

    # Assert that content was written
    handle = m()
    handle.write.assert_called_once_with(b"PDF content")

    assert result["stored_via"] == "smb"

def test_store_pdf_smb_missing_config_raises_error(form_engine):
    """
    Tests that a RuntimeError is raised if SMB is enabled but config is incomplete.
    """
    # Provide a specific incomplete config for this test case
    form_engine.config = AppSettings(smb=SmbConfig(enabled=True)).model_dump()

    with pytest.raises(RuntimeError, match="SMB ist aktiviert, aber Zugangsdaten/Pfade fehlen."):
        form_engine._store_pdf("/dummy/path.pdf", "", [])

def test_store_pdf_smb_fallback_on_connection_error(form_engine, mocker, tmp_path):
    """Tests that a failed SMB upload falls back to local storage with a warning."""
    temp_file = tmp_path / "temp.pdf"
    temp_file.write_text("PDF content")

    # Mock SMB to raise a connection error
    mocker.patch("smbclient.register_session", side_effect=ConnectionError("Connection refused"))
    mock_rename = mocker.patch("os.rename")

    smb_config = SmbConfig(
        enabled=True,
        server="smb-server",
        share="pdfs",
        folder="forms",
        username="testuser",
        password="testpass"
    )
    form_engine.config = AppSettings(smb=smb_config).model_dump()

    result = form_engine._store_pdf(str(temp_file), "/path/to/fallback.pdf", ["test"])

    mock_rename.assert_called_once_with(str(temp_file), "/path/to/fallback.pdf")
    assert result["stored_via"] == "local"
    assert "warning" in result
    assert "SMB-Server" in result["warning"]
    assert "fallback.pdf" in result["warning"]

def test_cleanup_temp_files_removes_old_files(form_engine, tmp_path, monkeypatch):
    """Tests that _cleanup_temp_files removes temp files older than the threshold."""
    monkeypatch.chdir(tmp_path)
    pdfs_dir = tmp_path / "pdfs"
    pdfs_dir.mkdir()

    old_file = pdfs_dir / "temp_old.pdf"
    old_file.touch()
    recent_file = pdfs_dir / "temp_recent.pdf"
    recent_file.touch()
    non_temp_file = pdfs_dir / "final_doc.pdf"
    non_temp_file.touch()

    now = 1000000.0
    # old_file is 2 hours old, recent_file is 30 minutes old
    monkeypatch.setattr("os.path.getmtime", lambda path: now - 7200 if "old" in path else now - 1800)
    monkeypatch.setattr(time, "time", lambda: now)

    form_engine._cleanup_temp_files(max_age_seconds=3600)

    assert not old_file.exists()
    assert recent_file.exists()
    assert non_temp_file.exists()

def test_cleanup_temp_files_keeps_young_files(form_engine, tmp_path, monkeypatch):
    """Tests that _cleanup_temp_files does not remove files newer than the threshold."""
    monkeypatch.chdir(tmp_path)
    pdfs_dir = tmp_path / "pdfs"
    pdfs_dir.mkdir()

    young_file = pdfs_dir / "temp_young.pdf"
    young_file.touch()

    now = 1000000.0
    monkeypatch.setattr("os.path.getmtime", lambda path: now - 60)
    monkeypatch.setattr(time, "time", lambda: now)

    form_engine._cleanup_temp_files(max_age_seconds=3600)

    assert young_file.exists()

def test_cleanup_temp_files_handles_oserror(form_engine, tmp_path, monkeypatch, caplog):
    """Tests that _cleanup_temp_files logs a warning and continues on OSError."""
    import logging
    monkeypatch.chdir(tmp_path)
    pdfs_dir = tmp_path / "pdfs"
    pdfs_dir.mkdir()

    error_file = pdfs_dir / "temp_error.pdf"
    error_file.touch()

    now = 1000000.0
    monkeypatch.setattr("os.path.getmtime", lambda path: now - 7200)
    monkeypatch.setattr(time, "time", lambda: now)
    def raise_oserror(path):
        raise OSError("Permission denied")

    monkeypatch.setattr("os.remove", raise_oserror)

    with caplog.at_level(logging.WARNING):
        form_engine._cleanup_temp_files(max_age_seconds=3600)

    assert any("Konnte temp-Datei nicht löschen" in r.message for r in caplog.records)
def test_store_pdf_smb_session_reused(form_engine, mocker, tmp_path):
    """Tests that the SMB session is registered only once across multiple uploads."""
    smb_config = SmbConfig(
        enabled=True,
        server="smb-server",
        share="pdfs",
        folder="",
        username="testuser",
        password="testpass"
    )
    form_engine.config = AppSettings(smb=smb_config).model_dump()

    mock_register = mocker.patch("smbclient.register_session")
    m = mocker.mock_open()
    mocker.patch("smbclient.open_file", m)

    for i in range(3):
        temp_file = tmp_path / f"temp{i}.pdf"
        temp_file.write_text("PDF content")
        form_engine._store_pdf(str(temp_file), "", [f"file{i}"])

    # register_session should only be called once regardless of upload count
    mock_register.assert_called_once_with("smb-server", username="testuser", password="testpass")

def test_store_pdf_smb_reregisters_on_session_expiry(form_engine, mocker, tmp_path):
    """Tests that an expired session is re-registered once and the upload retried."""
    temp_file = tmp_path / "temp.pdf"
    temp_file.write_text("PDF content")

    smb_config = SmbConfig(
        enabled=True,
        server="smb-server",
        share="pdfs",
        folder="",
        username="testuser",
        password="testpass"
    )
    form_engine.config = AppSettings(smb=smb_config).model_dump()

    # Simulate a session that is already registered
    form_engine._smb_session_registered = True

    mock_register = mocker.patch("smbclient.register_session")
    m = mocker.mock_open()
    # First open_file call raises (simulating expired session), second succeeds
    mock_smb_open = mocker.patch(
        "smbclient.open_file",
        side_effect=[OSError("Session expired"), m.return_value]
    )
    m.return_value.__enter__ = lambda s: s
    m.return_value.__exit__ = mocker.Mock(return_value=False)
    m.return_value.write = mocker.Mock()

    mocker.patch("os.remove")

    result = form_engine._store_pdf(str(temp_file), "", ["refile"])

    # register_session should have been called once (for re-registration)
    mock_register.assert_called_once_with("smb-server", username="testuser", password="testpass")
    assert form_engine._smb_session_registered is True
    assert result["stored_via"] == "smb"

def test_store_pdf_smb_flag_reset_on_fallback(form_engine, mocker, tmp_path):
    """Tests that _smb_session_registered is reset to False after a failed upload."""
    temp_file = tmp_path / "temp.pdf"
    temp_file.write_text("PDF content")

    smb_config = SmbConfig(
        enabled=True,
        server="smb-server",
        share="pdfs",
        folder="",
        username="testuser",
        password="testpass"
    )
    form_engine.config = AppSettings(smb=smb_config).model_dump()

    mocker.patch("smbclient.register_session", side_effect=ConnectionError("refused"))
    mocker.patch("os.rename")

    assert form_engine._smb_session_registered is False
    form_engine._store_pdf(str(temp_file), "/fallback.pdf", ["f"])

    # Flag should remain False so the next call re-attempts registration
    assert form_engine._smb_session_registered is False
