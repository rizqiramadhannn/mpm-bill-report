import os

from src.mpm_summary.pipeline import run_pipeline
from src.mpm_summary.email_sender import send_report_email


if __name__ == "__main__":
    pdf_paths = run_pipeline()
    for pdf_path in pdf_paths:
        print(f"Summary PDF created at: {pdf_path}")

    # Send email only when SMTP credentials are provided.
    if os.getenv("BREVO_SMTP_USER", "").strip() and os.getenv("BREVO_SMTP_PASS", "").strip():
        send_report_email(pdf_paths)
        print("Report email sent.")
    else:
        print("Email not sent (missing BREVO_SMTP_USER or BREVO_SMTP_PASS).")
