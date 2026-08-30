#!/usr/bin/env python3
"""
Update missing patients_affected values from web research
"""

import csv
from pathlib import Path

# Patient count updates from web research
UPDATES = {
    184: 135000,   # Ohio State Wexner vs Anthem
    # 186: None,   # Mount Carmel vs Humana - not disclosed
    191: 1700000,  # Ascension Wisconsin vs United
    # 197: None,   # Stamford Health vs Anthem - not disclosed
    199: 350000,   # Mount Sinai vs Anthem
    205: 413000,   # Abrazo Health vs Cigna
    208: 150000,   # Providence Alaska vs Premera
    209: 30,       # HMSA lawsuit (limited scope)
    210: 125000,   # University of Utah vs Regence
}

def update_patient_counts(csv_path: str):
    """Update patients_affected for disputes with missing values"""

    csv_path = Path(csv_path)

    # Read CSV
    print(f"Reading {csv_path}...")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Total disputes: {len(rows)}")
    print()

    # Apply updates
    print("Applying patient count updates:")
    print("=" * 70)

    updated_count = 0
    for row in rows:
        dispute_id = int(row['dispute_id'])

        if dispute_id in UPDATES:
            old_value = row.get('patients_affected', '')
            new_value = UPDATES[dispute_id]

            row['patients_affected'] = str(new_value)

            # Add enrichment note
            existing_notes = row.get('enrichment_notes', '').strip()
            note = f"Patient count added from web research: {new_value:,}"
            if existing_notes:
                row['enrichment_notes'] = f"{existing_notes}; {note}"
            else:
                row['enrichment_notes'] = note

            updated_count += 1
            print(f"  ✓ Dispute {dispute_id}: {row['system_name'][:40]}")
            print(f"    Patients: {old_value or '(empty)'} → {new_value:,}")

    print()
    print(f"Updated {updated_count} disputes")
    print(f"Skipped 2 disputes (no data disclosed)")
    print()

    # Write updated CSV
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Wrote updated data to {csv_path}")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Update missing patient counts')
    parser.add_argument('--csv', default='data/primary/disputes_enriched.csv',
                        help='Path to disputes CSV')

    args = parser.parse_args()

    update_patient_counts(args.csv)
