import os
import base64
import ssl
import logging
from typing import Dict, List

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail,
    Email,
    To,
    Content,
    Attachment,
    FileContent,
    FileName,
    FileType,
    Disposition
)

logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(self, config: Dict):
        self.api_key = os.environ.get("SENDGRID_API_KEY")

        if not self.api_key:
            raise RuntimeError("SENDGRID_API_KEY is not set")

    def send_combined_report(self, recipients: List[str], results: List[Dict]):
        self._send_combined_via_sendgrid(recipients, results)

    def _send_combined_via_sendgrid(self, recipients, results):
        if not results:
            raise ValueError("No results to send")

        subject = f"[Turbo Report] All Tenants | {results[0]['metrics']['report_generated_at']}"

        html_parts = ["""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <h2>Turbo Performance Report</h2>
        """]

        attachments = []
        image_counter = 0

        for res in results:
            metrics = res["metrics"]
            screenshot_path = res["screenshot_path"]

            if not os.path.exists(screenshot_path):
                logger.warning("Screenshot missing: %s", screenshot_path)
                continue

            img_id = f"img_{image_counter}"

            html_parts.append(f"""
            <div style="background:white; padding:20px; margin-bottom:20px; border-radius:10px;">
                <h3>{metrics['tenant_name']}</h3>
                <p>{metrics['environment']} | {metrics['report_generated_at']}</p>
                <img src="cid:{img_id}" style="width:100%; border:1px solid #ddd;">
            </div>
            """)

            with open(screenshot_path, "rb") as f:
                encoded_image = base64.b64encode(f.read()).decode()

            attachment = Attachment(
                FileContent(encoded_image),
                FileName(os.path.basename(screenshot_path)),
                FileType("image/png"),
                Disposition("inline")
            )

            attachment.content_id = img_id
            attachments.append(attachment)
            image_counter += 1

        html_parts.append("</body></html>")
        html_content = "\n".join(html_parts)

        cleaned_recipients = [To(email) for email in recipients if email and "@" in email]

        if not cleaned_recipients:
            raise ValueError("No valid recipients found")

        message = Mail(
            from_email=Email("grafana_report@conga.com", "Devops Conga"),
            to_emails=cleaned_recipients,
            subject=subject,
            html_content=Content("text/html", html_content)
        )

        for attachment in attachments:
            message.add_attachment(attachment)

        ssl._create_default_https_context = ssl._create_unverified_context

        sg = SendGridAPIClient(self.api_key)
        response = sg.send(message)

        if response.status_code in [200, 201, 202]:
            logger.info("Email sent successfully")
            logger.info("SendGrid status: %s", response.status_code)
        else:
            logger.error("Unexpected SendGrid response: %s", response.status_code)
            logger.error(response.body)