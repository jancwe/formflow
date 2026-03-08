"""Unit tests for helper classes and methods in formflow.pdf_generator."""
import pytest

from formflow.services.pdf_generator import _FormatMap, _resolve_signature_label, PdfGenerator


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def pdf_generator():
    """Returns a PdfGenerator instance for unit testing helper methods."""
    return PdfGenerator.__new__(PdfGenerator)  # skip __init__ to avoid filesystem deps


# ---------------------------------------------------------------------------
# TestFormatMap
# ---------------------------------------------------------------------------

class TestFormatMap:
    def test_known_key_returns_value(self):
        """A key that exists in the dict returns its associated value."""
        m = _FormatMap({"user": "Max"})
        assert m["user"] == "Max"

    def test_missing_key_returns_placeholder(self):
        """A missing key returns the key wrapped in curly braces."""
        m = _FormatMap()
        assert m["unbekannt"] == "{unbekannt}"

    def test_missing_key_with_special_chars(self):
        """A missing key with underscores returns the placeholder intact."""
        m = _FormatMap()
        assert m["my_field"] == "{my_field}"

    def test_known_and_missing_keys_coexist(self):
        """Known keys return their value while missing keys return the placeholder."""
        m = _FormatMap({"name": "Erika"})
        assert m["name"] == "Erika"
        assert m["unknown"] == "{unknown}"


# ---------------------------------------------------------------------------
# TestResolveSignatureLabel
# ---------------------------------------------------------------------------

class TestResolveSignatureLabel:
    def test_interpolates_form_field(self):
        """A {fieldname} placeholder is replaced by the matching value from form_data."""
        result = _resolve_signature_label("Unterzeichnet von {user}", {"user": "Max"}, "07.03.2026")
        assert result == "Unterzeichnet von Max"

    def test_interpolates_date_today(self):
        """{date_today} is replaced by the provided date string."""
        result = _resolve_signature_label("Am {date_today} unterzeichnet", {}, "07.03.2026")
        assert result == "Am 07.03.2026 unterzeichnet"

    def test_interpolates_mixed_placeholders(self):
        """Both a form_data placeholder and {date_today} are replaced correctly."""
        result = _resolve_signature_label(
            "Von {user} am {date_today}", {"user": "Erika"}, "01.01.2026"
        )
        assert result == "Von Erika am 01.01.2026"

    def test_unknown_placeholder_stays_intact(self):
        """An unknown placeholder is left unchanged in the output."""
        result = _resolve_signature_label("Gezeichnet von {unknown_field}", {}, "07.03.2026")
        assert result == "Gezeichnet von {unknown_field}"

    def test_static_string_unchanged(self):
        """A template string without any placeholders is returned unchanged."""
        result = _resolve_signature_label("IT-Abteilung", {}, "07.03.2026")
        assert result == "IT-Abteilung"

    def test_empty_form_data_with_known_field_placeholder(self):
        """{user} with empty form_data leaves the placeholder intact."""
        result = _resolve_signature_label("{user}", {}, "07.03.2026")
        assert result == "{user}"

    def test_empty_string_template(self):
        """An empty template string returns an empty string."""
        result = _resolve_signature_label("", {"user": "Max"}, "07.03.2026")
        assert result == ""

    def test_form_data_value_with_spaces(self):
        """A form_data value containing spaces is interpolated correctly."""
        result = _resolve_signature_label("{user}", {"user": "Max Mustermann"}, "07.03.2026")
        assert result == "Max Mustermann"

    def test_multiple_occurrences_of_same_placeholder(self):
        """The same placeholder appearing multiple times is replaced in all positions."""
        result = _resolve_signature_label("{user} und {user}", {"user": "Max"}, "07.03.2026")
        assert result == "Max und Max"


# ---------------------------------------------------------------------------
# TestResolveSIgnatureLabels
# ---------------------------------------------------------------------------

