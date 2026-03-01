import pytest
import time
from form_engine import FormEngine

@pytest.fixture
def form_engine(monkeypatch):
    """
    Provides a FormEngine instance with mocked external dependencies to allow for
    isolated unit testing of its helper methods.
    """
    # Mock methods that read from the filesystem or environment variables
    monkeypatch.setattr(FormEngine, "_load_config_from_env", lambda self: {})
    monkeypatch.setattr(FormEngine, "_load_forms", lambda self: None)
    engine = FormEngine()
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
