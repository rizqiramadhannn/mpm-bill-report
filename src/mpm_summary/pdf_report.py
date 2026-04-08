import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import OverdueRow


def _parse_rupiah(value: str) -> int:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits:
        return 0
    return int(digits)


def _format_rupiah(value: int) -> str:
    return f"Rp{value:,}".replace(",", ".")


def render_summary_pdf(
    rows: list[OverdueRow],
    output_path: str,
    report_title: str,
    total_label: str = "Belum Bayar",
) -> None:
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    doc = SimpleDocTemplate(output_path, pagesize=landscape(A4))
    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph(report_title, styles["Title"]))
    content.append(Spacer(1, 12))

    total_omset = sum(_parse_rupiah(row.omset) for row in rows)
    content.append(
        Paragraph(
            f"<b>Total {total_label} : {_format_rupiah(total_omset)} ({len(rows)} invoice)</b>",
            styles["Normal"],
        )
    )
    content.append(Spacer(1, 10))

    table_data = [[
        "No",
        "Customer Name",
        "Invoice Name",
        "Jumlah Pembayaran",
        "Jadwal Pembayaran",
        "Aging",
    ]]

    if rows:
        for row_number, row in enumerate(rows, start=1):
            aging_text = "-" if abs(row.aging_days) == 0 else f"{abs(row.aging_days)} hari"
            table_data.append(
                [
                    str(row_number),
                    row.customer_name or "-",
                    row.invoice_name or "-",
                    _format_rupiah(_parse_rupiah(row.omset)),
                    row.jadwal_pembayaran or "-",
                    aging_text,
                ]
            )
    else:
        table_data.append(["-", f"No {total_label.upper()} rows found", "-", "-", "-", "-"])

    table = Table(table_data, colWidths=[28, 170, 160, 130, 150, 80], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 1), (0, -1), "RIGHT"),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ("ALIGN", (5, 1), (5, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    content.append(table)

    doc.build(content)
