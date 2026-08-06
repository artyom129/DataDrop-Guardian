from __future__ import annotations
import csv, json, re
from datetime import datetime
from pathlib import Path

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class ParseError(Exception):
    pass

def load_records(path: Path):
    try:
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                if not reader.fieldnames:
                    raise ParseError("CSV header is missing")
                return "csv", [dict(r) for r in reader]
        if path.suffix.lower() == ".json":
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                data = data.get("items", data.get("records", data))
            if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
                raise ParseError("JSON must contain a list of objects")
            return "json", [dict(x) for x in data]
    except (OSError, UnicodeError, json.JSONDecodeError, csv.Error) as exc:
        raise ParseError(str(exc)) from exc
    raise ParseError("Only CSV and JSON files are supported")

def _blank(value):
    return value is None or str(value).strip() == ""

def _typed(value, kind):
    text = str(value).strip()
    try:
        if kind == "integer":
            return True, float(int(text))
        if kind == "decimal":
            return True, float(text.replace(",", "."))
        if kind == "date":
            datetime.strptime(text, "%Y-%m-%d")
            return True, None
        if kind == "email":
            return bool(EMAIL.match(text)), None
        if kind == "text":
            return True, None
    except (ValueError, TypeError):
        return False, None
    return False, None

def validate(records, pipeline):
    errors, valid, seen = [], [], set()
    duplicates = 0
    expected = {f.name for f in pipeline.fields}
    if records:
        missing = expected - set(records[0].keys())
        for name in sorted(missing):
            errors.append({
                "row_number": None, "field_name": name,
                "error_code": "missing_column",
                "message": f"Required column '{name}' is missing",
                "raw_value": None,
            })
        if missing:
            return [], errors, 0
    for row_number, row in enumerate(records, start=2):
        row_errors = []
        for rule in pipeline.fields:
            value = row.get(rule.name)
            if _blank(value):
                if rule.required:
                    row_errors.append({
                        "row_number": row_number, "field_name": rule.name,
                        "error_code": "required",
                        "message": f"'{rule.name}' is required",
                        "raw_value": value,
                    })
                continue
            ok, number = _typed(value, rule.type)
            if not ok:
                row_errors.append({
                    "row_number": row_number, "field_name": rule.name,
                    "error_code": "invalid_type",
                    "message": f"'{rule.name}' must be {rule.type}",
                    "raw_value": value,
                })
            elif number is not None and rule.minimum is not None and number < rule.minimum:
                row_errors.append({
                    "row_number": row_number, "field_name": rule.name,
                    "error_code": "below_minimum",
                    "message": f"'{rule.name}' must be at least {rule.minimum:g}",
                    "raw_value": value,
                })
        if pipeline.duplicate_key:
            key = tuple(str(row.get(k, "")).strip() for k in pipeline.duplicate_key)
            if key in seen:
                duplicates += 1
                row_errors.append({
                    "row_number": row_number,
                    "field_name": ",".join(pipeline.duplicate_key),
                    "error_code": "duplicate_row",
                    "message": f"Duplicate key: {' | '.join(key)}",
                    "raw_value": " | ".join(key),
                })
            else:
                seen.add(key)
        if row_errors:
            errors.extend(row_errors)
        else:
            valid.append(row)
    return valid, errors, duplicates
