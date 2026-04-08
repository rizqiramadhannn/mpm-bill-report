import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing {name} for email sending.")
    return value


def _parse_recipients(raw: str) -> list[str]:
    recipients = [item.strip() for item in raw.split(",")]
    return [item for item in recipients if item]


def send_report_email(attachments: list[str]) -> None:
    smtp_host = os.getenv("BREVO_SMTP_HOST", "smtp-relay.brevo.com").strip()
    smtp_port = int(os.getenv("BREVO_SMTP_PORT", "587").strip())
    smtp_user = _required("BREVO_SMTP_USER")
    smtp_pass = _required("BREVO_SMTP_PASS")
    email_from = _required("EMAIL_FROM")
    email_to = _required("EMAIL_TO")
    recipients = _parse_recipients(email_to)
    if not recipients:
        raise ValueError("EMAIL_TO must contain at least one recipient email.")

    subject_date = datetime.now().strftime("%d/%m/%Y")
    message = EmailMessage()
    message["From"] = email_from
    message["To"] = ", ".join(recipients)
    message["Subject"] = f"Tagihan Report MPM - {subject_date}"
    message.set_content(
        "Terlampir laporan tagihan:\n"
        "- Tagihan Invoice\n"
        "- Tagihan Supplier"
    )
    message.add_alternative(
        f"""\
<html>
  <body style="font-family: Arial, Helvetica, sans-serif; color: #1f2937; line-height: 1.5;">
    <p style="margin: 0 0 12px 0;">Terlampir laporan tagihan:</p>
    <ul style="margin: 0 0 14px 20px; padding: 0;">
      <li>Tagihan Invoice</li>
      <li>Tagihan Supplier</li>
    </ul>
    <p style="margin: 0; color: #6b7280; font-size: 12px;">Tanggal: {subject_date}</p>
  </body>
</html>
""",
        subtype="html",
    )

    for file_path in attachments:
        path = Path(file_path)
        if not path.exists():
            continue
        payload = path.read_bytes()
        message.add_attachment(
            payload,
            maintype="application",
            subtype="pdf",
            filename=path.name,
        )

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(message)
