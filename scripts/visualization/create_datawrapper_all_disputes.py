"""
Create Datawrapper-ready CSV including ongoing disputes
Uses today's date as the end point for unresolved disputes
"""

import pandas as pd
from datetime import datetime

# Read the data
df = pd.read_csv('/Users/all/claude_code/payer_provider_disputes/data/primary/disputes_enriched.csv')

# Convert date columns to datetime
df['first_media_date'] = pd.to_datetime(df['first_media_date'], errors='coerce')
df['resolution_date'] = pd.to_datetime(df['resolution_date'], errors='coerce')

# For disputes without resolution_date, use today's date
today = pd.Timestamp.now().normalize()
df['end_date_display'] = df['resolution_date'].fillna(today)

# Create a flag for ongoing vs resolved
df['status_category'] = df.apply(
    lambda x: 'Ongoing' if pd.isna(x['resolution_date']) and x['outcome_status'] in ['OON-Ongoing', 'OON-Permanent'] else 'Resolved',
    axis=1
)

# Sort by first_media_date
df = df.sort_values('first_media_date')

# Calculate duration in days
df['duration_days'] = (df['end_date_display'] - df['first_media_date']).dt.days

# Create short label
df['short_label'] = df.apply(
    lambda x: f"{x['system_name_normalized']} vs {x['insurer_name_normalized']} ({x['year_first_reported']})",
    axis=1
)

# Format dates as YYYY-MM-DD for Datawrapper
df['start_date'] = df['first_media_date'].dt.strftime('%Y-%m-%d')
df['end_date_formatted'] = df['end_date_display'].dt.strftime('%Y-%m-%d')

# Create indicator for ongoing
df['is_ongoing'] = df['resolution_date'].isna()
df['status_detail'] = df.apply(
    lambda x: f"{x['outcome_status']}" + (" (ongoing - as of today)" if x['is_ongoing'] else ""),
    axis=1
)

# Create Datawrapper format - ALL disputes
datawrapper_all = df[[
    'short_label',
    'start_date',
    'end_date_formatted',
    'duration_days',
    'outcome_status',
    'status_detail',
    'patients_affected',
    'is_ongoing'
]].copy()

datawrapper_all.columns = [
    'Dispute',
    'First Reported',
    'End Date',
    'Duration (days)',
    'Outcome Status',
    'Status Detail',
    'Patients Affected',
    'Ongoing'
]

# Save
output_all = '/Users/all/claude_code/payer_provider_disputes/data/derived/datawrapper_range_plot_all_disputes.csv'
datawrapper_all.to_csv(output_all, index=False)
print(f"All disputes Datawrapper format saved to: {output_all}")
print(f"Total rows: {len(datawrapper_all)}")

# Print summary stats
print("\n=== Summary Statistics ===")
print(f"Total disputes: {len(df)}")
print(f"Resolved (with actual resolution date): {(~df['resolution_date'].isna()).sum()}")
print(f"Ongoing/Permanent (using today's date): {df['resolution_date'].isna().sum()}")
print(f"\nAverage duration (resolved only): {df[~df['resolution_date'].isna()]['duration_days'].mean():.1f} days")
print(f"Average duration (all, with ongoing as of today): {df['duration_days'].mean():.1f} days")
print(f"\nMedian duration (resolved only): {df[~df['resolution_date'].isna()]['duration_days'].median():.1f} days")

print(f"\nOutcome Status breakdown:")
print(df['outcome_status'].value_counts())

print("\n=== Datawrapper Instructions ===")
print("1. Upload the CSV to Datawrapper")
print("2. Choose 'Range Plot' chart type")
print("3. Map columns:")
print("   - Start: 'First Reported'")
print("   - End: 'End Date'")
print("   - Label: 'Dispute'")
print("4. In Visualize:")
print("   - Color by 'Outcome Status' to distinguish resolved vs ongoing")
print("   - Consider using 'Ongoing' column to style ongoing disputes differently")
print("   - Add note: 'Ongoing disputes shown through current date'")
print("   - Tooltips: Show 'Status Detail', 'Duration (days)', 'Patients Affected'")

# Also create a version with just the key ongoing disputes (top by patients affected)
df_ongoing = df[df['is_ongoing']].copy()
df_ongoing_sorted = df_ongoing.sort_values('patients_affected', ascending=False)

print(f"\n=== Top 10 Ongoing Disputes by Patients Affected ===")
print(df_ongoing_sorted[['dispute_name', 'patients_affected', 'duration_days', 'outcome_status']].head(10))
