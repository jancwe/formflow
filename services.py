from typing import Dict, Any
from werkzeug.datastructures import MultiDict

def collect_form_data(form_def: Dict[str, Any], request_form: MultiDict) -> Dict[str, Any]:
    """Sammelt und normalisiert Formulardaten aus einem Flask-Request."""
    form_data: Dict[str, Any] = {}
    for field in form_def.get('fields', []):
        field_name = field.get('name')
        if not field_name:
            continue

        # Bei 'select' mit 'multiple: true' muss getlist() verwendet werden
        if field.get('type') == 'select' and field.get('multiple'):
            selected_options = request_form.getlist(field_name)
            form_data[field_name] = ", ".join(selected_options)
        else:
            form_data[field_name] = request_form.get(field_name, '')
    return form_data
