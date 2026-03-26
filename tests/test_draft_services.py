import json
import os
import time
import pytest
from werkzeug.datastructures import MultiDict

from formflow.services.draft_service import collect_form_data, save_draft, load_draft, list_drafts, delete_draft, update_draft, _build_draft_subtitle


@pytest.fixture
def drafts_dir(tmp_path):
    """Provides a temporary directory to act as the drafts folder."""
    d = tmp_path / "drafts"
    d.mkdir()
    return str(d)


# ---------------------------------------------------------------------------
# save_draft
# ---------------------------------------------------------------------------

def test_save_draft_creates_file(drafts_dir):
    """save_draft creates a JSON file in drafts_dir and returns a draft_id."""
    form_data = {"name": "Max", "date": "2026-01-01"}
    draft_id = save_draft(drafts_dir, "test_form", form_data)

    assert isinstance(draft_id, str)
    assert len(draft_id) == 32  # uuid4().hex is 32 chars

    expected_path = os.path.join(drafts_dir, f"draft_{draft_id}.json")
    assert os.path.isfile(expected_path)


def test_save_draft_file_contents(drafts_dir):
    """save_draft persists form_id, form_data, draft_id and saved_at."""
    form_data = {"field_a": "value_a", "field_b": "value_b"}
    draft_id = save_draft(drafts_dir, "my_form", form_data)

    path = os.path.join(drafts_dir, f"draft_{draft_id}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["draft_id"] == draft_id
    assert data["form_id"] == "my_form"
    assert data["form_data"] == form_data
    assert "saved_at" in data
    assert "T" in data["saved_at"]  # ISO-format contains 'T'


def test_save_draft_unique_ids(drafts_dir):
    """Each call to save_draft generates a unique draft_id."""
    id1 = save_draft(drafts_dir, "form_a", {})
    id2 = save_draft(drafts_dir, "form_a", {})
    assert id1 != id2


# ---------------------------------------------------------------------------
# load_draft
# ---------------------------------------------------------------------------

def test_load_draft_returns_correct_data(drafts_dir):
    """load_draft returns the same data that was saved."""
    form_data = {"employee": "Erika", "date": "2026-03-01"}
    draft_id = save_draft(drafts_dir, "handover", form_data)

    draft = load_draft(drafts_dir, draft_id)

    assert draft["draft_id"] == draft_id
    assert draft["form_id"] == "handover"
    assert draft["form_data"] == form_data


def test_load_draft_raises_for_missing_file(drafts_dir):
    """load_draft raises FileNotFoundError when the draft file does not exist."""
    with pytest.raises(FileNotFoundError):
        load_draft(drafts_dir, "nonexistent_draft_id")


def test_load_draft_raises_for_corrupt_file(drafts_dir):
    """load_draft raises json.JSONDecodeError for a corrupt JSON file."""
    corrupt_path = os.path.join(drafts_dir, "draft_badid.json")
    with open(corrupt_path, "w") as f:
        f.write("not valid json{{{")

    with pytest.raises(json.JSONDecodeError):
        load_draft(drafts_dir, "badid")


# ---------------------------------------------------------------------------
# list_drafts
# ---------------------------------------------------------------------------

def test_list_drafts_returns_empty_for_missing_dir(tmp_path):
    """list_drafts returns an empty list when the directory does not exist."""
    result = list_drafts(str(tmp_path / "nonexistent"), {})
    assert result == []


def test_list_drafts_returns_empty_for_empty_dir(drafts_dir):
    """list_drafts returns an empty list when there are no draft files."""
    result = list_drafts(drafts_dir, {})
    assert result == []


def test_list_drafts_resolves_form_title(drafts_dir):
    """list_drafts resolves form_title from the forms dict."""
    forms = {"my_form": {"title": "Mein Formular", "fields": []}}
    save_draft(drafts_dir, "my_form", {"field": "val"})

    drafts = list_drafts(drafts_dir, forms)

    assert len(drafts) == 1
    assert drafts[0]["form_title"] == "Mein Formular"
    assert drafts[0]["form_id"] == "my_form"
    assert "draft_id" in drafts[0]
    assert "saved_at" in drafts[0]


def test_list_drafts_uses_form_id_as_fallback_title(drafts_dir):
    """list_drafts falls back to form_id when the form is not in forms dict."""
    save_draft(drafts_dir, "unknown_form", {})

    drafts = list_drafts(drafts_dir, {})

    assert drafts[0]["form_title"] == "unknown_form"


def test_list_drafts_draft_subtitle_from_in_draft_title_fields(drafts_dir):
    """list_drafts builds draft_subtitle from fields that have in_draft_title: true."""
    forms = {
        "handover": {
            "title": "Übergabe",
            "fields": [
                {"name": "user", "in_draft_title": True},
                {"name": "notebook", "in_draft_title": True},
                {"name": "service_tag"},  # not in draft title
            ],
        }
    }
    save_draft(drafts_dir, "handover", {"user": "Max Mustermann", "notebook": "ThinkPad", "service_tag": "ABC123"})

    drafts = list_drafts(drafts_dir, forms)

    assert drafts[0]["draft_subtitle"] == "Max Mustermann, ThinkPad"


def test_list_drafts_draft_subtitle_empty_when_no_in_draft_title_fields(drafts_dir):
    """draft_subtitle is an empty string when no fields have in_draft_title: true."""
    forms = {
        "my_form": {
            "title": "Formular",
            "fields": [{"name": "name"}, {"name": "date"}],
        }
    }
    save_draft(drafts_dir, "my_form", {"name": "Max", "date": "2026-01-01"})

    drafts = list_drafts(drafts_dir, forms)

    assert drafts[0]["draft_subtitle"] == ""


def test_list_drafts_draft_subtitle_skips_empty_values(drafts_dir):
    """draft_subtitle omits fields whose saved value is empty or missing."""
    forms = {
        "my_form": {
            "title": "Formular",
            "fields": [
                {"name": "user", "in_draft_title": True},
                {"name": "dept", "in_draft_title": True},
            ],
        }
    }
    save_draft(drafts_dir, "my_form", {"user": "Erika", "dept": ""})

    drafts = list_drafts(drafts_dir, forms)

    assert drafts[0]["draft_subtitle"] == "Erika"


def test_list_drafts_sorted_newest_first(drafts_dir):
    """list_drafts returns drafts sorted by saved_at descending."""
    id1 = save_draft(drafts_dir, "form_a", {"order": "first"})
    id2 = save_draft(drafts_dir, "form_b", {"order": "second"})

    drafts = list_drafts(drafts_dir, {})
    ids = [d["draft_id"] for d in drafts]

    # The later-saved draft should come first
    assert ids.index(id2) < ids.index(id1)


def test_list_drafts_skips_corrupt_files(drafts_dir):
    """list_drafts skips corrupt JSON files and still returns valid ones."""
    corrupt_path = os.path.join(drafts_dir, "draft_corrupt.json")
    with open(corrupt_path, "w") as f:
        f.write("INVALID")

    save_draft(drafts_dir, "good_form", {"ok": "yes"})

    drafts = list_drafts(drafts_dir, {})
    assert len(drafts) == 1


def test_list_drafts_ignores_unrelated_files(drafts_dir):
    """list_drafts ignores files that do not match the draft_*.json pattern."""
    other_path = os.path.join(drafts_dir, "some_other_file.json")
    with open(other_path, "w") as f:
        json.dump({"draft_id": "x", "form_id": "y", "saved_at": "z", "form_data": {}}, f)

    save_draft(drafts_dir, "real_form", {})

    drafts = list_drafts(drafts_dir, {})
    assert len(drafts) == 1


# ---------------------------------------------------------------------------
# delete_draft
# ---------------------------------------------------------------------------

def test_delete_draft_removes_file(drafts_dir):
    """delete_draft removes the corresponding JSON file."""
    draft_id = save_draft(drafts_dir, "form_x", {"k": "v"})
    path = os.path.join(drafts_dir, f"draft_{draft_id}.json")
    assert os.path.isfile(path)

    delete_draft(drafts_dir, draft_id)

    assert not os.path.isfile(path)


def test_delete_draft_is_idempotent(drafts_dir):
    """delete_draft does not raise when called for a non-existent draft."""
    delete_draft(drafts_dir, "does_not_exist")  # should not raise


# ---------------------------------------------------------------------------
# collect_form_data
# ---------------------------------------------------------------------------

def test_collect_form_data_multiselect_stored_as_list():
    """collect_form_data stores multi-select values as a list, not a joined string."""
    form_def = {
        "fields": [
            {"type": "select", "name": "accessories", "multiple": True},
        ]
    }
    request_form = MultiDict([("accessories", "Netzteil"), ("accessories", "Maus")])

    result = collect_form_data(form_def, request_form)

    assert result["accessories"] == ["Netzteil", "Maus"]
    assert isinstance(result["accessories"], list)


def test_collect_form_data_multiselect_empty_list():
    """collect_form_data stores an empty list when no options are selected."""
    form_def = {
        "fields": [
            {"type": "select", "name": "accessories", "multiple": True},
        ]
    }
    request_form = MultiDict()

    result = collect_form_data(form_def, request_form)

    assert result["accessories"] == []


def test_collect_form_data_single_select_stored_as_string():
    """collect_form_data stores single-select values as a string (unchanged)."""
    form_def = {
        "fields": [
            {"type": "select", "name": "location", "multiple": False},
        ]
    }
    request_form = MultiDict([("location", "Berlin")])

    result = collect_form_data(form_def, request_form)

    assert result["location"] == "Berlin"
    assert isinstance(result["location"], str)


def test_list_drafts_draft_subtitle_with_list_value(drafts_dir):
    """list_drafts builds draft_subtitle correctly when in_draft_title field is a list."""
    forms = {
        "equipment": {
            "title": "Geräteübergabe",
            "fields": [
                {"name": "user", "in_draft_title": True},
                {"name": "accessories", "type": "select", "multiple": True, "in_draft_title": True},
            ],
        }
    }
    save_draft(drafts_dir, "equipment", {"user": "Max", "accessories": ["Netzteil", "Maus"]})

    drafts = list_drafts(drafts_dir, forms)

    assert drafts[0]["draft_subtitle"] == "Max, Netzteil, Maus"


# ---------------------------------------------------------------------------
# update_draft
# ---------------------------------------------------------------------------

def test_update_draft_overwrites_file(drafts_dir):
    """update_draft overwrites an existing draft file with new data."""
    draft_id = save_draft(drafts_dir, "my_form", {"field": "original"})

    update_draft(drafts_dir, draft_id, "my_form", {"field": "updated"})

    path = os.path.join(drafts_dir, f"draft_{draft_id}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["form_data"]["field"] == "updated"
    assert data["draft_id"] == draft_id
    assert data["form_id"] == "my_form"


def test_update_draft_returns_draft_id(drafts_dir):
    """update_draft returns the same draft_id that was passed."""
    draft_id = save_draft(drafts_dir, "my_form", {"x": "y"})
    returned_id = update_draft(drafts_dir, draft_id, "my_form", {"x": "z"})
    assert returned_id == draft_id


def test_update_draft_updates_saved_at(drafts_dir):
    """update_draft sets a new saved_at timestamp."""
    draft_id = save_draft(drafts_dir, "my_form", {"x": "y"})
    path = os.path.join(drafts_dir, f"draft_{draft_id}.json")
    with open(path, encoding="utf-8") as f:
        original_saved_at = json.load(f)["saved_at"]

    time.sleep(0.01)  # ensure timestamp changes

    update_draft(drafts_dir, draft_id, "my_form", {"x": "updated"})
    with open(path, encoding="utf-8") as f:
        updated_saved_at = json.load(f)["saved_at"]

    assert updated_saved_at >= original_saved_at


def test_update_draft_creates_file_if_not_exists(drafts_dir):
    """update_draft creates a new file if the draft_id does not yet exist."""
    update_draft(drafts_dir, "brand_new_id", "my_form", {"key": "value"})

    path = os.path.join(drafts_dir, "draft_brand_new_id.json")
    assert os.path.isfile(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["draft_id"] == "brand_new_id"
    assert data["form_data"]["key"] == "value"


# ---------------------------------------------------------------------------
# _build_draft_subtitle
# ---------------------------------------------------------------------------

def test_build_draft_subtitle_returns_joined_values():
    """_build_draft_subtitle joins in_draft_title field values with ', '."""
    form_def = {
        "fields": [
            {"name": "user", "in_draft_title": True},
            {"name": "notebook", "in_draft_title": True},
            {"name": "service_tag"},
        ]
    }
    result = _build_draft_subtitle(form_def, {"user": "Max", "notebook": "ThinkPad", "service_tag": "X1"})
    assert result == "Max, ThinkPad"


def test_build_draft_subtitle_skips_empty_values():
    """_build_draft_subtitle skips fields whose value is empty or missing."""
    form_def = {"fields": [{"name": "a", "in_draft_title": True}, {"name": "b", "in_draft_title": True}]}
    assert _build_draft_subtitle(form_def, {"a": "Hello", "b": ""}) == "Hello"


def test_build_draft_subtitle_handles_list_values():
    """_build_draft_subtitle joins list values with ', '."""
    form_def = {"fields": [{"name": "items", "in_draft_title": True}]}
    assert _build_draft_subtitle(form_def, {"items": ["A", "B"]}) == "A, B"


def test_build_draft_subtitle_empty_when_no_in_draft_title_fields():
    """_build_draft_subtitle returns '' when no field has in_draft_title: true."""
    form_def = {"fields": [{"name": "x"}, {"name": "y"}]}
    assert _build_draft_subtitle(form_def, {"x": "foo", "y": "bar"}) == ""


# ---------------------------------------------------------------------------
# draft_subtitle / form_title persisted in JSON
# ---------------------------------------------------------------------------

def test_save_draft_persists_draft_subtitle(drafts_dir):
    """save_draft stores draft_subtitle in the JSON when form_def is provided."""
    form_def = {
        "title": "My Form",
        "fields": [{"name": "user", "in_draft_title": True}],
    }
    draft_id = save_draft(drafts_dir, "my_form", {"user": "Erika"}, form_def)

    path = os.path.join(drafts_dir, f"draft_{draft_id}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["draft_subtitle"] == "Erika"
    assert data["form_title"] == "My Form"


def test_save_draft_without_form_def_omits_subtitle(drafts_dir):
    """save_draft does not add draft_subtitle when form_def is not provided."""
    draft_id = save_draft(drafts_dir, "my_form", {"user": "Erika"})

    path = os.path.join(drafts_dir, f"draft_{draft_id}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert "draft_subtitle" not in data
    assert "form_title" not in data


def test_update_draft_persists_draft_subtitle(drafts_dir):
    """update_draft stores draft_subtitle in the JSON when form_def is provided."""
    form_def = {
        "title": "Updated Form",
        "fields": [{"name": "device", "in_draft_title": True}],
    }
    draft_id = save_draft(drafts_dir, "my_form", {"device": "old"})
    update_draft(drafts_dir, draft_id, "my_form", {"device": "ThinkPad"}, form_def)

    path = os.path.join(drafts_dir, f"draft_{draft_id}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["draft_subtitle"] == "ThinkPad"
    assert data["form_title"] == "Updated Form"


def test_list_drafts_uses_persisted_draft_subtitle(drafts_dir):
    """list_drafts reads draft_subtitle from the JSON (not from forms dict)."""
    form_def = {
        "title": "Übergabe",
        "fields": [{"name": "user", "in_draft_title": True}],
    }
    save_draft(drafts_dir, "handover", {"user": "Max"}, form_def)

    # Pass an empty forms dict – subtitle must still come from persisted value
    drafts = list_drafts(drafts_dir, {})

    assert drafts[0]["draft_subtitle"] == "Max"
    assert drafts[0]["form_title"] == "Übergabe"


def test_list_drafts_falls_back_for_old_drafts_without_persisted_subtitle(drafts_dir):
    """list_drafts falls back to runtime calculation for old drafts without draft_subtitle."""
    forms = {
        "legacy_form": {
            "title": "Legacy",
            "fields": [{"name": "user", "in_draft_title": True}],
        }
    }
    # Write a draft JSON without draft_subtitle (simulates old format)
    old_draft = {
        "draft_id": "old123",
        "form_id": "legacy_form",
        "saved_at": "2024-01-01T00:00:00+00:00",
        "form_data": {"user": "OldUser"},
    }
    path = os.path.join(drafts_dir, "draft_old123.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(old_draft, f)

    drafts = list_drafts(drafts_dir, forms)

    assert drafts[0]["draft_subtitle"] == "OldUser"
    assert drafts[0]["form_title"] == "Legacy"
