#!/usr/bin/env python3
"""
Final cleanup: Remove remaining duplicates and correct misdated Northeast Georgia dispute
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

def clean_datawrapper():
    """Remove duplicates and correct dates in datawrapper_range_plot_simple.csv"""

    file_path = "/Users/all/claude_code/payer_provider_disputes/data/derived/visualizations/datawrapper_range_plot_simple.csv"

    print("=" * 80)
    print("FINAL CLEANUP: datawrapper_range_plot_simple.csv")
    print("=" * 80)

    # Backup original file
    backup_path = backup_file(file_path)

    # Read the CSV
    df = pd.read_csv(file_path)
    original_count = len(df)
    print(f"\nOriginal row count: {original_count}")

    # ACTION 1: Delete Row 38 (St. Luke's vs. BCBS MN - 122) and Row 60 (South Shore vs. Tufts - 30)
    # Using 0-based index: Row 38 = index 36, Row 60 = index 58
    rows_to_delete = [36, 58]  # 0-based indices

    print(f"\n--- ACTION 1: Deleting 2 duplicate rows ---")
    for idx in sorted(rows_to_delete, reverse=True):
        if idx < len(df):
            print(f"  Deleting Row {idx + 2}: {df.iloc[idx]['Dispute']}")

    df = df.drop(rows_to_delete).reset_index(drop=True)

    # ACTION 2: Correct Row 11 (Northeast Georgia vs. Anthem) from 2022 to 2019
    # After deletion, need to find the row again (it will have shifted)
    print(f"\n--- ACTION 2: Correcting date for Northeast Georgia vs. Anthem ---")

    # Find the 2022 Northeast Georgia entry
    ne_ga_mask = (df['Dispute'] == 'Northeast Georgia vs. Anthem - 92') & (df['First Reported'] == '2022-05-01')

    if ne_ga_mask.any():
        idx = df[ne_ga_mask].index[0]
        print(f"  Found at Row {idx + 2}: {df.iloc[idx]['Dispute']}")
        print(f"  OLD: {df.iloc[idx]['First Reported']} to {df.iloc[idx]['Resolution Date']}")

        # Correct the dates from 2022 to 2019
        df.loc[idx, 'First Reported'] = '2019-10-01'
        df.loc[idx, 'Resolution Date'] = '2020-01-01'

        print(f"  NEW: {df.loc[idx, 'First Reported']} to {df.loc[idx, 'Resolution Date']}")
    else:
        print("  ⚠️  Could not find Northeast Georgia vs. Anthem with 2022 date")

    # Save cleaned file
    df.to_csv(file_path, index=False)

    print(f"\nFinal row count: {len(df)}")
    print(f"Rows removed: {original_count - len(df)}")
    print(f"\n✅ File updated: {file_path}")

    return len(df), original_count - len(df)

def clean_disputes_enriched():
    """Remove duplicates and correct dates in disputes_enriched.csv"""

    file_path = "/Users/all/claude_code/payer_provider_disputes/data/primary/disputes_enriched.csv"

    print("\n" + "=" * 80)
    print("FINAL CLEANUP: disputes_enriched.csv")
    print("=" * 80)

    # Backup original file
    backup_path = backup_file(file_path)

    # Read the CSV
    df = pd.read_csv(file_path)
    original_count = len(df)
    print(f"\nOriginal row count: {original_count}")

    # ACTION 1: Delete Dispute IDs 102 (St. Luke's 2024) and 193 (South Shore Nov 2025)
    dispute_ids_to_delete = [102, 193]

    print(f"\n--- ACTION 1: Deleting 2 duplicate disputes ---")

    rows_to_delete = []
    for dispute_id in dispute_ids_to_delete:
        matching_rows = df[df['dispute_id'] == dispute_id]
        if len(matching_rows) > 0:
            idx = matching_rows.index[0]
            rows_to_delete.append(idx)
            row_data = df.iloc[idx]
            provider = row_data.get('provider_name', 'N/A')
            payer = row_data.get('payer_name', 'N/A')
            print(f"  Deleting Dispute ID {dispute_id}: {provider} vs {payer}")

    df = df.drop(rows_to_delete).reset_index(drop=True)

    # ACTION 2: Correct Dispute ID 18 (Northeast Georgia) from 2022 to 2019
    print(f"\n--- ACTION 2: Correcting dates for Dispute ID 18 ---")

    dispute_18_mask = df['dispute_id'] == 18

    if dispute_18_mask.any():
        idx = df[dispute_18_mask].index[0]
        row_data = df.iloc[idx]
        print(f"  Found Dispute ID 18: {row_data.get('provider_name', 'N/A')} vs {row_data.get('payer_name', 'N/A')}")
        print(f"  OLD: {df.loc[idx, 'first_media_date']} to {df.loc[idx, 'resolution_date']}")

        # Correct the dates from 2022 to 2019
        df.loc[idx, 'first_media_date'] = '2019-10-01'
        df.loc[idx, 'resolution_date'] = '2020-01-01'
        df.loc[idx, 'oon_effective_date'] = '2019-10-01'

        # Update year_label if it exists
        if 'year_label' in df.columns:
            df.loc[idx, 'year_label'] = '2019'

        print(f"  NEW: {df.loc[idx, 'first_media_date']} to {df.loc[idx, 'resolution_date']}")
    else:
        print("  ⚠️  Could not find Dispute ID 18")

    # Save cleaned file
    df.to_csv(file_path, index=False)

    print(f"\nFinal row count: {len(df)}")
    print(f"Rows removed: {original_count - len(df)}")
    print(f"\n✅ File updated: {file_path}")

    return len(df), original_count - len(df)

def main():
    """Main cleanup function"""

    print("\n" + "=" * 80)
    print("FINAL DUPLICATE CLEANUP")
    print("=" * 80)
    print("\nActions:")
    print("1. Delete Row 38 (St. Luke's vs. BCBS MN - misdated 2024 duplicate)")
    print("2. Delete Row 60 (South Shore vs. Tufts - Nov escalation duplicate)")
    print("3. Correct Row 11 (Northeast Georgia) from 2022 to 2019")
    print("\n" + "=" * 80 + "\n")

    # Clean datawrapper file
    dw_final_count, dw_removed = clean_datawrapper()

    # Clean disputes_enriched file
    de_final_count, de_removed = clean_disputes_enriched()

    # Summary
    print("\n" + "=" * 80)
    print("FINAL CLEANUP SUMMARY")
    print("=" * 80)
    print(f"\ndatawrapper_range_plot_simple.csv:")
    print(f"  - Rows removed: {dw_removed}")
    print(f"  - Final count: {dw_final_count}")
    print(f"  - Date corrections: 1 (Northeast Georgia 2022→2019)")

    print(f"\ndisputes_enriched.csv:")
    print(f"  - Rows removed: {de_removed}")
    print(f"  - Final count: {de_final_count}")
    print(f"  - Date corrections: 1 (Dispute ID 18)")

    print("\n✅ All cleanup complete! Backups created with timestamp suffix.")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
