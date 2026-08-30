#!/usr/bin/env python3
"""
Validate date data quality in disputes_enriched.csv

Checks:
- Source attribution for all dates
- Chronological ordering
- Quarter alignment
- Format consistency
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.date_validation import validate_all_dates


def validate_csv_dates(csv_path: str, show_details: bool = False):
    """Run validation on all disputes in CSV"""
    csv_path = Path(csv_path)

    # Read CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Date Validation Report")
    print(f"CSV: {csv_path}")
    print(f"Total disputes: {len(rows)}\n")

    # Run validation on each row
    results = []
    for row in rows:
        result = validate_all_dates(row)
        results.append(result)

    # Aggregate statistics
    total_valid = sum(1 for r in results if r['valid'])
    total_errors = sum(r['error_count'] for r in results)
    total_warnings = sum(r['warning_count'] for r in results)

    # Categorize issues
    source_issues = defaultdict(int)
    sequence_issues = defaultdict(int)
    quarter_issues = 0

    for r in results:
        # Count source issues
        for issue in r['first_media_validation'].get('issues', []):
            if 'no source URL' in issue:
                source_issues['first_media_date missing source'] += 1
            elif 'not in quarter' in issue:
                quarter_issues += 1

        for warning in r['first_media_validation'].get('warnings', []):
            if 'using primary_source_url' in warning:
                source_issues['first_media_date using fallback'] += 1

        for issue in r['resolution_validation'].get('issues', []):
            if 'no source URL' in issue:
                source_issues['resolution_date missing source'] += 1
            elif 'no resolution_date' in issue:
                source_issues['resolved but no date'] += 1

        for warning in r['resolution_validation'].get('warnings', []):
            if 'using primary_source_url' in warning:
                source_issues['resolution_date using fallback'] += 1

        # Count sequence violations
        for violation in r['sequence_validation'].get('violations', []):
            if 'after' in violation:
                sequence_issues['chronological violation'] += 1

    # Print summary
    print("=" * 60)
    print(f"SUMMARY")
    print("=" * 60)
    print(f"Valid disputes:     {total_valid} / {len(rows)} ({total_valid/len(rows)*100:.1f}%)")
    print(f"Total errors:       {total_errors}")
    print(f"Total warnings:     {total_warnings}")
    print()

    # Source attribution
    print("SOURCE ATTRIBUTION:")
    if source_issues:
        for issue_type, count in sorted(source_issues.items()):
            status = "⚠️" if "fallback" in issue_type else "❌"
            print(f"  {status} {issue_type}: {count}")
    else:
        print("  ✓ All dates have proper source attribution")
    print()

    # Chronological ordering
    print("CHRONOLOGICAL ORDERING:")
    if sequence_issues:
        for issue_type, count in sorted(sequence_issues.items()):
            print(f"  ❌ {issue_type}: {count}")
    else:
        print("  ✓ All dates in correct chronological order")
    print()

    # Quarter alignment
    print("QUARTER ALIGNMENT:")
    if quarter_issues > 0:
        print(f"  ❌ Quarter mismatches: {quarter_issues}")
    else:
        print("  ✓ All first_media_dates align with quarters")
    print()

    # OON Effective Date Coverage
    print("OON EFFECTIVE DATE COVERAGE:")
    oon_disputes = [r for r in rows if r.get('outcome_status') in ['OON-Ongoing', 'OON-Permanent']]
    oon_with_date = [r for r in oon_disputes if r.get('oon_effective_date', '').strip()]
    oon_missing_warnings = sum(1 for r in results if 'OON status' in str(r.get('oon_validation', {}).get('warnings', [])))

    if oon_disputes:
        print(f"  Total OON disputes: {len(oon_disputes)}")
        print(f"  Have oon_effective_date: {len(oon_with_date)} ({len(oon_with_date)/len(oon_disputes)*100:.1f}%)")
        print(f"  Missing oon_effective_date: {len(oon_disputes) - len(oon_with_date)} ({(len(oon_disputes)-len(oon_with_date))/len(oon_disputes)*100:.1f}%)")
        if oon_missing_warnings > 0:
            print(f"  ⚠️  Warnings for missing OON dates: {oon_missing_warnings}")
    else:
        print("  No OON disputes found")
    print()

    # Show detailed issues if requested
    if show_details:
        print("\n" + "=" * 60)
        print("DETAILED ISSUES")
        print("=" * 60)

        for r in results:
            if not r['valid']:
                print(f"\nDispute ID: {r['dispute_id']}")

                # First media issues
                fm_issues = r['first_media_validation'].get('issues', [])
                fm_warnings = r['first_media_validation'].get('warnings', [])
                if fm_issues or fm_warnings:
                    print("  First Media Date:")
                    for issue in fm_issues:
                        print(f"    ❌ {issue}")
                    for warning in fm_warnings:
                        print(f"    ⚠️ {warning}")

                # Sequence violations
                seq_violations = r['sequence_validation'].get('violations', [])
                if seq_violations:
                    print("  Date Sequence:")
                    for violation in seq_violations:
                        print(f"    ❌ {violation}")

                # Resolution issues
                res_issues = r['resolution_validation'].get('issues', [])
                res_warnings = r['resolution_validation'].get('warnings', [])
                if res_issues or res_warnings:
                    print("  Resolution Date:")
                    for issue in res_issues:
                        print(f"    ❌ {issue}")
                    for warning in res_warnings:
                        print(f"    ⚠️ {warning}")

                # OON issues
                oon_issues = r['oon_validation'].get('issues', [])
                oon_warnings = r['oon_validation'].get('warnings', [])
                if oon_issues or oon_warnings:
                    print("  OON Effective Date:")
                    for issue in oon_issues:
                        print(f"    ❌ {issue}")
                    for warning in oon_warnings:
                        print(f"    ⚠️ {warning}")

    # Final grade
    print("\n" + "=" * 60)
    if total_errors == 0:
        print("✓ DATA QUALITY: EXCELLENT (no errors)")
    elif total_errors < 10:
        print("⚠️ DATA QUALITY: GOOD (few errors)")
    elif total_errors < 50:
        print("⚠️ DATA QUALITY: FAIR (some errors)")
    else:
        print("❌ DATA QUALITY: NEEDS IMPROVEMENT (many errors)")
    print("=" * 60)

    return results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Validate date data quality in CSV')
    parser.add_argument('--csv', default='data/primary/disputes_enriched.csv',
                        help='Path to CSV file')
    parser.add_argument('--details', action='store_true',
                        help='Show detailed issues for each dispute')
    args = parser.parse_args()

    validate_csv_dates(args.csv, show_details=args.details)
