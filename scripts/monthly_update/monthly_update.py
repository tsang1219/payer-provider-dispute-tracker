#!/usr/bin/env python3
"""
monthly_update.py — the self-maintenance job for the dispute tracker.

Keeps data/primary/disputes_enriched.csv (CANONICAL) current with a strict
human review gate. The job NEVER writes discovered material to canonical
directly — discovery and status checks stage candidates into review/ CSVs;
only `apply` (run after Andrew edits the review files) touches canonical,
and it always writes a timestamped backup first.

Subcommands
-----------
  discover   Search Google News RSS for payer-provider standoffs not yet in
             the dataset. Stages candidates -> review/candidates_YYYY-MM.csv
  status     Re-check every OON-Ongoing dispute for resolution/escalation
             news. Stages findings -> review/status_check_YYYY-MM.csv
  apply      Merge APPROVED rows from the review CSVs into canonical
             (backup first), then rebuild all derived outputs.
  rebuild    Regenerate site JSON + DataWrapper/Flourish/map exports from
             canonical. Run after any manual edit to the canonical CSV.
  run        discover + status + rebuild  (the monthly cron entry — safe:
             does not modify canonical).

Data integrity rules
--------------------
* Every staged candidate carries the URL of the news item that produced it.
  Fields the job cannot read from the source are left BLANK, never guessed.
* `apply` validates required fields, status enum, dates, and state codes,
  and refuses rows that fail.
* Canonical is backed up to data/primary/ with a timestamp before any write.

Only Python 3.9+ stdlib is required (network: news.google.com RSS).
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "data/primary/disputes_enriched.csv"
REVIEW_DIR = ROOT / "review"
SEEN_LEDGER = REVIEW_DIR / "seen_items.json"
VIZ_DIR = ROOT / "data/derived/visualizations"

USER_AGENT = "Mozilla/5.0 (HIOP dispute-tracker monthly job; healthisotherpeople.com)"
RSS_DELAY_SECONDS = 1.2  # be polite to Google News

VALID_STATUSES = {"Resolved", "OON-Ongoing", "OON-Permanent"}
VALID_STATES = set(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT "
    "NE NV NH NJ NM NY NC ND OH OK OR PA PR RI SC SD TN TX UT VT VA WA WV WI WY".split()
)

# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


def read_canonical():
    with open(CANONICAL, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def canonical_fieldnames():
    with open(CANONICAL, newline="", encoding="utf-8") as fh:
        return csv.DictReader(fh).fieldnames


def backup_canonical():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = CANONICAL.with_suffix(f".csv.backup_{stamp}")
    shutil.copyfile(CANONICAL, dst)
    print(f"Backed up canonical -> {dst.name}")
    return dst


def fetch_rss(query: str, when_days: int = 45):
    """Fetch Google News RSS items for a query. Returns list of dicts."""
    q = urllib.parse.quote(f"{query} when:{when_days}d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except Exception as e:  # network failure: report, don't crash the run
        print(f"  ! fetch failed for {query!r}: {e}")
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"  ! parse failed for {query!r}: {e}")
        return []
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        source = (item.findtext("source") or "").strip()
        pub_iso = ""
        if pub:
            try:
                pub_iso = datetime.strptime(pub[:16], "%a, %d %b %Y").date().isoformat()
            except ValueError:
                pub_iso = pub
        items.append({"title": title, "url": link, "published": pub_iso, "source": source})
    return items


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()


def load_seen():
    if SEEN_LEDGER.exists():
        return set(json.loads(SEEN_LEDGER.read_text()))
    return set()


def save_seen(seen):
    REVIEW_DIR.mkdir(exist_ok=True)
    SEEN_LEDGER.write_text(json.dumps(sorted(seen), indent=0))


def item_key(title: str) -> str:
    """Dedupe key: normalized title (Google News URLs are session-flavored)."""
    return norm(title)[:160]


# ---------------------------------------------------------------------------
# discover
# ---------------------------------------------------------------------------

DISCOVERY_QUERIES = [
    'hospital insurer "out of network" contract dispute',
    'hospital "contract dispute" insurance "out of network"',
    'health system insurer contract negotiation deadline "out of network"',
    'hospital drops Medicare Advantage plan',
    'hospital terminates contract UnitedHealthcare',
    'hospital contract dispute Anthem OR Elevance',
    'hospital contract dispute Aetna OR Cigna OR Humana',
    'hospital "Blue Cross" contract dispute "out of network"',
    'health system "goes out of network"',
    'hospital insurance contract expires patients "out of network"',
]

# words that must appear for an item to be considered dispute-shaped
RELEVANCE_ANY = [
    "out of network", "out-of-network", "contract", "dispute", "negotiat",
    "terminat", "drops", "dropping", "split with", "leaves network", "network agreement",
]
PROVIDER_WORDS = ["hospital", "health system", "medical center", "health network",
                  "healthcare system", "clinic", "physicians", "health"]

INSURER_HINTS = [
    ("UnitedHealthcare", "UnitedHealth Group"), ("United Healthcare", "UnitedHealth Group"),
    ("Anthem", "Elevance Health"), ("Elevance", "Elevance Health"),
    ("Aetna", "CVS Health"), ("Cigna", "Cigna"), ("Humana", "Humana"),
    ("Blue Cross", "Blue Cross Blue Shield"), ("BCBS", "Blue Cross Blue Shield"),
    ("Centene", "Centene"), ("Molina", "Molina Healthcare"), ("Kaiser", "Kaiser Permanente"),
    ("Medicare Advantage", ""),
]

CANDIDATE_COLUMNS = [
    # discovery provenance (filled by the job)
    "found_date", "headline", "news_source", "url", "published",
    "guessed_insurer_family", "matches_existing_id",
    # the review gate (filled by Andrew)
    "approve",  # YES to add on apply; anything else = skipped
    # canonical fields required by apply (fill before approving)
    "system_name", "system_hq_city", "system_hq_state",
    "system_hq_lat", "system_hq_lon",  # needed for the map — HQ coordinates
    "state",
    "insurer_name", "insurer_type", "dispute_type",
    "first_media_date", "outcome_status",
    # optional but valuable
    "deadline_date", "oon_effective_date", "resolution_date",
    "patients_affected", "lawsuit_filed", "notes",
    "primary_source", "primary_source_url",
]


def guess_insurer(title: str):
    for hint, family in INSURER_HINTS:
        if hint.lower() in title.lower():
            return family or hint
    return ""


def match_existing(title: str, rows):
    """If the headline names a system+insurer pair already tracked, return that id."""
    t = norm(title)
    for r in rows:
        sysn = norm(r.get("system_name_normalized") or r.get("system_name", ""))
        insn = norm(r.get("insurer_name_normalized") or r.get("insurer_name", ""))
        if sysn and insn and sysn in t and insn.split(" ")[0] in t:
            return r["dispute_id"]
    return ""


def cmd_discover(args):
    rows = read_canonical()
    seen = load_seen()
    stamp = date.today()
    out_path = REVIEW_DIR / f"candidates_{stamp.strftime('%Y-%m')}.csv"
    REVIEW_DIR.mkdir(exist_ok=True)

    print(f"Discovery: {len(DISCOVERY_QUERIES)} queries, {args.days}-day window")
    found = {}
    for q in DISCOVERY_QUERIES:
        print(f"  · {q}")
        for it in fetch_rss(q, when_days=args.days):
            title = it["title"]
            tl = title.lower()
            if not any(w in tl for w in RELEVANCE_ANY):
                continue
            if not any(w in tl for w in PROVIDER_WORDS):
                continue
            key = item_key(title)
            if key in seen or key in found:
                continue
            found[key] = it
        time.sleep(RSS_DELAY_SECONDS)

    candidates = []
    for key, it in found.items():
        candidates.append({
            "found_date": stamp.isoformat(),
            "headline": it["title"],
            "news_source": it["source"],
            "url": it["url"],
            "published": it["published"],
            "guessed_insurer_family": guess_insurer(it["title"]),
            "matches_existing_id": match_existing(it["title"], rows),
            "approve": "",
            # canonical fields left blank on purpose — never guessed
            "system_name": "", "system_hq_city": "", "system_hq_state": "", "state": "",
            "insurer_name": "", "insurer_type": "", "dispute_type": "",
            "first_media_date": "", "outcome_status": "",
            "deadline_date": "", "oon_effective_date": "", "resolution_date": "",
            "patients_affected": "", "lawsuit_filed": "", "notes": "",
            "primary_source": it["source"], "primary_source_url": it["url"],
        })

    # append to this month's file if it already exists (idempotent within a month)
    existing_keys = set()
    prior = []
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            prior = list(csv.DictReader(fh))
        existing_keys = {item_key(p["headline"]) for p in prior}
    new_rows = [c for c in candidates if item_key(c["headline"]) not in existing_keys]

    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CANDIDATE_COLUMNS)
        w.writeheader()
        for p in prior:
            w.writerow({k: p.get(k, "") for k in CANDIDATE_COLUMNS})
        w.writerows(new_rows)

    # only mark as seen what was staged, so re-runs stay quiet
    for c in new_rows:
        seen.add(item_key(c["headline"]))
    save_seen(seen)

    n_linked = sum(1 for c in new_rows if c["matches_existing_id"])
    print(f"\nStaged {len(new_rows)} new candidates ({n_linked} look like already-tracked disputes)")
    print(f"Review gate: {out_path.relative_to(ROOT)}")
    print("Fill the canonical columns for real disputes, set approve=YES, then run: apply")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

RESOLUTION_SIGNALS = ["agreement", "reach", "new contract", "back in network",
                      "back in-network", "resolved", "multi-year", "multiyear",
                      "renew", "restore", "in network again", "deal"]
ESCALATION_SIGNALS = ["lawsuit", "sue", "terminate", "permanent", "arbitration",
                      "out of network", "out-of-network", "expire"]

STATUS_COLUMNS = [
    "dispute_id", "dispute_name", "current_status", "first_reported",
    "signal", "headlines", "urls",
    "approve",       # YES to apply the change below
    "new_status",    # Resolved / OON-Ongoing / OON-Permanent
    "resolution_date", "resolution_date_source", "note",
]


def cmd_status(args):
    rows = read_canonical()
    open_rows = [r for r in rows if r.get("outcome_status") == "OON-Ongoing"]
    if args.limit:
        open_rows = open_rows[: args.limit]
    stamp = date.today()
    out_path = REVIEW_DIR / f"status_check_{stamp.strftime('%Y-%m')}.csv"
    REVIEW_DIR.mkdir(exist_ok=True)

    print(f"Status check: {len(open_rows)} ongoing disputes, {args.days}-day window")
    findings = []
    checked = 0
    for r in open_rows:
        sysn = r.get("system_name_normalized") or r.get("system_name", "")
        insn = r.get("insurer_name_normalized") or r.get("insurer_name", "")
        query = f'"{sysn}" "{insn.split("(")[0].strip()}"'
        items = fetch_rss(query, when_days=args.days)
        checked += 1
        if checked % 10 == 0:
            print(f"  … {checked}/{len(open_rows)} checked")
        time.sleep(RSS_DELAY_SECONDS)
        relevant = [it for it in items if norm(sysn) in norm(it["title"])][:3]
        if not relevant:
            continue
        text = " ".join(it["title"].lower() for it in relevant)
        if any(s in text for s in RESOLUTION_SIGNALS):
            signal = "possible-resolution"
        elif any(s in text for s in ESCALATION_SIGNALS):
            signal = "escalation-news"
        else:
            signal = "news"
        findings.append({
            "dispute_id": r["dispute_id"],
            "dispute_name": r["dispute_name"],
            "current_status": r["outcome_status"],
            "first_reported": r.get("first_media_date", ""),
            "signal": signal,
            "headlines": " | ".join(it["title"] for it in relevant),
            "urls": " | ".join(it["url"] for it in relevant),
            "approve": "", "new_status": "", "resolution_date": "",
            "resolution_date_source": "", "note": "",
        })

    findings.sort(key=lambda f: (f["signal"] != "possible-resolution", f["dispute_name"]))
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=STATUS_COLUMNS)
        w.writeheader()
        w.writerows(findings)

    n_res = sum(1 for f in findings if f["signal"] == "possible-resolution")
    print(f"\nChecked {checked} ongoing disputes; {len(findings)} have recent news "
          f"({n_res} look like possible resolutions)")
    print(f"Review gate: {out_path.relative_to(ROOT)}")
    print("Verify against the linked coverage, set approve=YES + new_status, then run: apply")


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


def is_yes(v: str) -> bool:
    return (v or "").strip().lower() in ("yes", "y", "true", "approve", "approved", "1")


def valid_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def normalize_system(name: str) -> str:
    n = name
    for suffix in [" Health System", " Healthcare System", " Health Care", " Healthcare",
                   " Health", " Medical Center", " Hospital System", " System"]:
        if n.endswith(suffix) and len(n) > len(suffix) + 3:
            n = n[: -len(suffix)]
            break
    return n.strip()


def normalize_insurer(name: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", name).strip()


def completeness(row: dict) -> float:
    pts = 0.0
    if row.get("system_hq_lat") and row.get("system_hq_lon"):
        pts += 2
    try:
        if float(row.get("patients_affected") or 0) > 0:
            pts += 2
    except ValueError:
        pass
    if row.get("oon_effective_date"):
        pts += 1
    if row.get("resolution_date") or row.get("outcome_status") == "OON-Ongoing":
        pts += 1
    if row.get("primary_source_url"):
        pts += 1
    if row.get("insurer_parent"):
        pts += 1
    if row.get("system_type"):
        pts += 1
    if row.get("notes") or row.get("enrichment_notes"):
        pts += 1
    return round(pts / 10.0, 2)


def apply_candidates(path: Path, rows, fieldnames):
    with open(path, newline="", encoding="utf-8") as fh:
        cands = list(csv.DictReader(fh))
    approved = [c for c in cands if is_yes(c.get("approve", "")) and not c.get("matches_existing_id")]
    added, errors = [], []
    max_id = max(int(r["dispute_id"]) for r in rows)

    for c in approved:
        problems = []
        required = ["system_name", "insurer_name", "state", "first_media_date",
                    "outcome_status", "primary_source_url"]
        for k in required:
            if not (c.get(k) or "").strip():
                problems.append(f"missing {k}")
        if c.get("outcome_status") and c["outcome_status"] not in VALID_STATUSES:
            problems.append(f"bad outcome_status {c['outcome_status']!r}")
        if c.get("state") and c["state"].upper() not in VALID_STATES:
            problems.append(f"bad state {c['state']!r}")
        for dk in ["first_media_date", "deadline_date", "oon_effective_date", "resolution_date"]:
            if (c.get(dk) or "").strip() and not valid_date(c[dk].strip()):
                problems.append(f"bad date {dk}={c[dk]!r} (want YYYY-MM-DD)")
        for nk in ["system_hq_lat", "system_hq_lon", "patients_affected"]:
            v = (c.get(nk) or "").strip()
            if v:
                try:
                    float(v.replace(",", ""))
                except ValueError:
                    problems.append(f"non-numeric {nk}={v!r}")
        # duplicate guard against canonical
        for r in rows:
            if (norm(r["system_name"]) == norm(c.get("system_name", ""))
                    and norm(r["insurer_name_normalized"]) == norm(normalize_insurer(c.get("insurer_name", "")))
                    and str(r.get("year_first_reported")) == (c.get("first_media_date", "") or "")[:4]):
                problems.append(f"duplicate of dispute_id {r['dispute_id']}")
                break
        if problems:
            errors.append((c.get("headline") or c.get("system_name", "?"), problems))
            continue

        max_id += 1
        fmd = c["first_media_date"].strip()
        year = fmd[:4]
        quarter = f"Q{(int(fmd[5:7]) - 1) // 3 + 1}"
        insurer_norm = normalize_insurer(c["insurer_name"])
        new = {k: "" for k in fieldnames}
        new.update({
            "dispute_id": str(max_id),
            "dispute_name": f"{c['system_name'].strip()} vs {insurer_norm} {year}",
            "system_name": c["system_name"].strip(),
            "system_name_normalized": normalize_system(c["system_name"].strip()),
            "system_hq_city": (c.get("system_hq_city") or "").strip(),
            "system_hq_state": (c.get("system_hq_state") or c["state"]).strip().upper(),
            "system_hq_lat": (c.get("system_hq_lat") or "").strip(),
            "system_hq_lon": (c.get("system_hq_lon") or "").strip(),
            "insurer_name": c["insurer_name"].strip(),
            "insurer_name_normalized": insurer_norm,
            "insurer_type": (c.get("insurer_type") or "").strip(),
            "year_first_reported": year,
            "quarter_first_reported": quarter,
            "first_media_date": fmd,
            "deadline_date": (c.get("deadline_date") or "").strip(),
            "oon_effective_date": (c.get("oon_effective_date") or "").strip(),
            "resolution_date": (c.get("resolution_date") or "").strip(),
            "outcome_status": c["outcome_status"].strip(),
            "patients_affected": (c.get("patients_affected") or "").strip(),
            "patients_affected_source": "extracted_from_notes_patients" if (c.get("patients_affected") or "").strip() else "",
            "dispute_type": (c.get("dispute_type") or "").strip(),
            "lawsuit_filed": (c.get("lawsuit_filed") or "False").strip() or "False",
            "primary_source": (c.get("primary_source") or c.get("news_source") or "").strip(),
            "primary_source_url": c["primary_source_url"].strip(),
            "first_media_date_source": c["primary_source_url"].strip(),
            "state": c["state"].strip().upper(),
            "notes": (c.get("notes") or "").strip(),
            "enrichment_notes": f"Added via monthly update {date.today().isoformat()} "
                                f"(human-approved candidate; source: {c['primary_source_url'].strip()})",
            "last_updated": datetime.now().isoformat(),
            "manually_verified": "True",
        })
        if new["resolution_date"] and new["first_media_date"]:
            d = (datetime.strptime(new["resolution_date"], "%Y-%m-%d")
                 - datetime.strptime(new["first_media_date"], "%Y-%m-%d")).days
            new["duration_days"] = str(d)
            new["duration_months"] = str(round(d / 30.44, 1))
        new["data_completeness_score"] = str(completeness(new))
        rows.append(new)
        tag = "" if new["system_hq_lat"] else "  (no HQ lat/lon — will not appear on the map)"
        added.append(new["dispute_name"] + tag)

    return added, errors


def apply_status(path: Path, rows):
    with open(path, newline="", encoding="utf-8") as fh:
        checks = list(csv.DictReader(fh))
    updated, errors = [], []
    by_id = {r["dispute_id"]: r for r in rows}

    for c in checks:
        if not is_yes(c.get("approve", "")):
            continue
        r = by_id.get((c.get("dispute_id") or "").strip())
        problems = []
        if r is None:
            problems.append(f"unknown dispute_id {c.get('dispute_id')!r}")
        ns = (c.get("new_status") or "").strip()
        if not ns:
            problems.append("missing new_status")
        elif ns not in VALID_STATUSES:
            problems.append(f"bad new_status {ns!r}")
        rd = (c.get("resolution_date") or "").strip()
        if ns == "Resolved" and not rd:
            problems.append("Resolved requires resolution_date")
        if rd and not valid_date(rd):
            problems.append(f"bad resolution_date {rd!r} (want YYYY-MM-DD)")
        if problems:
            errors.append((c.get("dispute_name", c.get("dispute_id", "?")), problems))
            continue

        r["outcome_status"] = ns
        if rd:
            r["resolution_date"] = rd
            src = (c.get("resolution_date_source") or "").strip()
            if src:
                r["resolution_date_source"] = src
            if r.get("first_media_date"):
                d = (datetime.strptime(rd, "%Y-%m-%d")
                     - datetime.strptime(r["first_media_date"], "%Y-%m-%d")).days
                r["duration_days"] = str(d)
                r["duration_months"] = str(round(d / 30.44, 1))
        note = (c.get("note") or "").strip()
        stampnote = f"Status -> {ns} via monthly update {date.today().isoformat()}"
        if note:
            stampnote += f": {note}"
        r["enrichment_notes"] = ((r.get("enrichment_notes") or "").rstrip("; ") + "; " + stampnote).strip("; ")
        r["last_updated"] = datetime.now().isoformat()
        r["data_completeness_score"] = str(completeness(r))
        updated.append(f"{r['dispute_name']} -> {ns}")

    return updated, errors


def cmd_apply(args):
    rows = read_canonical()
    fieldnames = canonical_fieldnames()
    month = args.month or date.today().strftime("%Y-%m")
    cand_path = Path(args.candidates) if args.candidates else REVIEW_DIR / f"candidates_{month}.csv"
    stat_path = Path(args.status_file) if args.status_file else REVIEW_DIR / f"status_check_{month}.csv"

    added, updated, errors = [], [], []
    if cand_path.exists():
        a, e = apply_candidates(cand_path, rows, fieldnames)
        added += a
        errors += e
    else:
        print(f"(no candidates file at {cand_path})")
    if stat_path.exists():
        u, e = apply_status(stat_path, rows)
        updated += u
        errors += e
    else:
        print(f"(no status file at {stat_path})")

    if errors:
        print(f"\n{len(errors)} row(s) REFUSED (fix and re-run apply):")
        for name, problems in errors:
            print(f"  ✗ {name}: {'; '.join(problems)}")

    if not added and not updated:
        print("\nNothing approved — canonical untouched.")
        return

    backup_canonical()
    with open(CANONICAL, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"\nCanonical updated: +{len(added)} new, {len(updated)} status changes")
    for n in added:
        print(f"  + {n}")
    for n in updated:
        print(f"  ~ {n}")

    cmd_rebuild(args)


# ---------------------------------------------------------------------------
# rebuild (derived outputs)
# ---------------------------------------------------------------------------


def rebuild_flourish(rows, out=None):
    """Quarter-column time-slider CSV for Flourish, from canonical (stdlib)."""
    out = out or VIZ_DIR / "disputes_flourish_timeslider.csv"
    today = date.today()
    quarters = []
    for y in range(2021, today.year + 1):
        for q in range(1, 5):
            if y == today.year and q > (today.month - 1) // 3 + 1:
                break
            quarters.append(f"{y} Q{q}")

    base_cols = ["dispute_id", "dispute_name", "system_name", "insurer_name_normalized",
                 "system_hq_lat", "system_hq_lon", "system_hq_state", "state",
                 "year_first_reported", "quarter_first_reported", "outcome_status",
                 "patients_affected", "dispute_type"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(base_cols + quarters)
        for r in rows:
            try:
                start = quarters.index(f"{r['year_first_reported']} {r['quarter_first_reported']}")
            except ValueError:
                start = None
            qvals = []
            for i in range(len(quarters)):
                qvals.append(r["outcome_status"] if start is not None and i >= start else "")
            w.writerow([r.get(c, "") for c in base_cols] + qvals)
    print(f"  ✓ {out} ({len(rows)} rows, {len(quarters)} quarters)")


def rebuild_map_ready(rows, out=None):
    out = out or VIZ_DIR / "disputes_map_ready.csv"
    cols = ["dispute_id", "dispute_name", "system_name", "insurer_name_normalized",
            "system_hq_lat", "system_hq_lon", "system_hq_state", "system_hq_city",
            "year_first_reported", "quarter_first_reported", "outcome_status",
            "patients_affected", "dispute_type", "notes", "manually_verified"]
    n = 0
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            if not (r.get("system_hq_lat") and r.get("system_hq_lon")):
                continue
            w.writerow([r.get(c, "") for c in cols])
            n += 1
    print(f"  ✓ {out} ({n} geocoded rows)")


def rebuild_json_export(rows, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  ✓ {out} ({len(rows)} rows)")


def cmd_rebuild(_args):
    print("\nRebuilding derived outputs from canonical…")
    rows = read_canonical()

    targets = {
        "site_json": ROOT / "site/src/data/disputes.json",
        "public_csv": ROOT / "site/public/disputes.csv",
        "datawrapper": VIZ_DIR / "datawrapper_range_plot_simple.csv",
        "flourish": VIZ_DIR / "disputes_flourish_timeslider.csv",
        "map_ready": VIZ_DIR / "disputes_map_ready.csv",
        "json_export": ROOT / "data/derived/exports/disputes_enriched.json",
    }
    with tempfile.TemporaryDirectory(prefix="dispute-rebuild-") as temp_name:
        temp = Path(temp_name)
        staged = {name: temp / path.name for name, path in targets.items()}

        subprocess.run([
            sys.executable, str(ROOT / "scripts/site_data/build_site_data.py"),
            "--output", str(staged["site_json"]),
            "--public-csv", str(staged["public_csv"]),
        ], check=True)

        env = dict(os.environ, PYTHONPATH=str(ROOT))
        subprocess.run([
            sys.executable, str(ROOT / "scripts/visualization/regenerate_datawrapper_simple.py"),
            "--csv", str(CANONICAL),
            "--output", str(staged["datawrapper"]),
        ], check=True, cwd=ROOT, stdout=subprocess.DEVNULL, env=env)
        print("  ✓ staged DataWrapper range export")

        rebuild_flourish(rows, staged["flourish"])
        rebuild_map_ready(rows, staged["map_ready"])
        rebuild_json_export(rows, staged["json_export"])

        subprocess.run([
            sys.executable, str(ROOT / "scripts/maintenance/validate_release.py"),
            "--site-json", str(staged["site_json"]),
            "--public-csv", str(staged["public_csv"]),
            "--flourish", str(staged["flourish"]),
            "--map-ready", str(staged["map_ready"]),
        ], check=True)

        for name, target in targets.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged[name], target)
            print(f"  ✓ published {target.relative_to(ROOT)}")

    print("Rebuild complete. To ship the site: cd site && npm run build  (then deploy dist/)")


# ---------------------------------------------------------------------------
# run (the cron entry)
# ---------------------------------------------------------------------------


def cmd_run(args):
    cmd_discover(args)
    print("\n" + "=" * 70 + "\n")
    cmd_status(args)
    print("\n" + "=" * 70 + "\n")
    cmd_rebuild(args)
    print("\nMonthly sweep done. Canonical NOT modified — review the two files in "
          "review/ and run `apply` to merge approved rows.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("discover", help="stage new dispute candidates from news")
    d.add_argument("--days", type=int, default=45, help="lookback window (default 45)")
    d.set_defaults(fn=cmd_discover)

    s = sub.add_parser("status", help="re-check ongoing disputes for news")
    s.add_argument("--days", type=int, default=60, help="lookback window (default 60)")
    s.add_argument("--limit", type=int, default=0, help="only check first N (for testing)")
    s.set_defaults(fn=cmd_status)

    a = sub.add_parser("apply", help="merge APPROVED review rows into canonical")
    a.add_argument("--month", help="review-file month YYYY-MM (default: current)")
    a.add_argument("--candidates", help="explicit candidates CSV path")
    a.add_argument("--status-file", help="explicit status-check CSV path")
    a.set_defaults(fn=cmd_apply)

    r = sub.add_parser("rebuild", help="regenerate site data + viz exports")
    r.set_defaults(fn=cmd_rebuild)

    run = sub.add_parser("run", help="discover + status + rebuild (monthly cron entry)")
    run.add_argument("--days", type=int, default=45)
    run.add_argument("--limit", type=int, default=0)
    run.set_defaults(fn=cmd_run)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
