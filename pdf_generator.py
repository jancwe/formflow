import os
import logging
from datetime import date
from typing import Dict, Any, Optional
from weasyprint import HTML
# Environment + FileSystemLoader is used instead of Template() directly so that
# compiled templates are cached in memory and not re-parsed on every request.
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger(__name__)

class PdfGenerator:
    """Klasse zur Generierung von PDFs aus Formulardaten mittels WeasyPrint."""
    
    def __init__(self, templates_dir: str = 'pdf_templates'):
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
            
        html_content = template.render(
            form_title=form_def.get('title', 'Formular'),
            fields=form_def.get('fields', []),
            form_data=form_data,
            date_today=date.today().strftime("%d.%m.%Y"),
            uuid=os.path.basename(output_filename).replace('temp_', '').replace('.pdf', ''),
            config=config
        )
        
        # HTML zu PDF konvertieren
        HTML(string=html_content).write_pdf(output_filename)
