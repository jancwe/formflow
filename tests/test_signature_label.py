"""Unit tests for the signature_label interpolation logic in PdfGenerator."""

from formflow.services.pdf_generator import PdfGenerator, _resolve_signature_label

DATE = "07.03.2026"


def test_placeholder_replaced_with_form_data():
    """A {fieldname} placeholder is replaced by the matching form_data value."""
    result = _resolve_signature_label("Digital unterzeichnet von {user} am {date_today}", {"user": "Max Mustermann"}, DATE)
    assert result == f"Digital unterzeichnet von Max Mustermann am {DATE}"


def test_static_string_unchanged():
    """A signature_label without placeholders is returned unchanged."""
    label = "Gegengezeichnet durch IT-Abteilung"
    result = _resolve_signature_label(label, {}, DATE)
    assert result == label


def test_unknown_placeholder_preserved():
    """An unknown placeholder is left intact in the output string."""
    result = _resolve_signature_label("Unterzeichnet von {unbekannt}", {}, DATE)
    assert result == "Unterzeichnet von {unbekannt}"


def test_date_today_placeholder_replaced():
    """{date_today} is replaced by the provided date string."""
    result = _resolve_signature_label("Datum: {date_today}", {}, DATE)
    assert result == f"Datum: {DATE}"


def test_no_signature_label_no_resolved_key():
    """If a signature field has no signature_label, signature_label_resolved is not set."""
    generator = PdfGenerator.__new__(PdfGenerator)
    fields = [{"type": "signature", "name": "sig", "label": "Unterschrift"}]
    resolved = generator._resolve_signature_labels(fields, {}, DATE)
    assert len(resolved) == 1
    assert "signature_label_resolved" not in resolved[0]


def test_signature_label_resolved_set():
    """If a signature field has a signature_label, signature_label_resolved is set correctly."""
    generator = PdfGenerator.__new__(PdfGenerator)
    fields = [
        {
            "type": "signature",
            "name": "sig",
            "label": "Unterschrift",
            "signature_label": "Von {user}",
        }
    ]
    resolved = generator._resolve_signature_labels(fields, {"user": "Anna"}, DATE)
    assert resolved[0]["signature_label_resolved"] == "Von Anna"


def test_original_field_not_mutated():
    """The original field dict is not modified when resolving labels."""
    generator = PdfGenerator.__new__(PdfGenerator)
    original = {"type": "signature", "name": "sig", "label": "U", "signature_label": "{user}"}
    resolved = generator._resolve_signature_labels([original], {"user": "Test"}, DATE)
    assert "signature_label_resolved" not in original
    assert resolved[0]["signature_label_resolved"] == "Test"


def test_non_signature_fields_unchanged():
    """Non-signature fields are passed through without modification."""
    generator = PdfGenerator.__new__(PdfGenerator)
    fields = [{"type": "text", "name": "user", "label": "Name"}]
    resolved = generator._resolve_signature_labels(fields, {"user": "X"}, DATE)
    assert resolved == fields
