import os
import json
import logging
from typing import Dict
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, config: Dict):
        self.config = config
        self.output_dir = config["report"]["output_dir"]
        self.template_env = Environment(loader=FileSystemLoader("templates"))
        self.template_env.filters["tojson"] = lambda v, indent=2: json.dumps(v, indent=indent)

    def generate_html_report(self, metrics: Dict, screenshot_path: str) -> str:
        try:
            template = self.template_env.get_template("report_template.html")
            html_content = template.render(metrics=metrics, screenshot_path=os.path.abspath(screenshot_path))
            os.makedirs(self.output_dir, exist_ok=True)
            report_path = os.path.join(self.output_dir, f"{metrics['tenant_id']}_turbo_report.html")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Report saved: {report_path}")
            return report_path
        except Exception as e:
            logger.error(f"Report generation failed for {metrics['tenant_id']}: {e}")
            raise
