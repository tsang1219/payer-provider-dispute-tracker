#!/usr/bin/env python3
"""
Clean duplicate rows from datawrapper_range_plot_simple.csv and disputes_enriched.csv
Based on verification analysis from general-purpose agents.
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

def clean_datawrapper_simple():
    """Clean duplicates from datawrapper_range_plot_simple.csv"""

    file_path = "/Users/all/claude_code/payer_provider_disputes/data/derived/visualizations/datawrapper_range_plot_simple.csv"

    print("=" * 80)
    print("CLEANING: datawrapper_range_plot_simple.csv")
    print("=" * 80)

    # Backup original file
    backup_path = backup_file(file_path)

    # Read the CSV
    df = pd.read_csv(file_path)
    original_count = len(df)
    print(f"\nOriginal row count: {original_count}")

    # Rows to delete (using 0-based index, so subtract 2 from the row numbers shown to user)
    # Row numbers from analysis: 51, 7, 61, 35, 25, 10
    # Converting to 0-based index: 49, 5, 59, 33, 23, 8
    rows_to_delete = [49, 5, 59, 33, 23, 8]  # 0-based indices

    print(f"\nDeleting {len(rows_to_delete)} duplicate rows:")
    for idx in sorted(rows_to_delete, reverse=True):
        if idx < len(df):
            print(f"  Row {idx + 2}: {df.iloc[idx]['Dispute']}")

    # Delete the rows
    df_cleaned = df.drop(rows_to_delete)
    df_cleaned = df_cleaned.reset_index(drop=True)

    # Save cleaned file
    df_cleaned.to_csv(file_path, index=False)

    print(f"\nCleaned row count: {len(df_cleaned)}")
    print(f"Rows removed: {original_count - len(df_cleaned)}")
    print(f"\n✅ File updated: {file_path}")

    return len(df_cleaned), original_count - len(df_cleaned)

def clean_disputes_enriched():
    """Clean duplicates from disputes_enriched.csv"""

    file_path = "/Users/all/claude_code/payer_provider_disputes/data/primary/disputes_enriched.csv"

    print("\n" + "=" * 80)
    print("CLEANING: disputes_enriched.csv")
    print("=" * 80)

    # Backup original file
    backup_path = backup_file(file_path)

    # Read the CSV
    df = pd.read_csv(file_path)
    original_count = len(df)
    print(f"\nOriginal row count: {original_count}")

    # Dispute IDs to delete based on agent analysis:
    # - 204 (Phoenix Children's duplicate - Nov 1 start)
    # - 4 (Wellstar - 36,000 patients)
    # - 117 (Memorial Sloan Kettering duplicate)
    # - 63 (Memorial Sloan Kettering 2024 misdated)
    # - 99 (Bon Secours duplicate)
    # - 9 (Northside - 150 days)
    dispute_ids_to_delete = [204, 4, 117, 63, 99, 9]

    print(f"\nDeleting {len(dispute_ids_to_delete)} disputes by ID:")

    rows_to_delete = []
    for dispute_id in dispute_ids_to_delete:
        matching_rows = df[df['dispute_id'] == dispute_id]
        if len(matching_rows) > 0:
            idx = matching_rows.index[0]
            rows_to_delete.append(idx)
            row_data = df.iloc[idx]
            print(f"  Dispute ID {dispute_id}: {row_data.get('provider_name', 'N/A')} vs {row_data.get('payer_name', 'N/A')}")

    # Delete the rows
    df_cleaned = df.drop(rows_to_delete)
    df_cleaned = df_cleaned.reset_index(drop=True)

    # Save cleaned file
    df_cleaned.to_csv(file_path, index=False)

    print(f"\nCleaned row count: {len(df_cleaned)}")
    print(f"Rows removed: {original_count - len(df_cleaned)}")
    print(f"\n✅ File updated: {file_path}")

    return len(df_cleaned), original_count - len(df_cleaned)

def main():
    """Main cleanup function"""

    print("\n" + "=" * 80)
    print("DUPLICATE CLEANUP SCRIPT")
    print("=" * 80)
    print("\nThis script will:")
    print("1. Create backups of both files")
    print("2. Remove verified duplicate rows")
    print("3. Save the cleaned versions")
    print("\n" + "=" * 80 + "\n")

    # Clean datawrapper file
    dw_final_count, dw_removed = clean_datawrapper_simple()

    # Clean disputes_enriched file
    de_final_count, de_removed = clean_disputes_enriched()

    # Summary
    print("\n" + "=" * 80)
    print("CLEANUP SUMMARY")
    print("=" * 80)
    print(f"\ndatawrapper_range_plot_simple.csv:")
    print(f"  - Rows removed: {dw_removed}")
    print(f"  - Final count: {dw_final_count}")

    print(f"\ndisputes_enriched.csv:")
    print(f"  - Rows removed: {de_removed}")
    print(f"  - Final count: {de_final_count}")

    print("\n✅ Cleanup complete! Backups created with timestamp suffix.")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
