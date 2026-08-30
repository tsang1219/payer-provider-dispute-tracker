"""
Create Datawrapper-ready CSV for Range Plot visualization
Format: Each row is a dispute with start and end dates
"""

import pandas as pd
from datetime import datetime

# Read the data
df = pd.read_csv('/Users/all/claude_code/payer_provider_disputes/data/primary/disputes_enriched.csv')

# Convert date columns to datetime
df['first_media_date'] = pd.to_datetime(df['first_media_date'], errors='coerce')
df['resolution_date'] = pd.to_datetime(df['resolution_date'], errors='coerce')

# Filter to disputes with both dates
df_plot = df.dropna(subset=['first_media_date', 'resolution_date']).copy()

# Sort by first_media_date
df_plot = df_plot.sort_values('first_media_date')

# Calculate duration in days
df_plot['duration_days'] = (df_plot['resolution_date'] - df_plot['first_media_date']).dt.days

# Create short label for better readability
df_plot['short_label'] = df_plot.apply(
    lambda x: f"{x['system_name_normalized']} vs {x['insurer_name_normalized']} ({x['year_first_reported']})",
    axis=1
)

# Format dates as YYYY-MM-DD for Datawrapper
df_plot['start_date'] = df_plot['first_media_date'].dt.strftime('%Y-%m-%d')
df_plot['end_date'] = df_plot['resolution_date'].dt.strftime('%Y-%m-%d')

# Create Datawrapper-ready format
# Option 1: Simple format with just label and dates
datawrapper_simple = df_plot[[
    'short_label',
    'start_date',
    'end_date',
    'duration_days',
    'outcome_status',
    'patients_affected'
]].copy()

datawrapper_simple.columns = [
    'Dispute',
    'First Reported',
    'Resolution Date',
    'Duration (days)',
    'Outcome Status',
    'Patients Affected'
]

# Save simple version
output_simple = '/Users/all/claude_code/payer_provider_disputes/data/derived/datawrapper_range_plot_simple.csv'
datawrapper_simple.to_csv(output_simple, index=False)
print(f"Simple Datawrapper format saved to: {output_simple}")
print(f"Rows: {len(datawrapper_simple)}")

# Option 2: More detailed version with additional context
datawrapper_detailed = df_plot[[
    'dispute_name',
    'system_name_normalized',
    'insurer_name_normalized',
    'start_date',
    'end_date',
    'duration_days',
    'outcome_status',
    'patients_affected',
    'system_hq_state',
    'dispute_type'
]].copy()

datawrapper_detailed.columns = [
    'Dispute Name',
    'Provider',
    'Insurer',
    'First Reported',
    'Resolution Date',
    'Duration (days)',
    'Outcome',
    'Patients Affected',
    'State',
    'Type'
]

output_detailed = '/Users/all/claude_code/payer_provider_disputes/data/derived/datawrapper_range_plot_detailed.csv'
datawrapper_detailed.to_csv(output_detailed, index=False)
print(f"\nDetailed Datawrapper format saved to: {output_detailed}")
print(f"Rows: {len(datawrapper_detailed)}")

# Print summary stats
print("\n=== Summary Statistics ===")
print(f"Total disputes: {len(df_plot)}")
print(f"Average duration: {df_plot['duration_days'].mean():.1f} days")
print(f"Median duration: {df_plot['duration_days'].median():.1f} days")
print(f"Min duration: {df_plot['duration_days'].min():.0f} days")
print(f"Max duration: {df_plot['duration_days'].max():.0f} days")
print(f"\nOutcome Status breakdown:")
print(df_plot['outcome_status'].value_counts())

print("\n=== Instructions for Datawrapper ===")
print("1. Go to Datawrapper.de and create a new chart")
print("2. Choose 'Range Plot' chart type")
print("3. Upload one of the CSV files above")
print("4. In the 'Check & Describe' step:")
print("   - Set 'First Reported' as the start date")
print("   - Set 'Resolution Date' as the end date")
print("   - Use 'Dispute' or 'Dispute Name' as the label")
print("5. In the 'Visualize' step:")
print("   - Enable 'Sort by' → 'First Reported' (earliest first)")
print("   - Color by 'Outcome Status' for visual distinction")
print("   - Customize tooltips to show Duration and Patients Affected")
print("6. The x-axis will automatically be formatted as dates!")
