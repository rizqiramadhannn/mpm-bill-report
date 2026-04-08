import os
import re
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

from .google_sheets import fetch_sheet_rows, fetch_sheet_titles
from .models import OverdueRow
from .pdf_report import render_summary_pdf


def _normalize_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


def _find_header_key(row: dict[str, str], candidates: list[str]) -> str | None:
    normalized_map = {_normalize_header(key): key for key in row.keys() if key}
    for candidate in candidates:
        found = normalized_map.get(_normalize_header(candidate))
        if found:
            return found

    # Fuzzy fallback: accept headers that contain the candidate token.
    normalized_keys = list(normalized_map.keys())
    for candidate in candidates:
        token = _normalize_header(candidate)
        for normalized_key in normalized_keys:
            if token and token in normalized_key:
                return normalized_map[normalized_key]
    return None


def _parse_aging_days(value: str) -> int:
    match = re.search(r"-?\d+", str(value))
    if not match:
        return 0
    return int(match.group(0))


def _parse_date(value: str) -> date | None:
    raw = str(value).strip()
    if not raw:
        return None

    candidate = raw.split(" ")[0]
    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None


def _aging_from_deadline(deadline_value: str) -> int:
    deadline = _parse_date(deadline_value)
    if deadline is None:
        return 0
    return max(0, (date.today() - deadline).days)


def _pick_sheet_name(spreadsheet_id: str, explicit_name: str | None, label: str) -> str:
    if explicit_name:
        return explicit_name

    titles = fetch_sheet_titles(spreadsheet_id)
    if not titles:
        raise ValueError(f"Spreadsheet {label} has no visible sheets.")
    return titles[0]


def _extract_overdue_rows(
    rows: list[dict[str, str]],
    label: str,
    column_overrides: dict[str, str],
) -> list[OverdueRow]:
    if not rows:
        return []

    sample = rows[0]
    status_key = column_overrides["status"] or _find_header_key(
        sample, ["Status", "Status Pembayaran", "Payment Status", "Keterangan"]
    )
    aging_key = column_overrides["aging"] or _find_header_key(
        sample, ["Aging", "Days Overdue", "Hari Keterlambatan", "Lewat Jatuh Tempo"]
    )
    customer_key = column_overrides["customer_name"] or _find_header_key(
        sample, ["Customer Name", "Nama Customer", "Customer", "Nama"]
    )
    invoice_key = column_overrides["invoice_name"] or _find_header_key(
        sample, ["Invoice Name", "Nama Invoice", "No Invoice", "Invoice", "Nomor Invoice"]
    )
    omset_key = column_overrides["omset"] or _find_header_key(
        sample, ["Omset", "Sales", "Nilai Invoice", "Total Invoice"]
    )
    jadwal_key = column_overrides["jadwal_pembayaran"] or _find_header_key(
        sample, ["Jadwal Pembayaran", "Payment Schedule", "Jatuh Tempo", "Due Date"]
    )

    if not status_key:
        raise ValueError(
            f"Cannot find Status column in spreadsheet {label}. "
            "Set STATUS_COLUMN_NAME in .env to the exact header text. "
            f"Detected headers: {', '.join(sample.keys())}"
        )
    if not aging_key:
        raise ValueError(
            f"Cannot find Aging column in spreadsheet {label}. "
            "Set AGING_COLUMN_NAME in .env to the exact header text. "
            f"Detected headers: {', '.join(sample.keys())}"
        )

    output: list[OverdueRow] = []
    for row in rows:
        status_value = row.get(status_key, "").strip().upper()
        if status_value != "BELUM BAYAR":
            continue

        output.append(
            OverdueRow(
                aging_days=_parse_aging_days(row.get(aging_key, "")),
                customer_name=row.get(customer_key or "", "").strip(),
                invoice_name=row.get(invoice_key or "", "").strip(),
                omset=row.get(omset_key or "", "").strip(),
                pembayaran="",
                jadwal_pembayaran=row.get(jadwal_key or "", "").strip(),
            )
        )

    return sorted(output, key=lambda item: item.aging_days, reverse=True)


def _extract_supplier_rows(
    rows: list[dict[str, str]],
    column_overrides: dict[str, str],
) -> list[OverdueRow]:
    if not rows:
        return []

    sample = rows[0]
    status_key = column_overrides["status"] or _find_header_key(
        sample, ["Status", "Status Pembayaran", "Payment Status"]
    )
    supplier_key = column_overrides["customer_name"] or _find_header_key(
        sample, ["Supplier", "Nama Supplier", "Vendor"]
    )
    invoice_key = column_overrides["invoice_name"] or _find_header_key(
        sample, ["No Invoice", "Nomor Invoice", "Invoice"]
    )
    remaining_payment_key = column_overrides["omset"] or _find_header_key(
        sample, ["Remaining Payment", "Sisa Pembayaran", "Outstanding", "Outstanding Payment"]
    )
    deadline_key = column_overrides["jadwal_pembayaran"] or _find_header_key(
        sample, ["Payment Deadline", "Jatuh Tempo", "Due Date", "Tanggal Jatuh Tempo"]
    )

    if not status_key:
        raise ValueError(
            "Cannot find Status column in spreadsheet B. "
            f"Detected headers: {', '.join(sample.keys())}"
        )
    if not supplier_key:
        raise ValueError(
            "Cannot find Supplier column in spreadsheet B. "
            f"Detected headers: {', '.join(sample.keys())}"
        )
    if not invoice_key:
        raise ValueError(
            "Cannot find No Invoice column in spreadsheet B. "
            f"Detected headers: {', '.join(sample.keys())}"
        )
    if not remaining_payment_key:
        raise ValueError(
            "Cannot find Remaining Payment column in spreadsheet B. "
            f"Detected headers: {', '.join(sample.keys())}"
        )
    if not deadline_key:
        raise ValueError(
            "Cannot find Payment Deadline column in spreadsheet B. "
            f"Detected headers: {', '.join(sample.keys())}"
        )

    output: list[OverdueRow] = []
    for row in rows:
        status_value = row.get(status_key, "").strip().upper()
        if status_value not in {"BELUM LUNAS", "DP"}:
            continue

        deadline = row.get(deadline_key, "").strip()
        output.append(
            OverdueRow(
                aging_days=_aging_from_deadline(deadline),
                customer_name=row.get(supplier_key, "").strip(),
                invoice_name=row.get(invoice_key, "").strip(),
                omset=row.get(remaining_payment_key, "").strip(),
                pembayaran="",
                jadwal_pembayaran=deadline,
            )
        )

    return sorted(output, key=lambda item: item.aging_days, reverse=True)


