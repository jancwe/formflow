import os
import logging
from datetime import date
from typing import Dict, Any
from weasyprint import HTML
from jinja2 import Template

logger = logging.getLogger(__name__)

class PdfGenerator:
    """Klasse zur Generierung von PDFs aus Formulardaten mittels WeasyPrint."""
    
    def __init__(self, templates_dir: str = 'pdf_templates'):
        self.templates_dir = templates_dir

    def generate(self, form_def: Dict[str, Any], form_data: Dict[str, Any], output_filename: str) -> None:
        """
        Generiert ein PDF basierend auf einem HTML-Template und WeasyPrint.
        
        Args:
            form_def: Die YAML-Definition des Formulars als Dictionary.
            form_data: Die vom Benutzer eingegebenen Daten.
            output_filename: Der absolute oder relative Pfad, unter dem das PDF gespeichert werden soll.
        """
        # Template-Name aus YAML lesen oder Standard verwenden
        template_name = form_def.get('pdf_template', 'default_pdf.html')
        template_path = os.path.join(self.templates_dir, template_name)
        
        # Fallback, falls das Template nicht existiert
        if not os.path.exists(template_path):
            logger.warning(f"PDF-Template {template_name} nicht gefunden. Verwende default_pdf.html")
            template_path = os.path.join(self.templates_dir, 'default_pdf.html')
            
        # HTML mit Jinja2 rendern
        # Da wir nicht im app-Kontext sind, wenn wir render_template mit einem absoluten Pfad aufrufen,
        # lesen wir die Datei manuell und nutzen Jinja2 direkt
        with open(template_path, 'r', encoding='utf-8') as f:
            template = Template(f.read())
            
        html_content = template.render(
            form_title=form_def.get('title', 'Formular'),
            fields=form_def.get('fields', []),
            form_data=form_data,
            date_today=date.today().strftime("%d.%m.%Y")
        )
        
        # HTML zu PDF konvertieren
        HTML(string=html_content).write_pdf(output_filename)
