"""
email_sender.py — SendGrid integration for all ARIA form emails.
"""
import os
import base64
from datetime import datetime

import sendgrid
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName, FileType, Disposition
)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDER_EMAIL     = os.getenv("SENDER_EMAIL", "")
SCR_EMAIL        = os.getenv("SCR_EMAIL", "")


def _send_email(to_email: str, subject: str, html_body: str, attachments: list = None) -> bool:
    """
    Core send function. Returns True on success, raises on failure.
    attachments: list of dicts with keys: content (bytes), filename (str), mime_type (str)
    """
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_body,
    )

    if attachments:
        for att in attachments:
            encoded = base64.b64encode(att["content"]).decode()
            attachment = Attachment(
                FileContent(encoded),
                FileName(att["filename"]),
                FileType(att["mime_type"]),
                Disposition("attachment"),
            )
            message.add_attachment(attachment)

    response = sg.send(message)
    return response.status_code in (200, 201, 202)


async def send_occurrence_report(html: str, form_data: dict, to_email: str) -> bool:
    """Send a completed Occurrence Report via email."""
    date_str = form_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    time_str = form_data.get("time", "")
    unit = form_data.get("vehicle_number", "—")
    subject = f"EMS Occurrence Report — {date_str} {time_str} — Unit {unit}"
    return _send_email(to_email, subject, html)


async def send_teddy_bear_form(html: str, xml_content: str, form_data: dict, to_email: str) -> bool:
    """Send Teddy Bear form with XML attachment."""
    date_str = form_data.get("date_time", datetime.now().isoformat())[:10]
    subject = f"Teddy Bear Comfort Program — {date_str}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xml_filename = f"teddy_bear_{timestamp}.xml"

    attachments = [{
        "content": xml_content.encode("utf-8"),
        "filename": xml_filename,
        "mime_type": "application/xml",
    }]
    return _send_email(to_email, subject, html, attachments)


async def send_shift_change_request(html: str, form_data: dict) -> bool:
    """Send Shift Change Request to the hardcoded EMS scheduling address."""
    medic_name = f"{form_data.get('first_name', '')} {form_data.get('last_name', '')}".strip()
    action = form_data.get("requested_action", "Request")
    shift_date = form_data.get("shift_date", "—")
    subject = f"SCR — {action} — {medic_name} — {shift_date}"
    return _send_email(SCR_EMAIL, subject, html)
