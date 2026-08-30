#!/usr/bin/env python3
"""
Add annotations to datawrapper_range_plot_simple.csv explaining why long disputes took so long
Focus on disputes with durations over ~4 months (120 days)
"""

import pandas as pd
import shutil
from datetime import datetime

def backup_file(file_path):
    """Create a backup of the file before modification"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    return backup_path

def add_annotations():
    """Add annotation column to datawrapper_range_plot_simple.csv"""

    file_path = "/Users/all/claude_code/payer_provider_disputes/data/derived/visualizations/datawrapper_range_plot_simple.csv"

    print("=" * 100)
    print("ADDING ANNOTATIONS TO DATAWRAPPER FILE")
    print("=" * 100)

    # Backup original file
    backup_path = backup_file(file_path)

    # Read the CSV
    df = pd.read_csv(file_path)
    print(f"\nTotal disputes: {len(df)}")
    print(f"Disputes over 120 days: {len(df[df['Duration (days)'] >= 120])}")

    # Annotation mapping - focus on disputes that took notably long
    # Key: Dispute name from CSV, Value: Brief annotation explaining why it took long
    annotations = {
        # 3+ years - exceptional case
        'Tryon vs. Humana - 1157': '3+ year Medicare Advantage dispute',

        # 1.5+ years - very long
        'Chesapeake Regional vs. Cigna - 580': '19-month standoff; small market',
        'Jefferson vs. Cigna - 517': '17-month negotiation; retroactive settlement',

        # 1+ years - notably long
        'Baton Rouge General vs. Aetna - 458': 'MA contract dropped after 15 months',
        'Northside vs. Anthem - 426': 'Court injunction Dec 2021; 14-month legal battle',
        'M Health Fairview vs. United - 410': 'Major system; 125K patients affected',
        'Providence vs. Aetna - 395': '13-month Oregon MA dispute',

        # ~1 year
        'VCU vs. Anthem - 365': 'Year-long academic medical center standoff',
        'Carson Tahoe vs. United - 365': 'Nevada state employee coverage dispute',
        'Scripps vs. Anthem - 363': 'Nearly year-long CA dispute; extended to 2026',
        'Envision vs. United - 334': '$91M arbitration award; staffing model conflict',

        # 9-10 months
        'Methodist Health vs. BCBS TN - 304': '10-month Tennessee regional dispute',
        'Montefiore vs. United - 303': '10-month NYC system dispute; 10 hospitals',
        'Providence vs. Blue Shield (California) - 276': 'Large CA system; 80K patients',
        'Wellstar vs. United - 271': 'Major GA system; 80K patients affected',

        # 8 months
        'Mount Carmel vs. Humana - 242': '8-month Humana MA network exit',
        'Trinity Health Michigan vs. Humana - 242': 'Parallel Trinity Health MA dispute',

        # 5-6 months
        'UNC vs. United - 167': 'Major academic center; 200K patients at risk',
        'WakeMed vs. United - 153': '5-month NC regional dispute',
        'Memorial Hermann vs. BCBS TX - 143': 'Large TX system; 112K patients',

        # 4 months
        'Bon Secours Mercy vs. Anthem - 123': 'Ongoing out-of-network since May 2023',
        'Conway Regional vs. United - 122': '4-month Arkansas regional dispute',
        'CaroMont vs. United - 102': '3.5-month NC regional dispute',

        # Additional notable cases (3-4 months)
        'Northside Hospital Gwinnett vs. United - 92': 'Part of larger Northside-United negotiations',
        'Northeast Georgia vs. Anthem - 92': '3-month GA regional dispute (2021)',
        'SUNY Upstate vs. United - 92': '3-month upstate NY academic center',
        'Main Line vs. Cigna - 92': '3-month suburban Philadelphia dispute',
        'Northeast Georgia vs. Anthem - 92': '3-month GA dispute resolved early 2020',
    }

    # Add Annotation column
    df['Annotation'] = df['Dispute'].map(annotations)

    # Fill remaining annotations with empty string (for shorter disputes)
    df['Annotation'] = df['Annotation'].fillna('')

    # Report statistics
    annotated_count = len(df[df['Annotation'] != ''])
    print(f"\nAnnotations added: {annotated_count} out of {len(df)} disputes")

    # Show preview of annotated disputes
    print(f"\n{'=' * 100}")
    print("PREVIEW OF ANNOTATED DISPUTES (Top 10 by duration)")
    print('=' * 100)

    preview = df[df['Annotation'] != ''].nlargest(10, 'Duration (days)')
    for idx, row in preview.iterrows():
        print(f"\n{row['Dispute']}")
        print(f"  Duration: {row['Duration (days)']} days")
        print(f"  Annotation: {row['Annotation']}")

    # Save updated file
    df.to_csv(file_path, index=False)

    print(f"\n{'=' * 100}")
    print(f"✅ File updated: {file_path}")
    print(f"✅ Backup created: {backup_path}")
    print(f"✅ Total annotated disputes: {annotated_count}")
    print('=' * 100)

    return annotated_count

def main():
    """Main function"""
    print("\n" + "=" * 100)
    print("ADD ANNOTATIONS TO DATAWRAPPER FILE")
    print("=" * 100)
    print("\nThis script adds an 'Annotation' column to explain why certain disputes")
    print("took longer to resolve. Focuses on disputes over ~4 months duration.")
    print("=" * 100 + "\n")

    annotated_count = add_annotations()

    print(f"\n✅ Complete! Added {annotated_count} annotations to the datawrapper file.")
    print("=" * 100 + "\n")

if __name__ == "__main__":
    main()
