#!/usr/bin/env python3
"""
Outcome Status Consistency Validation

Detects discrepancies between outcome_status field and other fields (notes, resolution_date).
Generates a report with suggested corrections based on classification rules.

Usage:
    python scripts/validate_outcome_status_consistency.py
    python scripts/validate_outcome_status_consistency.py --report-only
    python scripts/validate_outcome_status_consistency.py --output validation_report.json
"""

import csv
import json
import re
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path


# ============================================================================
# CONFIGURATION
# ============================================================================

CSV_PATH = 'data/primary/disputes_enriched.csv'

# Confidence levels for corrections
CONFIDENCE_HIGH = 'high'
CONFIDENCE_MEDIUM = 'medium'
CONFIDENCE_LOW = 'low'


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_hybrid_dispute(notes: str) -> bool:
    """
    Check if notes indicate partial resolution (some components resolved, some ongoing).

    Examples:
    - "MA resolved; commercial ongoing"
    - "Commercial resolved Dec 15, 2024; Medicare Advantage individual plans remain out"
    """
    if not notes:
        return False

    hybrid_patterns = [
        r'(MA|Medicare Advantage).*(resolved|agreement).*commercial.*(ongoing|out|remain)',
        r'commercial.*(resolved|agreement).*(MA|Medicare).*(ongoing|out|remain)',
        r'partially resolved',
        r'some.*in[- ]network.*some.*out',
        r'(resolved|agreement).*remain.*out',
        r'(PPO|HMO).*(resolved|in).*(HMO|PPO|Medicaid).*(out|ongoing)',
    ]

    return any(re.search(pattern, notes, re.IGNORECASE) for pattern in hybrid_patterns)


def extract_resolution_date_from_notes(notes: str) -> Tuple[Optional[str], str]:
    """
    Extract resolution date from notes using regex patterns.

    Returns:
        (date_string, confidence) or (None, None) if not found
    """
    if not notes:
        return None, None

    # Date patterns to search for
    date_patterns = [
        # "resolved July 1, 2024" or "agreement March 15, 2023"
        (r'(resolved|agreement|back in[- ]network|effective)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})', CONFIDENCE_HIGH),
        # "resolved July 2024" or "agreement March 2023"
        (r'(resolved|agreement|new contract)\s+([A-Z][a-z]+\s+\d{4})', CONFIDENCE_MEDIUM),
        # "new contract March 1"
        (r'new contract\s+([A-Z][a-z]+\s+\d{1,2})', CONFIDENCE_LOW),
    ]

    for pattern, confidence in date_patterns:
        match = re.search(pattern, notes, re.IGNORECASE)
        if match:
            date_str = match.group(2) if match.lastindex >= 2 else match.group(1)
            return date_str, confidence

    return None, None


def is_old_dispute(first_media_date: str, months: int = 12) -> bool:
    """Check if dispute is older than N months based on first_media_date."""
    if not first_media_date:
        return False

    try:
        first_date = datetime.fromisoformat(first_media_date)
        cutoff = datetime.now() - timedelta(days=months*30)
        return first_date < cutoff
    except:
        return False


def contains_keywords(text: str, keywords: List[str], require_all: bool = False) -> bool:
    """Check if text contains any (or all) keywords (case-insensitive)."""
    if not text:
        return False

    text_lower = text.lower()
    matches = [kw.lower() in text_lower for kw in keywords]

    return all(matches) if require_all else any(matches)


# ============================================================================
# DISCREPANCY DETECTION
# ============================================================================

def detect_permanent_with_resolution(disputes: List[Dict]) -> List[Dict]:
    """
    Find OON-Permanent cases with resolution_date or agreement language.
    These likely should be marked as Resolved.
    """
    discrepancies = []

    for dispute in disputes:
        if dispute.get('outcome_status') != 'OON-Permanent':
            continue

        resolution_date = dispute.get('resolution_date', '').strip()
        notes = dispute.get('notes', '')

        # Check for resolution_date
        if resolution_date:
            discrepancies.append({
                'dispute_id': dispute['dispute_id'],
                'dispute_name': dispute['dispute_name'],
                'current_status': 'OON-Permanent',
                'issue': 'OON-Permanent with resolution_date populated',
                'evidence': f'resolution_date={resolution_date}',
                'suggested_status': 'Resolved',
                'confidence': CONFIDENCE_HIGH,
                'reason': 'Resolution date exists, should be Resolved'
            })
            continue

        # Check for agreement language in notes
        agreement_keywords = ['agreement reached', 'new contract', 'back in-network', 'multi-year agreement']
        if contains_keywords(notes, agreement_keywords):
            discrepancies.append({
                'dispute_id': dispute['dispute_id'],
                'dispute_name': dispute['dispute_name'],
                'current_status': 'OON-Permanent',
                'issue': 'OON-Permanent with agreement language in notes',
                'evidence': notes[:150],
                'suggested_status': 'Resolved',
                'confidence': CONFIDENCE_HIGH,
                'reason': 'Notes contain agreement language'
            })

    return discrepancies