class TestResolveSIgnatureLabels:
    def test_non_signature_fields_unchanged(self, pdf_generator):
        """Fields with a type other than 'signature' are passed through without modification."""
        fields = [{"type": "text", "name": "name", "label": "Name"}]
        result = pdf_generator._resolve_signature_labels(fields, {}, "07.03.2026")
        assert result == fields
        assert "signature_label_resolved" not in result[0]

    def test_signature_field_without_label_unchanged(self, pdf_generator):
        """A signature field that has no signature_label key does not receive signature_label_resolved."""
        fields = [{"type": "signature", "name": "sig", "label": "Unterschrift"}]
        result = pdf_generator._resolve_signature_labels(fields, {}, "07.03.2026")
        assert "signature_label_resolved" not in result[0]

    def test_signature_field_with_label_gets_resolved(self, pdf_generator):
        """A signature field with signature_label gets a correct signature_label_resolved entry."""
        fields = [{"type": "signature", "name": "sig", "label": "U", "signature_label": "Von {user}"}]
        result = pdf_generator._resolve_signature_labels(fields, {"user": "Anna"}, "07.03.2026")
        assert result[0]["signature_label_resolved"] == "Von Anna"

    def test_original_field_dict_not_mutated(self, pdf_generator):
        """The original field dict is not modified; only the copy in the returned list changes."""
        original = {"type": "signature", "name": "sig", "label": "U", "signature_label": "{user}"}
        pdf_generator._resolve_signature_labels([original], {"user": "Test"}, "07.03.2026")
        assert "signature_label_resolved" not in original

    def test_original_fields_list_not_mutated(self, pdf_generator):
        """The original fields list is not modified by the method."""
        fields = [{"type": "signature", "name": "sig", "label": "U", "signature_label": "{user}"}]
        original_length = len(fields)
        pdf_generator._resolve_signature_labels(fields, {"user": "Test"}, "07.03.2026")
        assert len(fields) == original_length

    def test_multiple_signature_fields(self, pdf_generator):
        """Multiple signature fields each receive their own resolved label."""
        fields = [
            {"type": "signature", "name": "sig1", "label": "U1", "signature_label": "Von {user}"},
            {"type": "signature", "name": "sig2", "label": "U2", "signature_label": "Datum: {date_today}"},
        ]
        result = pdf_generator._resolve_signature_labels(fields, {"user": "Max"}, "07.03.2026")
        assert result[0]["signature_label_resolved"] == "Von Max"
        assert result[1]["signature_label_resolved"] == "Datum: 07.03.2026"

    def test_mixed_field_types(self, pdf_generator):
        """Only signature fields with signature_label receive signature_label_resolved; others are unmodified."""
        fields = [
            {"type": "text", "name": "name", "label": "Name"},
            {"type": "date", "name": "dob", "label": "Geburtsdatum"},
            {"type": "select", "name": "dept", "label": "Abteilung"},
            {"type": "signature", "name": "sig", "label": "U", "signature_label": "Von {user}"},
        ]
        result = pdf_generator._resolve_signature_labels(fields, {"user": "Erika"}, "01.01.2026")
        for field in result[:3]:
            assert "signature_label_resolved" not in field
        assert result[3]["signature_label_resolved"] == "Von Erika"

    def test_returns_same_length_as_input(self, pdf_generator):
        """The returned list has the same number of elements as the input list."""
        fields = [
            {"type": "text", "name": "a", "label": "A"},
            {"type": "signature", "name": "b", "label": "B", "signature_label": "X"},
            {"type": "date", "name": "c", "label": "C"},
        ]
        result = pdf_generator._resolve_signature_labels(fields, {}, "07.03.2026")
        assert len(result) == len(fields)

    def test_empty_fields_list(self, pdf_generator):
        """An empty fields list returns an empty list."""
        result = pdf_generator._resolve_signature_labels([], {}, "07.03.2026")
        assert result == []

    def test_date_today_resolved_in_signature_label(self, pdf_generator):
        """{date_today} in a signature_label is replaced with the provided date string."""
        fields = [{"type": "signature", "name": "sig", "label": "U", "signature_label": "Am {date_today}"}]
        result = pdf_generator._resolve_signature_labels(fields, {}, "15.06.2026")
        assert result[0]["signature_label_resolved"] == "Am 15.06.2026"
