import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from werkzeug.datastructures import MultiDict

logger = logging.getLogger(__name__)

def collect_form_data(form_def: Dict[str, Any], request_form: MultiDict) -> Dict[str, Any]:
    """Sammelt und normalisiert Formulardaten aus einem Flask-Request."""
    form_data: Dict[str, Any] = {}
    for field in form_def.get('fields', []):
        field_name = field.get('name')
        if not field_name:
            continue

        # Bei 'select' mit 'multiple: true' getlist() verwenden und als Liste speichern
        if field.get('type') == 'select' and field.get('multiple'):
            form_data[field_name] = request_form.getlist(field_name)
        else:
            form_data[field_name] = request_form.get(field_name, '')
    return form_data


def save_draft(drafts_dir: str, form_id: str, form_data: dict) -> str:
    """Speichert einen Entwurf als JSON und gibt die draft_id zurück."""
    draft_id = uuid.uuid4().hex
    draft = {
        "draft_id": draft_id,
        "form_id": form_id,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "form_data": form_data,
    }
    path = os.path.join(drafts_dir, f"draft_{draft_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(draft, f, ensure_ascii=False)
    return draft_id


def load_draft(drafts_dir: str, draft_id: str) -> dict:
    """Lädt einen Entwurf aus einer JSON-Datei."""
    path = os.path.join(drafts_dir, f"draft_{draft_id}.json")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_drafts(drafts_dir: str, forms: dict) -> list:
    """Liest alle Entwürfe aus dem drafts/-Verzeichnis und gibt sie als Liste zurück."""
    drafts = []
    if not os.path.isdir(drafts_dir):
        return drafts
    for filename in os.listdir(drafts_dir):
        if not (filename.startswith('draft_') and filename.endswith('.json')):
            continue
        path = os.path.join(drafts_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                draft = json.load(f)
            form_def = forms.get(draft.get('form_id'), {})
            form_data = draft.get('form_data', {})
            subtitle_parts = []
            for field in form_def.get('fields', []):
                if not field.get('in_draft_title'):
                    continue
                value = form_data.get(field['name'])
                if not value:
                    continue
                if isinstance(value, list):
                    subtitle_parts.append(", ".join(value))
                else:
                    subtitle_parts.append(value)
            drafts.append({
                "draft_id": draft.get('draft_id'),
                "form_id": draft.get('form_id'),
                "form_title": form_def.get('title', draft.get('form_id', '')),
                "draft_subtitle": ", ".join(subtitle_parts),
                "saved_at": draft.get('saved_at'),
            })
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Entwurf konnte nicht geladen werden ({filename}): {e}")
    drafts.sort(key=lambda d: d.get('saved_at', ''), reverse=True)
    return drafts


def delete_draft(drafts_dir: str, draft_id: str) -> None:
    """Löscht eine Entwurfs-Datei."""
    path = os.path.join(drafts_dir, f"draft_{draft_id}.json")
    if os.path.exists(path):
        os.remove(path)
