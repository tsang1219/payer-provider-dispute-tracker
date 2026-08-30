#!/usr/bin/env python3
"""
Enrich missing OON effective dates for disputes with OON status

Three-phase approach:
1. Extract from existing notes field using regex patterns
2. Use deadline_date as fallback when available
3. Fetch primary_source_url and extract from web content

Target: 92 OON disputes missing oon_effective_date
Expected yield: ~87-88 dates (95% coverage)
"""

import csv
import sys
import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.improved_web_search_enrichment import extract_dates_improved
import re


def extract_oon_date_enhanced(text: str) -> Optional[str]:
    """
    Enhanced OON date extraction with additional patterns for 'dropped' etc.

    Includes patterns not in the standard extraction function.
    """
    month_map = {
        'january': '01', 'jan': '01',
        'february': '02', 'feb': '02',
        'march': '03', 'mar': '03',
        'april': '04', 'apr': '04',
        'may': '05',
        'june': '06', 'jun': '06',
        'july': '07', 'jul': '07',
        'august': '08', 'aug': '08',
        'september': '09', 'sep': '09', 'sept': '09',
        'october': '10', 'oct': '10',
        'november': '11', 'nov': '11',
        'december': '12', 'dec': '12'
    }

    # Enhanced patterns including "dropped"
    oon_patterns = [
        # Standard patterns
        r'(?:went|goes|going)\s+out[-\s]of[-\s]network\s+(?:on|effective)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'out[-\s]of[-\s]network\s+(?:effective|on)\s+(\w+\s+\d{1,2},?\s+\d{4})',
        r'OON\s+(?:effective|on)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'terminated\s+(?:on|effective)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'contract\s+(?:expired|ended)\s+(?:on)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'ended\s+(\w+\s+\d{1,2},?\s+\d{4})',

        # Additional patterns for "dropped"
        r'dropped\s+(?:on|effective)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'(?:MA|Medicare\s+Advantage)\s+dropped\s+(\w+\s+\d{1,2},?\s+\d{4})',
        r'dropped\s+(?:MA|Medicare\s+Advantage)\s+(?:plans?\s+)?(\w+\s+\d{1,2},?\s+\d{4})',
    ]

    for pattern in oon_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)

            # Parse date
            # Try Month Day, Year format
            match_date = re.match(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', date_str, re.IGNORECASE)
            if match_date:
                month_name, day, year = match_date.groups()
                month_name = month_name.lower()
                if month_name in month_map:
                    return f"{year}-{month_map[month_name]}-{int(day):02d}"

            # Try Month Year format (no day)
            match_date = re.match(r'(\w+)\s+(\d{4})', date_str, re.IGNORECASE)
            if match_date:
                month_name, year = match_date.groups()
                month_name = month_name.lower()
                if month_name in month_map:
                    return f"{year}-{month_map[month_name]}-01"

    return None


def phase_1_extract_from_notes(disputes: List[Dict], verbose: bool = False) -> Dict:
    """
    Phase 1: Extract OON dates from existing notes field

    Returns:
        stats dict with counts of filled dates
    """
    filled = 0

    for dispute in disputes:
        # Skip if already has oon_effective_date
        if dispute.get('oon_effective_date', '').strip():
            continue

        # Extract dates from notes
        notes = dispute.get('notes', '') or ''
        enrichment_notes = dispute.get('enrichment_notes', '') or ''
        combined_text = f"{notes} {enrichment_notes}"

        if not combined_text.strip():
            continue

        # Try standard extraction first
        dates = extract_dates_improved(combined_text)
        oon_date = dates.get('oon_effective_date')

        # If not found, try enhanced extraction
        if not oon_date:
            oon_date = extract_oon_date_enhanced(combined_text)

        if oon_date:
            dispute['oon_effective_date'] = oon_date

            # Set source to primary_source_url if available
            if dispute.get('primary_source_url', '').strip():
                dispute['oon_effective_date_source'] = dispute['primary_source_url']
            else:
                dispute['oon_effective_date_source'] = 'extracted_from_notes'

            # Add enrichment note
            existing_notes = dispute.get('enrichment_notes', '').strip()
            new_note = f"OON date extracted from notes: {oon_date}"
            if existing_notes:
                dispute['enrichment_notes'] = f"{existing_notes}; {new_note}"
            else:
                dispute['enrichment_notes'] = new_note

            filled += 1

            if verbose:
                print(f"  Dispute {dispute['dispute_id']}: Extracted {oon_date} from notes")

    return {'filled': filled}


def phase_2_use_deadline_fallback(disputes: List[Dict], verbose: bool = False) -> Dict:
    """
    Phase 2: Use deadline_date as oon_effective_date when available

    Rationale: Contract expiration typically = network termination

    Returns:
        stats dict with counts of filled dates
    """
    filled = 0

    for dispute in disputes:
        # Skip if already has oon_effective_date
        if dispute.get('oon_effective_date', '').strip():
            continue

        # Check if deadline_date exists
        deadline_date = dispute.get('deadline_date', '').strip()
        if not deadline_date:
            continue

        # Copy deadline to OON date
        dispute['oon_effective_date'] = deadline_date
        dispute['oon_effective_date_source'] = 'calculated_from_deadline_date'

        # Add enrichment note
        existing_notes = dispute.get('enrichment_notes', '').strip()
        new_note = f"OON date inferred from deadline_date (contract expiration)"
        if existing_notes:
            dispute['enrichment_notes'] = f"{existing_notes}; {new_note}"
        else:
            dispute['enrichment_notes'] = new_note

        filled += 1

        if verbose:
            print(f"  Dispute {dispute['dispute_id']}: Using deadline_date {deadline_date} as fallback")

    return {'filled': filled}


def phase_3_fetch_from_urls(disputes: List[Dict], verbose: bool = False, max_fetch: int = 20) -> Dict:
    """
    Phase 3: Fetch primary_source_url and extract dates from content

    Args:
        disputes: List of dispute records
        verbose: Print detailed progress
        max_fetch: Maximum number of URLs to fetch (to avoid rate limiting)

    Returns:
        stats dict with counts of filled dates and fetch results
    """
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
    import time

    filled = 0
    fetch_attempted = 0
    fetch_success = 0
    fetch_failed = 0

    for dispute in disputes:
        # Skip if already has oon_effective_date
        if dispute.get('oon_effective_date', '').strip():
            continue

        # Check if we've hit max fetch limit
        if fetch_attempted >= max_fetch:
            if verbose:
                print(f"  Reached max fetch limit ({max_fetch})")
            break

        # Get primary source URL
        url = dispute.get('primary_source_url', '').strip()
        if not url:
            continue

        fetch_attempted += 1

        try:
            # Fetch URL with user agent
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})

            if verbose:
                print(f"  Dispute {dispute['dispute_id']}: Fetching {url[:60]}...")

            with urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8', errors='ignore')

            fetch_success += 1

            # Extract dates from fetched content
            dates = extract_dates_improved(content)

            if dates.get('oon_effective_date'):
                dispute['oon_effective_date'] = dates['oon_effective_date']
                dispute['oon_effective_date_source'] = url

                # Add enrichment note
                existing_notes = dispute.get('enrichment_notes', '').strip()
                new_note = f"OON date extracted from {url[:50]}..."
                if existing_notes:
                    dispute['enrichment_notes'] = f"{existing_notes}; {new_note}"
                else:
                    dispute['enrichment_notes'] = new_note

                filled += 1

                if verbose:
                    print(f"    ✓ Extracted {dates['oon_effective_date']}")
            else:
                if verbose:
                    print(f"    ✗ No OON date found in content")

            # Rate limiting
            time.sleep(0.5)

        except (URLError, HTTPError, TimeoutError) as e:
            fetch_failed += 1
            if verbose:
                print(f"    ✗ Fetch failed: {str(e)[:60]}")
        except Exception as e:
            fetch_failed += 1
            if verbose:
                print(f"    ✗ Error: {str(e)[:60]}")

    return {
        'filled': filled,
        'fetch_attempted': fetch_attempted,
        'fetch_success': fetch_success,
        'fetch_failed': fetch_failed
    }


