from dataclasses import dataclass


@dataclass(frozen=True)
class MetricRule:
    metric_key: str
    title: str
    spreadsheet: str
    sheet_name: str
    column: str
    operation: str
    match_value: str = ""


@dataclass(frozen=True)
class MetricResult:
    metric_key: str
    title: str
    value: float
    operation: str


SUPPORTED_OPERATIONS = {
    "count_all",
    "count_non_empty",
    "count_equals",
    "sum",
}


def parse_rules(config_rows: list[dict[str, str]]) -> list[MetricRule]:
    rules: list[MetricRule] = []

    for row_number, row in enumerate(config_rows, start=2):
        metric_key = row.get("metric_key", "").strip()
        spreadsheet = row.get("spreadsheet", "").strip().upper() or "A"
        sheet_name = row.get("sheet_name", "").strip()
        column = row.get("column", "").strip()
        operation = row.get("operation", "").strip().lower()
        title = row.get("title", "").strip() or metric_key
        match_value = row.get("match_value", "").strip()

        if not metric_key:
            continue
        if spreadsheet != "A":
            raise ValueError(
                f"Invalid spreadsheet value at config row {row_number}. "
                "Only A is enabled for now."
            )
        if not sheet_name:
            raise ValueError(f"Missing sheet_name at config row {row_number}.")
        if not column:
            raise ValueError(f"Missing column at config row {row_number}.")
        if operation not in SUPPORTED_OPERATIONS:
            raise ValueError(
                f"Invalid operation '{operation}' at config row {row_number}. "
                f"Supported: {', '.join(sorted(SUPPORTED_OPERATIONS))}"
            )

        rules.append(
            MetricRule(
                metric_key=metric_key,
                title=title,
                spreadsheet=spreadsheet,
                sheet_name=sheet_name,
                column=column,
                operation=operation,
                match_value=match_value,
            )
        )

    if not rules:
        raise ValueError("No valid rules found in config sheet.")

    return rules


def evaluate_rule(rule: MetricRule, rows: list[dict[str, str]]) -> MetricResult:
    values = [row.get(rule.column, "") for row in rows]

    if rule.operation == "count_all":
        result = float(len(values))
    elif rule.operation == "count_non_empty":
        result = float(sum(1 for value in values if str(value).strip() != ""))
    elif rule.operation == "count_equals":
        result = float(sum(1 for value in values if str(value).strip() == rule.match_value))
    elif rule.operation == "sum":
        total = 0.0
        for value in values:
            cleaned = str(value).strip().replace(",", "")
            if not cleaned:
                continue
            try:
                total += float(cleaned)
            except ValueError as exc:
                raise ValueError(
                    f"Cannot convert '{value}' to number for rule '{rule.metric_key}'."
                ) from exc
        result = total
    else:
        raise ValueError(f"Unsupported operation: {rule.operation}")

    return MetricResult(
        metric_key=rule.metric_key,
        title=rule.title,
        value=result,
        operation=rule.operation,
    )
