import json
import os
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_SHEETS_SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _build_credentials() -> service_account.Credentials:
    raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw_json:
        raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON environment variable")

    account_info = json.loads(raw_json)
    return service_account.Credentials.from_service_account_info(
        account_info,
        scopes=GOOGLE_SHEETS_SCOPE,
    )


def fetch_sheet_rows(
    spreadsheet_id: str,
    sheet_name: str,
    header_row: int = 1,
    data_start_row: int | None = None,
) -> list[dict[str, str]]:
    if header_row < 1:
        raise ValueError("header_row must be >= 1")

    effective_data_start_row = data_start_row if data_start_row is not None else header_row + 1
    if effective_data_start_row < header_row:
        raise ValueError("data_start_row must be >= header_row")

    credentials = _build_credentials()
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    range_name = f"{sheet_name}!A{header_row}:ZZ"

    response: dict[str, Any] = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )

    values = response.get("values", [])
    if not values:
        return []

    headers = [h.strip() for h in values[0]]
    data_offset = effective_data_start_row - header_row
    rows = values[data_offset:]

    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        row_dict: dict[str, str] = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            row_dict[header] = row[index].strip() if index < len(row) else ""
        normalized_rows.append(row_dict)

    return normalized_rows


def fetch_sheet_titles(spreadsheet_id: str) -> list[str]:
    credentials = _build_credentials()
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    response: dict[str, Any] = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets.properties.title")
        .execute()
    )

    sheets = response.get("sheets", [])
    titles = []
    for sheet in sheets:
        properties = sheet.get("properties", {})
        title = properties.get("title", "").strip()
        if title:
            titles.append(title)
    return titles
