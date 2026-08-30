#!/usr/bin/env python3
"""
Transform disputes CSV for Flourish time slider visualization.

Creates columns for each quarter (2021 Q1 through 2025 Q4) where:
- The dispute's outcome_status appears in the column when it first shows up
- Status persists across subsequent quarters
- 'Unknown' statuses are left blank
- Valid statuses: Resolved, OON-Temporary, OON-Ongoing (plus any date-based ones mapped appropriately)
"""

import pandas as pd
import os

# Read the enriched disputes
input_file = 'output/disputes_enriched.csv'
output_file = 'output/disputes_flourish_timeslider.csv'

df = pd.read_csv(input_file)

# Define the quarters in order (2021 Q1 through 2025 Q4)
quarters = []
for year in range(2021, 2026):
    for q in ['Q1', 'Q2', 'Q3', 'Q4']:
        quarters.append(f"{year} {q}")

print(f"Creating {len(quarters)} quarter columns: {quarters[0]} to {quarters[-1]}")

# Function to normalize outcome status
def normalize_status(status):
    """
    Normalize outcome status values.
    Returns None for Unknown or invalid statuses.

    Valid statuses:
    - Resolved: Agreement reached, back in-network
    - OON-Partial: Some plans (commercial) resolved, but MA or specific plans still out
    - OON-Negotiating: Active talks, deadline pending, cooling-off period
    - OON-Terminated: Contract ended, negotiations failed, no resolution in sight
    """
    if pd.isna(status) or status == '' or status == 'Unknown':
        return None

    status = str(status).strip()

    # Valid statuses to keep
    valid_statuses = ['Resolved', 'OON-Partial', 'OON-Negotiating', 'OON-Terminated']

    if status in valid_statuses:
        return status

    # Legacy status mapping
    if status == 'OON-Ongoing':
        return 'OON-Terminated'
    if status == 'OON-Temporary':
        return 'OON-Negotiating'

    # If it looks like a date (contains - and numbers), it might indicate resolution
    # Map date-based entries to 'Resolved' since they typically indicate resolution dates
    if '-' in status and any(c.isdigit() for c in status):
        return 'Resolved'

    return None

# Create quarter columns
for q in quarters:
    df[q] = ''

# Function to get quarter index
def get_quarter_index(year, quarter):
    """Convert year and quarter to index in the quarters list."""
    try:
        year = int(year)
        quarter_str = f"{year} {quarter}"
        if quarter_str in quarters:
            return quarters.index(quarter_str)
    except (ValueError, TypeError):
        pass
    return None

# Populate the quarter columns
for idx, row in df.iterrows():
    year = row['year_first_reported']
    quarter = row['quarter_first_reported']
    status = normalize_status(row['outcome_status'])

    if status is None:
        continue  # Skip unknown statuses

    start_idx = get_quarter_index(year, quarter)
    if start_idx is None:
        continue

    # Place the status in the first quarter and all subsequent quarters
    for q_idx in range(start_idx, len(quarters)):
        df.at[idx, quarters[q_idx]] = status

# Keep all original columns plus the new quarter columns
# The quarter columns are already added to df

# Save the result
df.to_csv(output_file, index=False)

print(f"\nOutput saved to: {output_file}")
print(f"Total rows: {len(df)}")

# Show sample of the quarter columns
sample_cols = ['dispute_name', 'year_first_reported', 'quarter_first_reported', 'outcome_status'] + quarters[:4] + ['...'] + quarters[-2:]
print(f"\nSample of quarter columns added:")
for q in quarters[:4]:
    print(f"  {q}: {(df[q] != '').sum()} disputes with status")
print("  ...")
for q in quarters[-2:]:
    print(f"  {q}: {(df[q] != '').sum()} disputes with status")

# Count by status
print("\nStatus distribution in final quarter (2025 Q4):")
last_q = quarters[-1]
status_counts = df[last_q].value_counts()
print(status_counts)
