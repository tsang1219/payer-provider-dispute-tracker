#!/usr/bin/env python3
"""
Outcome Status Correction Script

Applies corrections to outcome_status field based on validation report.
- AUTO-APPLIES high confidence corrections
- PROMPTS for medium confidence corrections
- FLAGS low confidence for manual review

Usage:
    python scripts/correct_outcome_status.py
    python scripts/correct_outcome_status.py --dry-run
    python scripts/correct_outcome_status.py --auto-all  # Skip prompts
"""

import csv
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import shutil


# ============================================================================
# CONFIGURATION
# ============================================================================

CSV_PATH = 'data/primary/disputes_enriched.csv'
VALIDATION_REPORT = 'output/outcome_status_validation_report.json'
CONFIDENCE_HIGH = 'high'
CONFIDENCE_MEDIUM = 'medium'
CONFIDENCE_LOW = 'low'


# ============================================================================
# CORRECTION FUNCTIONS
# ============================================================================

def create_backup(csv_path: str) -> str:
    """Create timestamped backup of CSV file."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = csv_path.replace('.csv', f'_backup_{timestamp}.csv')
    shutil.copy2(csv_path, backup_path)
    return backup_path


def load_disputes(csv_path: str) -> tuple[List[Dict], List[str]]:
    """Load disputes from CSV."""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        disputes = list(reader)
    return disputes, fieldnames


def save_disputes(disputes: List[Dict], fieldnames: List[str], csv_path: str):
    """Save disputes back to CSV."""
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(disputes)


def apply_correction(dispute: Dict, correction: Dict, audit_log: List[Dict]) -> bool:
    """
    Apply a single correction to a dispute.

    Returns:
        True if correction was applied, False otherwise
    """
    dispute_id = dispute['dispute_id']

    # Check if this is the right dispute
    if dispute_id != str(correction['dispute_id']):
        return False

    # Record old values
    old_status = dispute.get('outcome_status', '')
    old_date = dispute.get('resolution_date', '')
    old_detail = dispute.get('outcome_status_detail', '')

    # Apply status change
    if 'suggested_status' in correction:
        dispute['outcome_status'] = correction['suggested_status']

    # Apply resolution date if suggested
    if 'suggested_date' in correction and correction['suggested_date']:
        dispute['resolution_date'] = correction['suggested_date']

    # Apply outcome_status_detail if suggested
    if 'suggested_detail' in correction:
        dispute['outcome_status_detail'] = correction['suggested_detail']

    # Update last_updated timestamp
    dispute['last_updated'] = datetime.now().isoformat()

    # Record in audit log
    audit_entry = {
        'dispute_id': dispute_id,
        'dispute_name': dispute.get('dispute_name'),
        'timestamp': datetime.now().isoformat(),
        'old_status': old_status,
        'new_status': dispute['outcome_status'],
        'old_resolution_date': old_date,
        'new_resolution_date': dispute.get('resolution_date', ''),
        'old_detail': old_detail,
        'new_detail': dispute.get('outcome_status_detail', ''),
        'reason': correction.get('reason', ''),
        'confidence': correction.get('confidence', ''),
        'evidence': correction.get('evidence', '')[:200]
    }
    audit_log.append(audit_entry)

    return True


def prompt_for_correction(correction: Dict) -> bool:
    """Prompt user to confirm a medium-confidence correction."""
    print("\n" + "="*80)
    print(f"ID {correction['dispute_id']}: {correction['dispute_name'][:60]}")
    print("="*80)
    print(f"Current status: {correction['current_status']}")
    print(f"Issue: {correction['issue']}")
    print(f"\nSuggested change:")
    if 'suggested_status' in correction:
        print(f"  outcome_status: {correction['current_status']} → {correction['suggested_status']}")
    if 'suggested_date' in correction and correction['suggested_date']:
        print(f"  resolution_date: → {correction['suggested_date']}")
    if 'suggested_detail' in correction:
        print(f"  outcome_status_detail: → {correction['suggested_detail']}")
    print(f"\nReason: {correction['reason']}")
    print(f"Confidence: {correction['confidence']}")
    print(f"\nEvidence: {correction['evidence'][:150]}")
    print("-"*80)

    while True:
        response = input("Apply this correction? [y/n/q(uit)]: ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            print("  → Skipped")
            return False
        elif response in ['q', 'quit']:
            print("\nExiting...")
            exit(0)
        else:
            print("  Please enter y, n, or q")


# ============================================================================
# MAIN CORRECTION LOGIC
# ============================================================================

def process_corrections(
    validation_report: Dict,
    csv_path: str,
    dry_run: bool = False,
    auto_all: bool = False
) -> Dict:
    """
    Process all corrections from validation report.

    Returns:
        Summary statistics of corrections applied
    """
    # Load disputes
    print(f"\nLoading disputes from {csv_path}...")
    disputes, fieldnames = load_disputes(csv_path)
    print(f"Loaded {len(disputes)} disputes")

    # Create dispute lookup by ID
    dispute_by_id = {d['dispute_id']: d for d in disputes}

    # Initialize tracking
    audit_log = []
    stats = {
        'high_applied': 0,
        'medium_applied': 0,
        'medium_skipped': 0,
        'low_flagged': 0,
        'total_processed': 0
    }

    # Process each category of discrepancies
    all_corrections = []
    for category, corrections in validation_report['discrepancies'].items():
        all_corrections.extend(corrections)

    # Sort by confidence (high first, then medium, then low)
    confidence_order = {CONFIDENCE_HIGH: 0, CONFIDENCE_MEDIUM: 1, CONFIDENCE_LOW: 2}
    all_corrections.sort(key=lambda x: confidence_order.get(x.get('confidence'), 3))

    print(f"\nProcessing {len(all_corrections)} corrections...")
    print("="*80)

    # Process HIGH confidence - auto-apply
    high_corrections = [c for c in all_corrections if c.get('confidence') == CONFIDENCE_HIGH]
    if high_corrections:
        print(f"\nAUTO-APPLYING {len(high_corrections)} HIGH confidence corrections...")
        for correction in high_corrections:
            dispute_id = str(correction['dispute_id'])
            if dispute_id in dispute_by_id:
                apply_correction(dispute_by_id[dispute_id], correction, audit_log)
                stats['high_applied'] += 1
                print(f"  ✓ ID {dispute_id}: {correction['dispute_name'][:50]}")

    # Process MEDIUM confidence - prompt (unless auto_all)
    medium_corrections = [c for c in all_corrections if c.get('confidence') == CONFIDENCE_MEDIUM]
    if medium_corrections:
        print(f"\n\nREVIEWING {len(medium_corrections)} MEDIUM confidence corrections...")

        if auto_all:
            print("  (Auto-applying all - --auto-all flag enabled)")
            for correction in medium_corrections:
                dispute_id = str(correction['dispute_id'])
                if dispute_id in dispute_by_id:
                    apply_correction(dispute_by_id[dispute_id], correction, audit_log)
                    stats['medium_applied'] += 1
                    print(f"  ✓ ID {dispute_id}: {correction['dispute_name'][:50]}")
        else:
            for correction in medium_corrections:
                dispute_id = str(correction['dispute_id'])
                if dispute_id in dispute_by_id:
                    if prompt_for_correction(correction):
                        apply_correction(dispute_by_id[dispute_id], correction, audit_log)
                        stats['medium_applied'] += 1
                        print(f"  ✓ Applied")
                    else:
                        stats['medium_skipped'] += 1

    # Process LOW confidence - flag for manual review
    low_corrections = [c for c in all_corrections if c.get('confidence') == CONFIDENCE_LOW]
    if low_corrections:
        print(f"\n\nFLAGGED {len(low_corrections)} LOW confidence corrections for manual review:")
        print("="*80)
        for correction in low_corrections:
            print(f"  ! ID {correction['dispute_id']}: {correction['dispute_name'][:50]}")
            print(f"    Issue: {correction['issue']}")
            print(f"    Reason: {correction['reason']}")
            stats['low_flagged'] += 1

    stats['total_processed'] = len(all_corrections)

    # Save changes (if not dry run)
    if dry_run:
        print("\n" + "="*80)
        print("DRY RUN MODE - No changes saved")
        print("="*80)
    else:
        # Create backup
        backup_path = create_backup(csv_path)
        print(f"\n✓ Created backup: {backup_path}")

        # Save updated disputes
        save_disputes(disputes, fieldnames, csv_path)
        print(f"✓ Updated {csv_path}")

        # Save audit log
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        audit_path = f'output/outcome_status_corrections_{timestamp}.json'
        Path(audit_path).parent.mkdir(parents=True, exist_ok=True)
        with open(audit_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'backup_file': backup_path,
                'statistics': stats,
                'corrections': audit_log
            }, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved audit log: {audit_path}")

    return stats


def print_summary(stats: Dict):
    """Print summary of corrections."""
    print("\n" + "="*80)
    print("CORRECTION SUMMARY")
    print("="*80)
    print(f"  HIGH confidence (auto-applied):     {stats['high_applied']}")
    print(f"  MEDIUM confidence (applied):        {stats['medium_applied']}")
    print(f"  MEDIUM confidence (skipped):        {stats['medium_skipped']}")
    print(f"  LOW confidence (flagged):           {stats['low_flagged']}")
    print("-"*80)
    print(f"  TOTAL corrections applied:          {stats['high_applied'] + stats['medium_applied']}")
    print(f"  TOTAL flagged for manual review:    {stats['low_flagged']}")
    print("="*80)


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Apply outcome_status corrections based on validation report'
    )
    parser.add_argument(
        '--validation-report',
        default=VALIDATION_REPORT,
        help=f'Path to validation report JSON (default: {VALIDATION_REPORT})'
    )
    parser.add_argument(
        '--csv',
        default=CSV_PATH,
        help=f'Path to disputes CSV (default: {CSV_PATH})'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview corrections without saving changes'
    )
    parser.add_argument(
        '--auto-all',
        action='store_true',
        help='Auto-apply MEDIUM confidence corrections without prompting'
    )

    args = parser.parse_args()

    # Load validation report
    print(f"Loading validation report from {args.validation_report}...")
    with open(args.validation_report, 'r', encoding='utf-8') as f:
        validation_report = json.load(f)

    print(f"Found {validation_report['total_discrepancies']} discrepancies")

    # Process corrections
    stats = process_corrections(
        validation_report=validation_report,
        csv_path=args.csv,
        dry_run=args.dry_run,
        auto_all=args.auto_all
    )

    # Print summary
    print_summary(stats)

    if not args.dry_run:
        print("\nNext steps:")
        print("  1. Review the audit log for all changes made")
        print("  2. Run: python scripts/validate_dates.py")
        print("  3. Manually review low-confidence flagged cases")
        print("  4. Regenerate visualizations: python scripts/regenerate_datawrapper_simple.py")


if __name__ == '__main__':
    main()
