#!/usr/bin/env python3
"""
Regenerate datawrapper_range_plot_simple.csv with corrected dates and shortened names

Changes:
1. Apply corrected first_media_date values from validation work
2. Shorten dispute names to "Health System vs. Payer" format
3. Recalculate durations with corrected dates
"""

import csv
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.date_validation import parse_date


def shorten_payer_name(payer_name: str) -> str:
    """Shorten payer names to abbreviated format"""

    import re

    # State abbreviations map
    state_abbrevs = {
        'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
        'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
        'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
        'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
        'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
        'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
        'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
        'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
        'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
        'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
        'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
        'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
        'Wisconsin': 'WI', 'Wyoming': 'WY'
    }

    # Remove parent company names in parentheses (e.g., "Anthem (Elevance Health)" → "Anthem")
    payer_name = re.sub(r'\s*\([^)]*\)\s*', ' ', payer_name).strip()

    # Common abbreviations
    abbreviations = {
        'UnitedHealthcare': 'United',
        'UnitedHealth': 'United',
        'Blue Cross Blue Shield': 'BCBS',
        'Anthem Blue Cross Blue Shield': 'Anthem',
        'Anthem Blue Cross': 'Anthem',
        'Anthem': 'Anthem',
        'Blue Cross': 'BCBS',
        'Blue Shield': 'Blue Shield',
        'Premera Blue Cross Blue Shield': 'Premera',
        'Premera Blue Cross': 'Premera',
        'Cigna Healthcare': 'Cigna',
        'Cigna': 'Cigna',
        'ConnectiCare': 'ConnectiCare',
        'Tufts Health Direct': 'Tufts',
        'Regence BlueCross BlueShield': 'Regence',
        'Regence': 'Regence',
        'Florida Blue': 'Florida Blue',
        'CDPHP': 'CDPHP',
        'Healthfirst': 'Healthfirst',
        'Aetna': 'Aetna',
        'Humana': 'Humana',
    }

    # Try exact match first
    if payer_name in abbreviations:
        return abbreviations[payer_name]

    # Try partial matches
    for full_name, abbrev in abbreviations.items():
        if full_name in payer_name:
            # Handle state suffixes
            state_suffix = ''
            if ' of ' in payer_name:
                parts = payer_name.split(' of ')
                if len(parts) > 1:
                    state = parts[-1].strip()

                    # For BCBS, use state abbreviation without parentheses
                    if abbrev == 'BCBS' and state in state_abbrevs:
                        return f"{abbrev} {state_abbrevs[state]}"

                    # For other insurers, only keep state if it's short
                    if len(state) <= 20:
                        state_suffix = f' ({state})'

            return abbrev + state_suffix

    return payer_name


def shorten_system_name(system_name: str) -> str:
    """Shorten health system names by removing common suffixes"""

    # Remove common suffixes
    suffixes_to_remove = [
        'Health System',
        'Health',
        'Healthcare System',
        'Healthcare',
        'Medical Center',
        'Hospital',
        'Hospitals',
        'Regional Medical Center',
        'Care',
        'Health Network',
        'Network',
        '(physician staffing)',
        'Partners',
        'Medical',
    ]

    name = system_name.strip()

    # Fix HTML entity encoding (e.g., \u0026 → &)
    import html
    name = html.unescape(name)

    # Special cases
    if 'TeamHealth' in name:
        return 'TeamHealth'
    if 'UC Health (University of California)' in name:
        return 'UC Health'
    if 'SUNY Upstate' in name:
        return 'SUNY Upstate'
    if 'St. Luke' in name or "St. Luke's" in name:
        return "St. Luke's"
    if 'CommonSpirit' in name:
        return 'CommonSpirit'
    if 'HCAcare' in name:
        return 'HCA'
    if 'Lifespan' in name:
        return 'Lifespan'
    if 'Baylor Scott' in name:
        return 'Baylor Scott & White'

    # Remove suffixes
    for suffix in suffixes_to_remove:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()

    # Remove trailing commas and whitespace
    name = name.rstrip(',').strip()

    return name


