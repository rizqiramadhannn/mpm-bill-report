from dataclasses import dataclass


@dataclass(frozen=True)
class OverdueRow:
    aging_days: int
    customer_name: str
    invoice_name: str
    omset: str
    pembayaran: str
    jadwal_pembayaran: str