def detect_ongoing_with_termination(disputes: List[Dict]) -> List[Dict]:
    """
    Find OON-Ongoing cases with termination/dropped language.
    These might should be marked as OON-Permanent if old enough.
    """
    discrepancies = []

    for dispute in disputes:
        if dispute.get('outcome_status') != 'OON-Ongoing':
            continue

        notes = dispute.get('notes', '')
        first_media_date = dispute.get('first_media_date', '')

        # Check for termination language
        termination_keywords = ['terminated', 'dropped', 'ended']
        if not contains_keywords(notes, termination_keywords):
            continue

        # Check age
        is_old = is_old_dispute(first_media_date, months=12)

        if is_old:
            discrepancies.append({
                'dispute_id': dispute['dispute_id'],
                'dispute_name': dispute['dispute_name'],
                'current_status': 'OON-Ongoing',
                'issue': 'OON-Ongoing with termination language + 12+ months old',
                'evidence': f'{notes[:100]}... | first_media_date={first_media_date}',
                'suggested_status': 'OON-Permanent',
                'confidence': CONFIDENCE_MEDIUM,
                'reason': 'Termination language + 12+ months with no resolution'
            })
        else:
            # Still flag but lower confidence
            discrepancies.append({
                'dispute_id': dispute['dispute_id'],
                'dispute_name': dispute['dispute_name'],
                'current_status': 'OON-Ongoing',
                'issue': 'OON-Ongoing with termination language (recent)',
                'evidence': notes[:100],
                'suggested_status': 'OON-Ongoing',  # No change suggested
                'confidence': CONFIDENCE_LOW,
                'reason': 'Has termination language but < 12 months old'
            })

    return discrepancies


def detect_oon_with_resolution_date(disputes: List[Dict]) -> List[Dict]:
    """
    Find OON-* cases with populated resolution_date.
    Check for hybrid status before suggesting change to Resolved.
    """
    discrepancies = []

    for dispute in disputes:
        outcome_status = dispute.get('outcome_status', '')
        if outcome_status not in ['OON-Ongoing', 'OON-Permanent']:
            continue

        resolution_date = dispute.get('resolution_date', '').strip()
        if not resolution_date:
            continue

        notes = dispute.get('notes', '')

        # Check if hybrid dispute
        if is_hybrid_dispute(notes):
            discrepancies.append({
                'dispute_id': dispute['dispute_id'],
                'dispute_name': dispute['dispute_name'],
                'current_status': outcome_status,
                'issue': 'Hybrid dispute - partial resolution',
                'evidence': notes[:150],
                'suggested_status': 'OON-Ongoing',
                'suggested_detail': 'Partial resolution - see notes for details',
                'confidence': CONFIDENCE_HIGH,
                'reason': 'Hybrid status: some components resolved, some ongoing'
            })
        else:
            discrepancies.append({
                'dispute_id': dispute['dispute_id'],
                'dispute_name': dispute['dispute_name'],
                'current_status': outcome_status,
                'issue': f'{outcome_status} with resolution_date populated',
                'evidence': f'resolution_date={resolution_date}; notes={notes[:100]}',
                'suggested_status': 'Resolved',
                'confidence': CONFIDENCE_HIGH,
                'reason': 'Resolution date exists and no hybrid language found'
            })

    return discrepancies


def detect_resolved_without_date(disputes: List[Dict]) -> List[Dict]:
    """
    Find Resolved cases missing resolution_date.
    Attempt to extract date from notes.
    """
    discrepancies = []

    for dispute in disputes:
        if dispute.get('outcome_status') != 'Resolved':
            continue

        resolution_date = dispute.get('resolution_date', '').strip()
        if resolution_date:
            continue  # Has date, no issue

        notes = dispute.get('notes', '')

        # Try to extract date from notes
        extracted_date, confidence = extract_resolution_date_from_notes(notes)

        if extracted_date:
            discrepancies.append({
                'dispute_id': dispute['dispute_id'],
                'dispute_name': dispute['dispute_name'],
                'current_status': 'Resolved',
                'issue': 'Resolved without resolution_date',
                'evidence': f'Extracted "{extracted_date}" from notes: {notes[:100]}',
                'suggested_date': extracted_date,
                'confidence': confidence,
                'reason': f'Date extracted from notes with {confidence} confidence'
            })
        else:
            discrepancies.append({
                'dispute_id': dispute['dispute_id'],
                'dispute_name': dispute['dispute_name'],
                'current_status': 'Resolved',
                'issue': 'Resolved without resolution_date (extraction failed)',
                'evidence': notes[:100] if notes else 'No notes available',
                'suggested_date': None,
                'confidence': CONFIDENCE_LOW,
                'reason': 'Could not extract date from notes - manual review needed'
            })

    return discrepancies


