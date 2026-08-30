"""
Create Datawrapper-ready CSV with rich HTML tooltips
Includes dispute details, system info, outcome, patients, and key notes
"""

import pandas as pd
from datetime import datetime
import html

# Read the data
df = pd.read_csv('/Users/all/claude_code/payer_provider_disputes/data/primary/disputes_enriched.csv')

# Convert date columns to datetime
df['first_media_date'] = pd.to_datetime(df['first_media_date'], errors='coerce')
df['resolution_date'] = pd.to_datetime(df['resolution_date'], errors='coerce')

# For disputes without resolution_date, use today's date
today = pd.Timestamp.now().normalize()
df['end_date_display'] = df['resolution_date'].fillna(today)

# Sort by first_media_date
df = df.sort_values('first_media_date')

# Calculate duration
df['duration_days'] = (df['end_date_display'] - df['first_media_date']).dt.days
df['duration_months'] = (df['duration_days'] / 30).round(1)

# Create status detail
df['is_ongoing'] = df['resolution_date'].isna()
df['status_display'] = df.apply(
    lambda x: f"{x['outcome_status']}" + (" (ongoing)" if x['is_ongoing'] else ""),
    axis=1
)

# Format dates
df['start_date'] = df['first_media_date'].dt.strftime('%Y-%m-%d')
df['end_date_formatted'] = df['end_date_display'].dt.strftime('%Y-%m-%d')
df['start_date_readable'] = df['first_media_date'].dt.strftime('%b %d, %Y')
df['end_date_readable'] = df['end_date_display'].dt.strftime('%b %d, %Y')

# Create short label for the chart
df['short_label'] = df.apply(
    lambda x: f"{x['system_name_normalized']} vs {x['insurer_name_normalized']} ({x['year_first_reported']})",
    axis=1
)

# Function to create rich HTML tooltip
def create_tooltip(row):
    """Create rich HTML formatted tooltip"""

    # Start with dispute name as header
    tooltip = f"<strong style='font-size: 14px;'>{html.escape(str(row['dispute_name']))}</strong><br>"
    tooltip += "<br>"

    # System and Insurer info
    tooltip += f"<strong>Provider:</strong> {html.escape(str(row['system_name']))}<br>"

    # Add HQ location
    hq_location = f"{row['system_hq_city']}, {row['system_hq_state']}" if pd.notna(row['system_hq_city']) else row['system_hq_state']
    if pd.notna(hq_location):
        tooltip += f"<strong>Headquarters:</strong> {html.escape(str(hq_location))}<br>"

    tooltip += f"<strong>Insurer:</strong> {html.escape(str(row['insurer_name']))}<br>"
    tooltip += "<br>"

    # Timeline
    tooltip += "<strong style='color: #2c5aa0;'>Timeline</strong><br>"
    tooltip += f"<strong>First Reported:</strong> {row['start_date_readable']}<br>"

    if row['is_ongoing']:
        tooltip += f"<strong>Status:</strong> {html.escape(str(row['outcome_status']))} (ongoing)<br>"
        tooltip += f"<strong>Duration:</strong> {int(row['duration_days'])} days (~{row['duration_months']:.1f} months) <em>and counting</em><br>"
    else:
        tooltip += f"<strong>Resolved:</strong> {row['end_date_readable']}<br>"
        tooltip += f"<strong>Duration:</strong> {int(row['duration_days'])} days (~{row['duration_months']:.1f} months)<br>"
        tooltip += f"<strong>Outcome:</strong> {html.escape(str(row['outcome_status']))}<br>"

    tooltip += "<br>"

    # Patients affected
    if pd.notna(row['patients_affected']) and row['patients_affected'] > 0:
        tooltip += f"<strong style='color: #c44e52;'>Patients Affected:</strong> {int(row['patients_affected']):,}<br>"

    # Dispute type
    if pd.notna(row['dispute_type']) and str(row['dispute_type']) != 'Unknown':
        tooltip += f"<strong>Dispute Type:</strong> {html.escape(str(row['dispute_type']))}<br>"

    # Insurer type
    if pd.notna(row['insurer_type']):
        tooltip += f"<strong>Coverage Type:</strong> {html.escape(str(row['insurer_type']))}<br>"

    # Key issues or resolution terms (if not too long)
    if pd.notna(row['resolution_terms_summary']) and len(str(row['resolution_terms_summary'])) < 150:
        tooltip += "<br>"
        tooltip += f"<em>{html.escape(str(row['resolution_terms_summary']))}</em><br>"
    elif pd.notna(row['key_issues']) and len(str(row['key_issues'])) < 150:
        tooltip += "<br>"
        tooltip += f"<em>{html.escape(str(row['key_issues']))}</em><br>"

    # Add brief note if available and concise
    if pd.notna(row['notes']) and len(str(row['notes'])) < 200 and len(str(row['notes'])) > 10:
        # Clean up note - remove redundant date info
        note = str(row['notes'])
        if 'Patient estimation' not in note and 'first_media_date corrected' not in note:
            tooltip += "<br>"
            tooltip += f"<em style='color: #666;'>{html.escape(note[:200])}</em><br>"

    return tooltip