def _build_output_path(directory: str, title: str, date_token: str) -> str:
    filename = f"{title} {date_token}.pdf"
    return str(Path(directory) / filename)


def _cleanup_old_reports(directory: str, title: str, keep_path: str) -> None:
    output_dir = Path(directory)
    if not output_dir.exists():
        return

    keep_resolved = Path(keep_path).resolve()
    pattern = f"{title} *.pdf"
    for path in output_dir.glob(pattern):
        try:
            if path.resolve() == keep_resolved:
                continue
            path.unlink(missing_ok=True)
        except OSError:
            # Ignore cleanup failures and continue report generation.
            continue


def run_pipeline(output_pdf_path_override: str | None = None) -> list[str]:
    load_dotenv()

    spreadsheet_a_id = os.getenv("SPREADSHEET_A_ID")
    spreadsheet_b_id = os.getenv("SPREADSHEET_B_ID")
    sheet_a_name = os.getenv("SHEET_A_NAME")
    sheet_b_name = os.getenv("SHEET_B_NAME", "DATA PERINVOICE")
    sheet_a_header_row = int(os.getenv("SHEET_A_HEADER_ROW", "1"))
    sheet_b_header_row = int(os.getenv("SHEET_B_HEADER_ROW", "4"))
    sheet_a_data_start_row_env = os.getenv("SHEET_A_DATA_START_ROW", "").strip()
    sheet_b_data_start_row_env = os.getenv("SHEET_B_DATA_START_ROW", "6").strip()
    sheet_a_data_start_row = int(sheet_a_data_start_row_env) if sheet_a_data_start_row_env else None
    sheet_b_data_start_row = int(sheet_b_data_start_row_env) if sheet_b_data_start_row_env else None
    output_directory = os.getenv("OUTPUT_DIR", "output")
    date_token = datetime.now().strftime("%d%m%Y")
    column_overrides = {
        "status": os.getenv("STATUS_COLUMN_NAME", "").strip(),
        "aging": os.getenv("AGING_COLUMN_NAME", "").strip(),
        "customer_name": os.getenv("CUSTOMER_NAME_COLUMN_NAME", "").strip(),
        "invoice_name": os.getenv("INVOICE_NAME_COLUMN_NAME", "").strip(),
        "omset": os.getenv("OMSET_COLUMN_NAME", "").strip(),
        "jadwal_pembayaran": os.getenv("JADWAL_PEMBAYARAN_COLUMN_NAME", "").strip(),
    }

    if not spreadsheet_a_id:
        raise ValueError("Missing SPREADSHEET_A_ID")
    if not spreadsheet_b_id:
        raise ValueError("Missing SPREADSHEET_B_ID")

    resolved_sheet_a_name = _pick_sheet_name(spreadsheet_a_id, sheet_a_name, "A")
    rows_a = fetch_sheet_rows(
        spreadsheet_a_id,
        resolved_sheet_a_name,
        header_row=sheet_a_header_row,
        data_start_row=sheet_a_data_start_row,
    )

    output_paths: list[str] = []
    rows_a_overdue = _extract_overdue_rows(rows_a, "A", column_overrides)
    output_a_path = output_pdf_path_override or _build_output_path(
        output_directory,
        "Tagihan Invoice MPM",
        date_token,
    )
    _cleanup_old_reports(output_directory, "Tagihan Invoice MPM", output_a_path)
    render_summary_pdf(rows_a_overdue, output_a_path, "Tagihan Invoice MPM", "Belum Bayar")
    output_paths.append(output_a_path)

    resolved_sheet_b_name = _pick_sheet_name(spreadsheet_b_id, sheet_b_name, "B")
    rows_b = fetch_sheet_rows(
        spreadsheet_b_id,
        resolved_sheet_b_name,
        header_row=sheet_b_header_row,
        data_start_row=sheet_b_data_start_row,
    )
    rows_b_overdue = _extract_supplier_rows(rows_b, column_overrides)
    output_b_path = _build_output_path(
        output_directory,
        "Tagihan Supplier MPM",
        date_token,
    )
    _cleanup_old_reports(output_directory, "Tagihan Supplier MPM", output_b_path)
    render_summary_pdf(rows_b_overdue, output_b_path, "Tagihan Supplier MPM", "Belum Lunas")
    output_paths.append(output_b_path)

    return output_paths