def enrich_oon_dates(csv_path: str, output_path: str = None, phases: str = '1,2,3',
                     verbose: bool = False, dry_run: bool = False, max_fetch: int = 20):
    """
    Main enrichment function

    Args:
        csv_path: Path to disputes CSV
        output_path: Path to write updated CSV (default: same as input)
        phases: Comma-separated list of phases to run (e.g., '1,2,3' or '1,2')
        verbose: Print detailed progress
        dry_run: Don't write changes to CSV
        max_fetch: Maximum URLs to fetch in phase 3
    """
    csv_path = Path(csv_path)
    if output_path is None:
        output_path = csv_path
    else:
        output_path = Path(output_path)

    phases_to_run = [int(p) for p in phases.split(',')]

    # Read CSV
    print(f"Reading {csv_path}...")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Total disputes: {len(rows)}")

    # Filter for OON disputes missing oon_effective_date
    oon_statuses = ['OON-Ongoing', 'OON-Permanent']
    oon_disputes = [
        row for row in rows
        if row.get('outcome_status') in oon_statuses
    ]

    oon_missing = [
        row for row in oon_disputes
        if not row.get('oon_effective_date', '').strip()
    ]

    print(f"OON disputes: {len(oon_disputes)}")
    print(f"OON disputes with oon_effective_date: {len(oon_disputes) - len(oon_missing)}")
    print(f"OON disputes missing oon_effective_date: {len(oon_missing)}")
    print()

    # Track starting state
    initial_missing = len(oon_missing)

    # Run requested phases
    phase_results = {}

    if 1 in phases_to_run:
        print("=" * 70)
        print("PHASE 1: Extract from Notes")
        print("=" * 70)
        stats = phase_1_extract_from_notes(oon_missing, verbose=verbose)
        phase_results[1] = stats
        print(f"✓ Filled {stats['filled']} OON dates from notes")
        print()

    if 2 in phases_to_run:
        print("=" * 70)
        print("PHASE 2: Use Deadline Date as Fallback")
        print("=" * 70)
        stats = phase_2_use_deadline_fallback(oon_missing, verbose=verbose)
        phase_results[2] = stats
        print(f"✓ Filled {stats['filled']} OON dates from deadline_date")
        print()

    if 3 in phases_to_run:
        print("=" * 70)
        print("PHASE 3: Fetch from Primary Source URLs")
        print("=" * 70)
        print(f"Max fetches: {max_fetch}")
        stats = phase_3_fetch_from_urls(oon_missing, verbose=verbose, max_fetch=max_fetch)
        phase_results[3] = stats
        print(f"✓ Filled {stats['filled']} OON dates from web content")
        print(f"  Fetch attempts: {stats['fetch_attempted']}")
        print(f"  Fetch success: {stats['fetch_success']}")
        print(f"  Fetch failed: {stats['fetch_failed']}")
        print()

    # Calculate final stats
    still_missing = sum(1 for row in oon_missing if not row.get('oon_effective_date', '').strip())
    total_filled = initial_missing - still_missing

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Initial OON disputes missing dates: {initial_missing}")
    print(f"Total dates filled: {total_filled} ({total_filled/initial_missing*100:.1f}%)")
    print(f"Remaining missing: {still_missing} ({still_missing/initial_missing*100:.1f}%)")
    print()

    for phase_num in sorted(phase_results.keys()):
        stats = phase_results[phase_num]
        print(f"Phase {phase_num}: {stats['filled']} dates filled")

    print()

    # Write updated CSV
    if not dry_run:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"✓ Wrote updated data to {output_path}")
    else:
        print("DRY RUN: No changes written to CSV")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Enrich missing OON effective dates')
    parser.add_argument('--csv', default='data/primary/disputes_enriched.csv',
                        help='Path to disputes CSV')
    parser.add_argument('--output', default=None,
                        help='Output path (default: overwrite input)')
    parser.add_argument('--phases', default='1,2,3',
                        help='Phases to run (default: 1,2,3)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print detailed progress')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show changes without writing to CSV')
    parser.add_argument('--max-fetch', type=int, default=20,
                        help='Max URLs to fetch in phase 3 (default: 20)')

    args = parser.parse_args()

    enrich_oon_dates(
        csv_path=args.csv,
        output_path=args.output,
        phases=args.phases,
        verbose=args.verbose,
        dry_run=args.dry_run,
        max_fetch=args.max_fetch
    )
