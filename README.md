# Google Sheets Tagihan Report

This project reads both Spreadsheet A and Spreadsheet B from Google Sheets and generates 2 PDFs:

- `Tagihan Invoice MPM ddmmyyyy.pdf` (from Sheet A)
- `Tagihan Supplier MPM ddmmyyyy.pdf` (from Sheet B)

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Environment variables

Required:

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `SPREADSHEET_A_ID`
- `SPREADSHEET_B_ID`

Optional:

- `SHEET_A_NAME` (if empty, first tab of Spreadsheet A is used)
- `SHEET_A_HEADER_ROW` (default: `1`)
- `SHEET_A_DATA_START_ROW` (default: `SHEET_A_HEADER_ROW + 1`)
- `SHEET_B_NAME` (default: `DATA PERINVOICE`)
- `SHEET_B_HEADER_ROW` (default: `4`)
- `SHEET_B_DATA_START_ROW` (default: `6`)
- `OUTPUT_DIR` (default: `output`)
- `STATUS_COLUMN_NAME` (exact header override)
- `AGING_COLUMN_NAME` (exact header override)
- `CUSTOMER_NAME_COLUMN_NAME` (exact header override)
- `INVOICE_NAME_COLUMN_NAME` (exact header override)
- `OMSET_COLUMN_NAME` (exact header override)
- `JADWAL_PEMBAYARAN_COLUMN_NAME` (exact header override)
- `BREVO_SMTP_HOST` (default: `smtp-relay.brevo.com`)
- `BREVO_SMTP_PORT` (default: `587`)
- `BREVO_SMTP_USER` (Brevo SMTP login)
- `BREVO_SMTP_PASS` (Brevo SMTP key/password)
- `EMAIL_FROM` (must be verified sender in Brevo)
- `EMAIL_TO` (comma-separated recipient list)

## Filtering rules

Sheet A:
- Status must be `BELUM BAYAR`
- Aging comes from the sheet `Aging` column

Sheet B:
- Status must be `BELUM LUNAS`
- Uses columns: Supplier, No Invoice, Remaining Payment, Payment Deadline
- Aging is calculated as `today - payment deadline` (minimum `0`)

## Run locally

```bash
python main.py
```

If SMTP vars are present, the script automatically emails both generated PDFs.
When new dated PDFs are generated, older PDFs with the same report title are removed automatically.

## API (Vercel-ready)

- `GET /api/health`
- `GET /api/generate`

Important: share both spreadsheets with your service account email.
