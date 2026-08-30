#!/usr/bin/env python3
"""
Duplicate Detection Script for Datawrapper Range Plot Data
Identifies various types of duplicates and inconsistencies in dispute records.
"""

import pandas as pd
from collections import defaultdict
import re

def extract_base_name(dispute_name):
    """Extract base name without duration suffix"""
    # Remove the " - XXX" duration pattern at the end
    match = re.match(r'(.+?)\s*-\s*\d+$', dispute_name)
    if match:
        return match.group(1).strip()
    return dispute_name.strip()

def analyze_duplicates(csv_path):
    """Analyze and report on duplicates in the dataset"""

    # Read the CSV
    df = pd.read_csv(csv_path)

    # Remove any empty rows
    df = df.dropna(subset=['Dispute'])

    print("=" * 80)
    print("DUPLICATE ANALYSIS REPORT")
    print("=" * 80)
    print(f"\nTotal rows in file: {len(df)}")
    print()

    # Extract base names
    df['Base_Name'] = df['Dispute'].apply(extract_base_name)

    # 1. EXACT DUPLICATES (same dispute name)
    print("\n" + "=" * 80)
    print("1. EXACT DUPLICATE DISPUTE NAMES")
    print("=" * 80)

    dispute_counts = df['Dispute'].value_counts()
    exact_duplicates = dispute_counts[dispute_counts > 1]

    if len(exact_duplicates) > 0:
        print(f"\nFound {len(exact_duplicates)} dispute names with exact duplicates:\n")
        for dispute_name, count in exact_duplicates.items():
            print(f"\n'{dispute_name}' appears {count} times:")
            dupes = df[df['Dispute'] == dispute_name]
            for idx, row in dupes.iterrows():
                print(f"  Row {idx + 2}: {row['First Reported']} to {row['Resolution Date']} "
                      f"({row['Duration (days)']} days, {row['Patients Affected']} patients)")
    else:
        print("\nNo exact duplicate dispute names found.")

    # 2. SAME BASE NAME BUT DIFFERENT DURATIONS
    print("\n\n" + "=" * 80)
    print("2. SAME BASE NAME WITH DIFFERENT DURATIONS")
    print("=" * 80)

    base_name_groups = df.groupby('Base_Name')
    name_with_multiple_durations = []

    for base_name, group in base_name_groups:
        if len(group) > 1:
            # Check if they have different duration values in the name
            unique_disputes = group['Dispute'].unique()
            if len(unique_disputes) > 1:
                name_with_multiple_durations.append((base_name, group))

    if name_with_multiple_durations:
        print(f"\nFound {len(name_with_multiple_durations)} base names with different duration suffixes:\n")
        for base_name, group in name_with_multiple_durations:
            print(f"\n'{base_name}':")
            for idx, row in group.iterrows():
                print(f"  Row {idx + 2}: {row['Dispute']}")
                print(f"    Dates: {row['First Reported']} to {row['Resolution Date']}")
                print(f"    Duration: {row['Duration (days)']} days, Patients: {row['Patients Affected']}")
    else:
        print("\nNo disputes with same base name but different durations found.")

    # 3. SAME BASE NAME WITH DIFFERENT YEARS
    print("\n\n" + "=" * 80)
    print("3. SAME BASE NAME ACROSS DIFFERENT YEARS")
    print("=" * 80)

    df['Year'] = pd.to_datetime(df['First Reported']).dt.year

    base_name_year_groups = df.groupby('Base_Name')
    multi_year_disputes = []

    for base_name, group in base_name_year_groups:
        if len(group) > 1:
            years = group['Year'].unique()
            if len(years) > 1:
                multi_year_disputes.append((base_name, group))

    if multi_year_disputes:
        print(f"\nFound {len(multi_year_disputes)} disputes occurring across different years:\n")
        print("⚠️  These may represent separate disputes or data entry errors:\n")
        for base_name, group in multi_year_disputes:
            print(f"\n'{base_name}':")
            for idx, row in group.iterrows():
                print(f"  Row {idx + 2}: {row['Dispute']} (Year: {row['Year']})")
                print(f"    Dates: {row['First Reported']} to {row['Resolution Date']}")
                print(f"    Duration: {row['Duration (days)']} days, Patients: {row['Patients Affected']}")
    else:
        print("\nNo disputes spanning different years found.")

    # 4. SIMILAR DATES WITH DIFFERENT ATTRIBUTES
    print("\n\n" + "=" * 80)
    print("4. POTENTIAL DUPLICATES WITH INCONSISTENT DATA")
    print("=" * 80)

    base_name_groups = df.groupby('Base_Name')
    inconsistent_data = []

    for base_name, group in base_name_groups:
        if len(group) > 1:
            # Check for same dates but different durations or patient counts
            date_groups = group.groupby(['First Reported', 'Resolution Date'])
            for dates, date_group in date_groups:
                if len(date_group) > 1:
                    durations = date_group['Duration (days)'].unique()
                    patients = date_group['Patients Affected'].unique()
                    if len(durations) > 1 or len(patients) > 1:
                        inconsistent_data.append((base_name, date_group))

    if inconsistent_data:
        print(f"\nFound {len(inconsistent_data)} groups with same base name and dates but different attributes:\n")
        for base_name, group in inconsistent_data:
            print(f"\n'{base_name}':")
            for idx, row in group.iterrows():
                print(f"  Row {idx + 2}: {row['Dispute']}")
                print(f"    Duration: {row['Duration (days)']} days, Patients: {row['Patients Affected']}")
    else:
        print("\nNo inconsistent data found for same dispute and dates.")

    # 5. SUMMARY AND RECOMMENDATIONS
    print("\n\n" + "=" * 80)
    print("5. SUMMARY AND RECOMMENDATIONS")
    print("=" * 80)

    total_issues = len(exact_duplicates) + len(name_with_multiple_durations) + len(multi_year_disputes)

    print(f"\nTotal potential duplicate issues: {total_issues}")
    print(f"  - Exact duplicate names: {len(exact_duplicates)}")
    print(f"  - Same base name, different durations: {len(name_with_multiple_durations)}")
    print(f"  - Same base name, different years: {len(multi_year_disputes)}")

    print("\n\nRECOMMENDATIONS:")
    print("\n1. For EXACT duplicates: Keep the row with the most accurate/complete data")
    print("   - Verify dates against source documentation")
    print("   - Check patient counts for accuracy")

    print("\n2. For DIFFERENT DURATIONS with same base name:")
    print("   - Recalculate duration from First Reported to Resolution Date")
    print("   - Update the dispute name suffix to match the actual duration")
    print("   - If dates differ, these may be separate disputes - verify")

    print("\n3. For DIFFERENT YEARS:")
    print("   - Verify if these are truly separate disputes")
    print("   - If not separate, keep only the correct instance")
    print("   - Consider adding a year identifier if truly separate events")

    print("\n\n" + "=" * 80)
    print("ROWS TO REVIEW MANUALLY")
    print("=" * 80)

    # Collect all problematic row numbers
    review_rows = set()

    # Add exact duplicates
    for dispute_name in exact_duplicates.index:
        rows = df[df['Dispute'] == dispute_name].index + 2
        review_rows.update(rows)

    # Add multi-duration disputes
    for base_name, group in name_with_multiple_durations:
        review_rows.update(group.index + 2)

    # Add multi-year disputes
    for base_name, group in multi_year_disputes:
        review_rows.update(group.index + 2)

    if review_rows:
        print(f"\nRows requiring manual review: {sorted(review_rows)}")
        print(f"Total rows to review: {len(review_rows)}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    csv_path = "/Users/all/claude_code/payer_provider_disputes/data/derived/visualizations/datawrapper_range_plot_simple.csv"
    analyze_duplicates(csv_path)
