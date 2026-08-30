#!/usr/bin/env python3
"""
build_site_data.py — generate the web app's bundled JSON from the canonical CSV.

Reads:  data/primary/disputes_enriched.csv  (CANONICAL — source of truth)
Writes: site/src/data/disputes.json         (bundled into the static build)

Every figure in the app derives from this file; the script never invents values.
Empty fields stay null. Run after any canonical CSV change:

    python3 scripts/site_data/build_site_data.py
"""

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "data/primary/disputes_enriched.csv"
OUT = ROOT / "site/src/data/disputes.json"
PUBLIC_CSV = ROOT / "site/public/disputes.csv"  # download link on the site

VALID_STATUSES = {"Resolved", "OON-Ongoing", "OON-Permanent", "OON-Temporary",
                  "OON-Negotiating", "OON-Partial", "Unknown"}


def f(row, key):
    v = (row.get(key) or "").strip()
    return v or None


def num(row, key):
    v = f(row, key)
    if v is None:
        return None
    try:
        n = float(v)
        return int(n) if n == int(n) else n
    except ValueError:
        return None


def boolean(row, key):
    v = f(row, key)
    if v is None:
        return None
    return v.lower() in ("true", "1", "yes")


def iso_date(row, key):
    v = f(row, key)
    if v is None:
        return None
    try:
        return datetime.strptime(v[:10], "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--public-csv", type=Path, default=PUBLIC_CSV)
    args = parser.parse_args(argv)
    with open(CANONICAL, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    disputes = []
    problems = []
    for row in rows:
        d = {
            "id": num(row, "dispute_id"),
            "name": f(row, "dispute_name"),
            "system": f(row, "system_name"),
            "systemShort": f(row, "system_name_normalized"),
            "systemType": f(row, "system_type"),
            "hqCity": f(row, "system_hq_city"),
            "hqState": f(row, "system_hq_state"),
            "lat": num(row, "system_hq_lat"),
            "lon": num(row, "system_hq_lon"),
            "beds": num(row, "total_beds"),
            "insurer": f(row, "insurer_name"),
            "insurerShort": f(row, "insurer_name_normalized"),
            "insurerParent": f(row, "insurer_parent"),
            "insurerType": f(row, "insurer_type"),
            "disputeType": f(row, "dispute_type"),
            "state": f(row, "state") or f(row, "system_hq_state"),
            "year": num(row, "year_first_reported"),
            "quarter": f(row, "quarter_first_reported"),
            "firstDate": iso_date(row, "first_media_date"),
            "deadlineDate": iso_date(row, "deadline_date"),
            "oonDate": iso_date(row, "oon_effective_date"),
            "resolutionDate": iso_date(row, "resolution_date"),
            "durationDays": num(row, "duration_days"),
            "status": f(row, "outcome_status"),
            "patients": num(row, "patients_affected"),
            "patientsSource": f(row, "patients_affected_source"),
            "lawsuit": boolean(row, "lawsuit_filed"),
            "sourceName": f(row, "primary_source"),
            "sourceUrl": f(row, "primary_source_url"),
            "resolutionSourceUrl": f(row, "resolution_date_source"),
            "notes": f(row, "notes"),
            "verified": boolean(row, "manually_verified"),
            "completeness": num(row, "data_completeness_score"),
        }
        if d["id"] is None or d["system"] is None or d["insurer"] is None:
            problems.append(f"row missing id/system/insurer: {row.get('dispute_id')}")
            continue
        if d["status"] not in VALID_STATUSES:
            problems.append(f"dispute {d['id']}: unexpected status {d['status']!r}")
        if d["firstDate"] is None:
            problems.append(f"dispute {d['id']}: no first_media_date")
        disputes.append(d)

    last_updated = max((f(r, "last_updated") or "" for r in rows), default="")
    release_date = last_updated[:10] or None
    payload = {
        "meta": {
            "generated": release_date,
            "asOf": release_date,
            "records": len(disputes),
            "sourceFile": "data/primary/disputes_enriched.csv",
            "lastRecordUpdate": release_date,
        },
        "disputes": disputes,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))

    args.public_csv.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CANONICAL, args.public_csv)

    print(f"Wrote {len(disputes)} disputes -> {args.output}")
    print(f"Copied canonical CSV -> {args.public_csv}")
    if problems:
        print(f"\n{len(problems)} data warnings (not fatal):")
        for p in problems[:20]:
            print("  -", p)
        if len(problems) > 20:
            print(f"  ... and {len(problems) - 20} more")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
