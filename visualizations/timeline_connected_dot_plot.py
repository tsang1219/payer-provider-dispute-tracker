"""
Connected Dot Plot for Payer-Provider Dispute Timelines
Shows timeline from first_media_date to resolution_date for each dispute
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np

# Read the data
df = pd.read_csv('/Users/all/claude_code/payer_provider_disputes/data/primary/disputes_enriched.csv')

# Convert date columns to datetime
df['first_media_date'] = pd.to_datetime(df['first_media_date'], errors='coerce')
df['resolution_date'] = pd.to_datetime(df['resolution_date'], errors='coerce')

# Filter out rows where both dates are missing
df_plot = df.dropna(subset=['first_media_date', 'resolution_date']).copy()

# Sort by first_media_date for better visualization
df_plot = df_plot.sort_values('first_media_date')

# Create figure and axis
fig, ax = plt.subplots(figsize=(16, max(12, len(df_plot) * 0.4)))

# Colors for different outcome statuses
status_colors = {
    'Resolved': '#2ecc71',  # Green
    'OON-Permanent': '#e74c3c',  # Red
    'Unknown': '#95a5a6',  # Gray
    'Ongoing': '#f39c12'  # Orange
}

# Plot each dispute as a connected dot plot
for idx, row in df_plot.iterrows():
    y_pos = len(df_plot) - list(df_plot.index).index(idx) - 1

    start_date = row['first_media_date']
    end_date = row['resolution_date']

    # Determine color based on outcome status
    color = status_colors.get(row['outcome_status'], '#95a5a6')

    # Draw connecting line
    ax.plot([start_date, end_date], [y_pos, y_pos],
            color=color, linewidth=2.5, alpha=0.7, zorder=1)

    # Draw dots at start and end
    ax.scatter([start_date], [y_pos], color=color, s=100,
              marker='o', zorder=2, edgecolors='white', linewidths=1.5)
    ax.scatter([end_date], [y_pos], color=color, s=150,
              marker='D', zorder=2, edgecolors='white', linewidths=1.5)

    # Add dispute name label
    dispute_label = f"{row['dispute_name'][:50]}..." if len(str(row['dispute_name'])) > 50 else row['dispute_name']
    ax.text(start_date, y_pos, f"  {dispute_label}",
           va='center', ha='left', fontsize=8, alpha=0.8)

# Format x-axis
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.xticks(rotation=45, ha='right')

# Labels and title
ax.set_xlabel('Date', fontsize=12, fontweight='bold')
ax.set_ylabel('Disputes (sorted by first media date)', fontsize=12, fontweight='bold')
ax.set_title('Payer-Provider Dispute Timelines: From First Report to Resolution',
            fontsize=16, fontweight='bold', pad=20)

# Remove y-axis ticks (we have labels on the lines)
ax.set_yticks([])

# Add grid
ax.grid(True, axis='x', alpha=0.3, linestyle='--')
ax.set_axisbelow(True)

# Add legend for outcome statuses
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=status_colors['Resolved'], label='Resolved'),
    Patch(facecolor=status_colors['OON-Permanent'], label='OON-Permanent'),
    Patch(facecolor=status_colors.get('Ongoing', '#f39c12'), label='Ongoing'),
    Patch(facecolor=status_colors['Unknown'], label='Unknown')
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

# Add subtitle with statistics
total_disputes = len(df_plot)
avg_duration = (df_plot['resolution_date'] - df_plot['first_media_date']).dt.days.mean()
fig.text(0.5, 0.98, f'Total Disputes: {total_disputes} | Average Duration: {avg_duration:.0f} days',
        ha='center', fontsize=11, style='italic', alpha=0.7)

plt.tight_layout()

# Save the figure
output_path = '/Users/all/claude_code/payer_provider_disputes/visualizations/timeline_connected_dot_plot.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"Visualization saved to: {output_path}")

# Also create an interactive HTML version using plotly
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # Create plotly figure
    fig_plotly = go.Figure()

    for idx, row in df_plot.iterrows():
        y_pos = len(df_plot) - list(df_plot.index).index(idx) - 1

        start_date = row['first_media_date']
        end_date = row['resolution_date']
        color = status_colors.get(row['outcome_status'], '#95a5a6')

        # Add line
        fig_plotly.add_trace(go.Scatter(
            x=[start_date, end_date],
            y=[y_pos, y_pos],
            mode='lines',
            line=dict(color=color, width=3),
            hoverinfo='skip',
            showlegend=False
        ))

        # Add start marker
        fig_plotly.add_trace(go.Scatter(
            x=[start_date],
            y=[y_pos],
            mode='markers',
            marker=dict(size=10, color=color, symbol='circle', line=dict(width=2, color='white')),
            name=row['outcome_status'],
            hovertext=f"<b>{row['dispute_name']}</b><br>" +
                     f"First Report: {start_date.strftime('%Y-%m-%d')}<br>" +
                     f"Resolution: {end_date.strftime('%Y-%m-%d')}<br>" +
                     f"Duration: {(end_date - start_date).days} days<br>" +
                     f"Status: {row['outcome_status']}<br>" +
                     f"Patients: {row['patients_affected']:,.0f}" if pd.notna(row['patients_affected']) else '',
            hoverinfo='text',
            showlegend=False
        ))

        # Add end marker
        fig_plotly.add_trace(go.Scatter(
            x=[end_date],
            y=[y_pos],
            mode='markers',
            marker=dict(size=12, color=color, symbol='diamond', line=dict(width=2, color='white')),
            hovertext=f"<b>{row['dispute_name']}</b><br>" +
                     f"First Report: {start_date.strftime('%Y-%m-%d')}<br>" +
                     f"Resolution: {end_date.strftime('%Y-%m-%d')}<br>" +
                     f"Duration: {(end_date - start_date).days} days<br>" +
                     f"Status: {row['outcome_status']}<br>" +
                     f"Patients: {row['patients_affected']:,.0f}" if pd.notna(row['patients_affected']) else '',
            hoverinfo='text',
            showlegend=False
        ))

    fig_plotly.update_layout(
        title=dict(
            text='Payer-Provider Dispute Timelines: From First Report to Resolution<br>' +
                 f'<sub>Total Disputes: {total_disputes} | Average Duration: {avg_duration:.0f} days</sub>',
            x=0.5,
            xanchor='center'
        ),
        xaxis_title='Date',
        yaxis_title='Disputes (sorted by first media date)',
        height=max(800, len(df_plot) * 25),
        hovermode='closest',
        showlegend=False,
        plot_bgcolor='white',
        yaxis=dict(showticklabels=False, showgrid=False),
        xaxis=dict(showgrid=True, gridcolor='lightgray', gridwidth=0.5)
    )

    output_html = '/Users/all/claude_code/payer_provider_disputes/visualizations/timeline_connected_dot_plot.html'
    fig_plotly.write_html(output_html)
    print(f"Interactive visualization saved to: {output_html}")

except ImportError:
    print("Plotly not installed. Skipping interactive HTML version.")
    print("Install with: pip install plotly")

plt.show()