def create_short_dispute_name(dispute: dict) -> str:
    """Create shortened dispute name: System vs. Payer"""

    system = shorten_system_name(dispute['system_name'])
    payer = shorten_payer_name(dispute['insurer_name'])

    return f"{system} vs. {payer}"


def regenerate_datawrapper_simple(csv_path: str, output_path: str):
    """
    Regenerate datawrapper simple CSV with corrected dates and shortened names

    Args:
        csv_path: Path to disputes_enriched.csv
        output_path: Path to write datawrapper CSV
    """

    # Read disputes
    print(f"Reading {csv_path}...")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        disputes = list(reader)

    print(f"Total disputes: {len(disputes)}")

    # Filter for resolved disputes with dates
    eligible_disputes = []

    for dispute in disputes:
        first_date = dispute.get('first_media_date', '').strip()
        resolution_date = dispute.get('resolution_date', '').strip()
        outcome = dispute.get('outcome_status', '')

        # Include resolved disputes and OON disputes with both dates
        if first_date and (
            (outcome == 'Resolved' and resolution_date) or
            (outcome in ['OON-Ongoing', 'OON-Permanent', 'Unknown'] and resolution_date)
        ):
            eligible_disputes.append(dispute)

    print(f"Eligible disputes for chart: {len(eligible_disputes)}")
    print()

    # Generate datawrapper rows
    datawrapper_rows = []

    for dispute in eligible_disputes:
        first_date_str = dispute['first_media_date']
        resolution_date_str = dispute['resolution_date']

        # Parse dates
        first_date = parse_date(first_date_str)
        resolution_date = parse_date(resolution_date_str)

        if not first_date or not resolution_date:
            continue

        # Calculate duration
        duration_days = (resolution_date - first_date).days

        # Filter out disputes with less than 30 days duration
        if duration_days < 30:
            continue

        # Create shortened dispute name with duration (no 'd' suffix)
        base_name = create_short_dispute_name(dispute)
        dispute_name = f"{base_name} - {duration_days}"

        # Get patients affected
        patients = dispute.get('patients_affected', '')

        datawrapper_rows.append({
            'Dispute': dispute_name,
            'First Reported': first_date_str,
            'Resolution Date': resolution_date_str,
            'Duration (days)': duration_days,
            'Outcome Status': dispute['outcome_status'],
            'Patients Affected': patients
        })

    # Sort by first reported date
    datawrapper_rows.sort(key=lambda x: x['First Reported'])

    # Write output
    print(f"Writing {len(datawrapper_rows)} disputes to {output_path}...")

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        fieldnames = [
            'Dispute',
            'First Reported',
            'Resolution Date',
            'Duration (days)',
            'Outcome Status',
            'Patients Affected'
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(datawrapper_rows)

    print(f"✓ Successfully regenerated datawrapper CSV")
    print()

    # Show sample of shortened names
    print("Sample of shortened dispute names:")
    for row in datawrapper_rows[:10]:
        print(f"  {row['Dispute']}")
    print()

    # Show disputes with corrected durations
    print("Disputes with updated durations (previously 0 days):")
    for row in datawrapper_rows:
        if 'Wellstar' in row['Dispute'] or 'WakeMed' in row['Dispute'] or \
           'Baylor' in row['Dispute'] or 'CaroMont' in row['Dispute']:
            print(f"  {row['Dispute']}: {row['Duration (days)']} days")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Regenerate datawrapper simple CSV')
    parser.add_argument('--csv', default='data/primary/disputes_enriched.csv',
                        help='Path to disputes CSV')
    parser.add_argument('--output', default='data/derived/datawrapper_range_plot_simple.csv',
                        help='Output path for datawrapper CSV')

    args = parser.parse_args()

    regenerate_datawrapper_simple(
        csv_path=args.csv,
        output_path=args.output
    )
