#!/usr/bin/env python3
"""
Manual patient estimation for remaining disputes without patient counts

Uses a simple formula based on available data:
- Beds-based: beds × 8,000 (annual visits per bed) × payer_share × 0.15
- This gives a conservative estimate of affected commercially insured patients
"""

import csv
from pathlib import Path
from datetime import datetime


# Payer commercial market share estimates by state
PAYER_SHARE = {
    ('Anthem', 'OH'): 0.25,
    ('United', 'WI'): 0.15,
    ('Cigna', 'AZ'): 0.10,
    ('BCBS', 'UT'): 0.35,
    ('HMSA', 'HI'): 0.50,  # Dominant in Hawaii
}


def estimate_payer_share(insurer_name: str, state: str) -> float:
    """Estimate payer's commercial market share"""

    # Normalize payer name
    payer = None
    insurer_lower = insurer_name.lower()

    if 'anthem' in insurer_lower:
        payer = 'Anthem'
    elif 'united' in insurer_lower:
        payer = 'United'
    elif 'cigna' in insurer_lower:
        payer = 'Cigna'
    elif 'bcbs' in insurer_lower or 'blue cross' in insurer_lower:
        payer = 'BCBS'
    elif 'hmsa' in insurer_lower:
        payer = 'HMSA'
    elif 'regence' in insurer_lower:
        payer = 'BCBS'  # Regence is BCBS affiliate

    # Check lookup
    if payer and (payer, state) in PAYER_SHARE:
        return PAYER_SHARE[(payer, state)]

    # Default assumptions
    if payer == 'United':
        return 0.15
    elif payer == 'Anthem':
        return 0.20
    elif payer == 'Cigna':
        return 0.08
    elif payer == 'BCBS':
        return 0.25

    return 0.12  # Conservative default


def estimate_patients_from_beds(beds: int, market_share_pct: float, payer_share: float) -> int:
    """
    Estimate affected patients from bed count

    Formula: beds × 8,000 × (market_share/100) × payer_share × 0.15

    - 8,000 = typical annual patient visits per bed (includes admissions, outpatient, ER)
    - market_share_pct = hospital's share of local market (from enrichment)
    - payer_share = payer's commercial insurance share in state
    - 0.15 = dispute impact factor (conservative, 10-20% of payer's customers affected)
    """
    if not beds or beds == 0:
        return None

    annual_patients = beds * 8000  # Total annual patient interactions
    market_adjusted = annual_patients * (market_share_pct / 100)  # Hospital's market
    payer_adjusted = market_adjusted * payer_share  # Payer's patients
    dispute_adjusted = int(payer_adjusted * 0.15)  # Actually affected

    return dispute_adjusted


def manual_estimate_patients(csv_path: str, output_path: str = None):
    """
    Manually estimate patients for remaining disputes

    Args:
        csv_path: Path to disputes CSV
        output_path: Path to write updated CSV (default: overwrite input)
    """
    csv_path = Path(csv_path)
    if output_path is None:
        output_path = csv_path
    else:
        output_path = Path(output_path)

    # Read disputes CSV
    print(f"Reading {csv_path}...")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        disputes = list(reader)

    print(f"Total disputes: {len(disputes)}")
    print()

    # Find disputes missing patient counts
    print("=" * 70)
    print("MANUAL PATIENT ESTIMATION")
    print("=" * 70)

    estimated = 0
    skipped = 0

    for dispute in disputes:
        # Skip if already has patient count
        if dispute.get('patients_affected') and dispute.get('patients_affected') != '':
            continue

        dispute_id = int(dispute['dispute_id'])
        system_name = dispute['system_name']
        insurer_name = dispute['insurer_name']
        state = dispute.get('state', dispute.get('system_hq_state', ''))

        # Get data
        beds = dispute.get('total_beds', '')
        market_share_pct = dispute.get('market_share_pct', '')

        if not beds or not market_share_pct:
            print(f"  ⊘ Dispute {dispute_id}: {system_name[:50]}")
            print(f"    Missing beds or market_share_pct")
            print()
            skipped += 1
            continue

        try:
            beds = int(float(beds))
            market_share_pct = float(market_share_pct)
        except (ValueError, TypeError):
            print(f"  ⊘ Dispute {dispute_id}: {system_name[:50]}")
            print(f"    Invalid beds ({beds}) or market_share ({market_share_pct})")
            print()
            skipped += 1
            continue

        # Estimate payer share
        payer_share = estimate_payer_share(insurer_name, state)

        # Calculate estimate
        patient_estimate = estimate_patients_from_beds(beds, market_share_pct, payer_share)

        if patient_estimate and patient_estimate > 0:
            # Update dispute
            dispute['patients_affected'] = patient_estimate
            dispute['patients_affected_source'] = 'estimated_bed_calculation'

            # Add enrichment note
            existing_notes = dispute.get('enrichment_notes', '').strip()
            timestamp = datetime.now().strftime('%Y-%m-%d')
            note = (f"Patient estimation {timestamp}: {patient_estimate:,} "
                   f"(bed-based calculation: {beds} beds × {market_share_pct}% market share × "
                   f"{payer_share:.0%} payer share × 0.15 dispute factor)")

            if existing_notes:
                dispute['enrichment_notes'] = f"{existing_notes}; {note}"
            else:
                dispute['enrichment_notes'] = note

            estimated += 1

            print(f"  ✓ Dispute {dispute_id}: {system_name[:45]}")
            print(f"    vs {insurer_name[:40]} ({state})")
            print(f"    Estimated: {patient_estimate:,} patients")
            print(f"    Basis: {beds} beds, {market_share_pct}% market share, {payer_share:.0%} payer share")
            print()
        else:
            skipped += 1

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Patient counts estimated: {estimated}")
    print(f"Disputes skipped (insufficient data): {skipped}")
    print()

    # Write updated CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(disputes)

    print(f"✓ Wrote updated data to {output_path}")
    print()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Manual patient estimation for remaining disputes')
    parser.add_argument('--csv', default='data/primary/disputes_enriched.csv',
                        help='Path to disputes CSV')
    parser.add_argument('--output', default=None,
                        help='Output path (default: overwrite input)')

    args = parser.parse_args()

    manual_estimate_patients(
        csv_path=args.csv,
        output_path=args.output
    )
