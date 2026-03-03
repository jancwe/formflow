import json
import os
import pytest

from services import save_draft, load_draft, list_drafts, delete_draft


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
    forms = {"my_form": {"title": "Mein Formular"}}
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