# Apply tooltip creation
df['tooltip'] = df.apply(create_tooltip, axis=1)

# Create final Datawrapper export with tooltip
datawrapper_export = df[[
    'short_label',
    'start_date',
    'end_date_formatted',
    'duration_days',
    'outcome_status',
    'patients_affected',
    'is_ongoing',
    'tooltip'
]].copy()

datawrapper_export.columns = [
    'Dispute',
    'First Reported',
    'End Date',
    'Duration (days)',
    'Outcome Status',
    'Patients Affected',
    'Ongoing',
    'Tooltip'
]

# Save
output_file = '/Users/all/claude_code/payer_provider_disputes/data/derived/datawrapper_range_plot_with_tooltips.csv'
datawrapper_export.to_csv(output_file, index=False)
print(f"Datawrapper file with tooltips saved to: {output_file}")
print(f"Total disputes: {len(datawrapper_export)}")

print("\n=== Sample Tooltip (first dispute) ===")
print(datawrapper_export['Tooltip'].iloc[0])

print("\n=== Datawrapper Setup Instructions ===")
print("1. Upload the CSV to Datawrapper")
print("2. Choose 'Range Plot' chart type")
print("3. In 'Check & Describe' tab:")
print("   - Set 'First Reported' as start date")
print("   - Set 'End Date' as end date")
print("   - Set 'Dispute' as label")
print("4. In 'Visualize' tab:")
print("   - REFINE tab → Customize tooltip:")
print("     * Select 'Custom template'")
print("     * In the tooltip editor, use: {{ Tooltip }}")
print("     * This will render the HTML-formatted tooltip")
print("   - Color by 'Outcome Status'")
print("   - Sort by 'First Reported' (ascending)")
print("5. Add annotation:")
print("   'Ongoing disputes shown through current date (January 2026)'")

print("\n=== Alternative: Simple Tooltip (if HTML doesn't work) ===")
print("If Datawrapper strips HTML, use these individual fields in custom tooltip:")
print("{{ Dispute }}")
print("Provider: {{ Provider }}")
print("Duration: {{ Duration (days) }} days")
print("Patients: {{ Patients Affected }}")

# Also create a version with separate tooltip fields (non-HTML fallback)
df_fallback = df.copy()

# Create clean text versions
df_fallback['tooltip_title'] = df_fallback['dispute_name']
df_fallback['tooltip_provider'] = df_fallback['system_name']
df_fallback['tooltip_hq'] = df_fallback.apply(
    lambda x: f"{x['system_hq_city']}, {x['system_hq_state']}" if pd.notna(x['system_hq_city']) else x['system_hq_state'],
    axis=1
)
df_fallback['tooltip_insurer'] = df_fallback['insurer_name']
df_fallback['tooltip_timeline'] = df_fallback.apply(
    lambda x: f"{x['start_date_readable']} → {x['end_date_readable']}" + (" (ongoing)" if x['is_ongoing'] else ""),
    axis=1
)
df_fallback['tooltip_patients'] = df_fallback['patients_affected'].apply(
    lambda x: f"{int(x):,}" if pd.notna(x) and x > 0 else "Unknown"
)
df_fallback['tooltip_status'] = df_fallback['status_display']

fallback_export = df_fallback[[
    'short_label',
    'start_date',
    'end_date_formatted',
    'tooltip_title',
    'tooltip_provider',
    'tooltip_hq',
    'tooltip_insurer',
    'tooltip_timeline',
    'tooltip_patients',
    'tooltip_status',
    'outcome_status'
]].copy()

fallback_export.columns = [
    'Dispute',
    'First Reported',
    'End Date',
    'Dispute Name',
    'Provider',
    'Headquarters',
    'Insurer',
    'Timeline',
    'Patients Affected',
    'Status',
    'Outcome Status'
]

output_fallback = '/Users/all/claude_code/payer_provider_disputes/data/derived/datawrapper_range_plot_separate_fields.csv'
fallback_export.to_csv(output_fallback, index=False)
print(f"\nFallback version with separate fields saved to: {output_fallback}")
print("Use this if HTML tooltips don't render properly in Datawrapper")