# ============================================================================
# MAIN VALIDATION
# ============================================================================

def validate_all_disputes(csv_path: str = CSV_PATH) -> Dict:
    """
    Run all validation checks and compile comprehensive report.
    """
    # Load disputes
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        disputes = list(reader)

    print(f"\nLoaded {len(disputes)} disputes from {csv_path}")
    print("Running validation checks...\n")

    # Run all checks
    results = {
        'permanent_with_resolution': detect_permanent_with_resolution(disputes),
        'ongoing_with_termination': detect_ongoing_with_termination(disputes),
        'oon_with_resolution_date': detect_oon_with_resolution_date(disputes),
        'resolved_without_date': detect_resolved_without_date(disputes),
    }

    # Count by confidence
    all_discrepancies = []
    for category, items in results.items():
        all_discrepancies.extend(items)

    confidence_counts = {
        CONFIDENCE_HIGH: len([d for d in all_discrepancies if d.get('confidence') == CONFIDENCE_HIGH]),
        CONFIDENCE_MEDIUM: len([d for d in all_discrepancies if d.get('confidence') == CONFIDENCE_MEDIUM]),
        CONFIDENCE_LOW: len([d for d in all_discrepancies if d.get('confidence') == CONFIDENCE_LOW]),
    }

    # Compile report
    report = {
        'timestamp': datetime.now().isoformat(),
        'csv_path': csv_path,
        'total_disputes': len(disputes),
        'total_discrepancies': len(all_discrepancies),
        'by_category': {cat: len(items) for cat, items in results.items()},
        'by_confidence': confidence_counts,
        'discrepancies': results,
    }

    return report


def print_summary(report: Dict):
    """Print human-readable summary of validation report."""
    print("\n" + "="*80)
    print("OUTCOME STATUS CONSISTENCY VALIDATION REPORT")
    print("="*80)
    print(f"\nTimestamp: {report['timestamp']}")
    print(f"Data source: {report['csv_path']}")
    print(f"Total disputes: {report['total_disputes']}")
    print(f"\n{'TOTAL DISCREPANCIES FOUND:'} {report['total_discrepancies']}")

    print("\n" + "-"*80)
    print("BY CATEGORY:")
    print("-"*80)
    for category, count in report['by_category'].items():
        print(f"  {category:40} {count:3} issues")

    print("\n" + "-"*80)
    print("BY CONFIDENCE LEVEL:")
    print("-"*80)
    for confidence, count in report['by_confidence'].items():
        symbol = "✓" if confidence == CONFIDENCE_HIGH else ("?" if confidence == CONFIDENCE_MEDIUM else "!")
        print(f"  {symbol} {confidence.upper():10} {count:3} issues")

    print("\n" + "-"*80)
    print("DETAILED FINDINGS:")
    print("-"*80)

    for category, discrepancies in report['discrepancies'].items():
        if not discrepancies:
            continue

        print(f"\n{category.replace('_', ' ').title()} ({len(discrepancies)} issues):")
        print("-" * 80)

        for d in discrepancies[:5]:  # Show first 5 of each category
            print(f"\n  ID {d['dispute_id']}: {d['dispute_name'][:50]}")
            print(f"    Current: {d['current_status']}")
            print(f"    Issue: {d['issue']}")
            if 'suggested_status' in d:
                print(f"    Suggested: {d['suggested_status']} ({d['confidence']} confidence)")
            if 'suggested_date' in d:
                print(f"    Suggested date: {d['suggested_date']}")
            print(f"    Reason: {d['reason']}")
            print(f"    Evidence: {d['evidence'][:100]}")

        if len(discrepancies) > 5:
            print(f"\n  ... and {len(discrepancies) - 5} more")

    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Review the full JSON report for all discrepancies")
    print("2. Run: python scripts/correct_outcome_status.py")
    print("   - Will auto-apply HIGH confidence corrections")
    print("   - Will prompt for MEDIUM confidence corrections")
    print("   - Will flag LOW confidence for manual review")
    print("="*80 + "\n")


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Validate outcome_status consistency across disputes dataset'
    )
    parser.add_argument(
        '--output', '-o',
        default='output/outcome_status_validation_report.json',
        help='Output path for JSON report (default: output/outcome_status_validation_report.json)'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Only print summary, don\'t save JSON report'
    )
    parser.add_argument(
        '--csv',
        default=CSV_PATH,
        help=f'Path to disputes CSV (default: {CSV_PATH})'
    )

    args = parser.parse_args()

    # Run validation
    report = validate_all_disputes(csv_path=args.csv)

    # Print summary
    print_summary(report)

    # Save JSON report
    if not args.report_only:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"Full report saved to: {output_path}")


if __name__ == '__main__':
    main()
