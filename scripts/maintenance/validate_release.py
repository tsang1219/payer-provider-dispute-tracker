#!/usr/bin/env python3
"""Validate canonical dispute data and all release-facing derived artifacts."""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "data/primary/disputes_enriched.csv"
VALID_STATUSES = {"Resolved", "OON-Ongoing", "OON-Permanent"}
DATE_FIELDS = ("first_media_date", "deadline_date", "oon_effective_date", "resolution_date")


def csv_rows(path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-json", type=Path, default=ROOT / "site/src/data/disputes.json")
    parser.add_argument("--public-csv", type=Path, default=ROOT / "site/public/disputes.csv")
    parser.add_argument("--flourish", type=Path, default=ROOT / "data/derived/visualizations/disputes_flourish_timeslider.csv")
    parser.add_argument("--map-ready", type=Path, default=ROOT / "data/derived/visualizations/disputes_map_ready.csv")
    args = parser.parse_args(argv)

    errors, warnings = [], []
    rows = csv_rows(CANONICAL)
    ids = [r.get("dispute_id", "").strip() for r in rows]
    if not rows:
        errors.append("canonical dataset is empty")
    if any(not value for value in ids):
        errors.append("canonical contains a blank dispute_id")
    if len(ids) != len(set(ids)):
        errors.append("canonical contains duplicate dispute_id values")

    for line, row in enumerate(rows, start=2):
        for field in ("system_name", "insurer_name", "first_media_date", "primary_source_url"):
            if not row.get(field, "").strip():
                errors.append(f"line {line}: missing {field}")
        status = row.get("outcome_status", "").strip()
        if status not in VALID_STATUSES:
            errors.append(f"line {line}: invalid outcome_status {status!r}")
        parsed = {}
        for field in DATE_FIELDS:
            value = row.get(field, "").strip()
            if not value:
                continue
            try:
                parsed[field] = datetime.strptime(value[:10], "%Y-%m-%d").date()
            except ValueError:
                errors.append(f"line {line}: invalid {field} {value!r}")
        if parsed.get("resolution_date") and parsed.get("first_media_date") and parsed["resolution_date"] < parsed["first_media_date"]:
            errors.append(f"line {line}: resolution_date precedes first_media_date")
        if status == "Resolved" and not row.get("resolution_date", "").strip():
            warnings.append(f"line {line}: Resolved without resolution_date")

    try:
        payload = json.loads(args.site_json.read_text(encoding="utf-8"))
        if payload.get("meta", {}).get("records") != len(rows):
            errors.append("site JSON record count does not match canonical")
        if len(payload.get("disputes", [])) != len(rows):
            errors.append("site JSON disputes length does not match canonical")
    except Exception as exc:
        errors.append(f"site JSON unreadable: {exc}")

    try:
        if args.public_csv.read_bytes() != CANONICAL.read_bytes():
            errors.append("public CSV is not byte-identical to canonical")
    except OSError as exc:
        errors.append(f"public CSV unreadable: {exc}")

    for label, path in (("Flourish", args.flourish), ("map-ready", args.map_ready)):
        try:
            if len(csv_rows(path)) != len(rows):
                errors.append(f"{label} row count does not match canonical")
        except OSError as exc:
            errors.append(f"{label} export unreadable: {exc}")

    print(f"Canonical: {len(rows)} records, {len(set(ids))} unique IDs")
    print(f"Warnings: {len(warnings)}")
    for warning in warnings[:20]:
        print(f"  WARN {warning}")
    if len(warnings) > 20:
        print(f"  ... {len(warnings) - 20} more warnings")
    if errors:
        print(f"Errors: {len(errors)}")
        for error in errors:
            print(f"  ERROR {error}")
        return 1
    print("Release validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
