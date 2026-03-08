import os
import logging
from datetime import date
from typing import Dict, Any, Optional
from weasyprint import HTML
# Environment + FileSystemLoader is used instead of Template() directly so that
# compiled templates are cached in memory and not re-parsed on every request.
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger(__name__)

_DEFAULT_PDF_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pdf_templates')


class _FormatMap(dict):
    """A dict subclass that returns the placeholder unchanged for missing keys."""
    def __missing__(self, key: str) -> str:
        return '{' + key + '}'


def _resolve_signature_label(template_str: str, form_data: Dict[str, Any], date_today: str) -> str:
    """Interpolate {placeholder} values in a signature_label string.

    Placeholders matching keys in form_data or the special ``{date_today}``
    are replaced with their corresponding values.  Unknown placeholders are
    left intact (e.g. ``{unknown}`` stays ``{unknown}``).
    """
    context = _FormatMap(form_data)
    context['date_today'] = date_today
    return template_str.format_map(context)


class PdfGenerator:
    """Klasse zur Generierung von PDFs aus Formulardaten mittels WeasyPrint."""
    
    def __init__(self, templates_dir: str = _DEFAULT_PDF_TEMPLATES_DIR):
        self.templates_dir = templates_dir
        self._env = Environment(
            loader=FileSystemLoader(templates_dir),
            auto_reload=False,
        )

    def generate(self, form_def: Dict[str, Any], form_data: Dict[str, Any], output_filename: str, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Generiert ein PDF basierend auf einem HTML-Template und WeasyPrint.
        
        Args:
            form_def: Die YAML-Definition des Formulars als Dictionary.
            form_data: Die vom Benutzer eingegebenen Daten.
            output_filename: Der absolute oder relative Pfad, unter dem das PDF gespeichert werden soll.
            config: Globale Konfiguration (CI-Farben, Firmenname etc.)
        """
        if config is None:
            config = {}
            
        # Template-Name aus YAML lesen oder Standard verwenden
        template_name = form_def.get('pdf_template', 'default_pdf.html')

        # Fallback, falls das Template nicht existiert
        try:
            template = self._env.get_template(template_name)
        except TemplateNotFound:
            logger.warning(f"PDF-Template {template_name} nicht gefunden. Verwende default_pdf.html")
            template = self._env.get_template('default_pdf.html')

        date_today_str = date.today().strftime("%d.%m.%Y")
        resolved_fields = self._resolve_signature_labels(
            form_def.get('fields', []), form_data, date_today_str
        )

        html_content = template.render(
            form_title=form_def.get('title', 'Formular'),
            fields=resolved_fields,
            form_data=form_data,
            date_today=date_today_str,
            uuid=os.path.basename(output_filename).replace('temp_', '').replace('.pdf', ''),
            config=config
        )
        
        # HTML zu PDF konvertieren
        HTML(string=html_content).write_pdf(output_filename)

    def _resolve_signature_labels(
        self,
        fields: list,
        form_data: Dict[str, Any],
        date_today: str,
    ) -> list:
        """Return a copy of *fields* with ``signature_label_resolved`` set for signature fields.

        The original list and its dicts are not modified (YAML definitions may be cached).
        """
        resolved = []
        for field in fields:
            if field.get('type') == 'signature' and field.get('signature_label'):
                field = dict(field)
                field['signature_label_resolved'] = _resolve_signature_label(
                    field['signature_label'], form_data, date_today
                )
            resolved.append(field)
        return resolved
