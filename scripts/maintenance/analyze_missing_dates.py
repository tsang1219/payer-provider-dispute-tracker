"""
Analyze why only 87 disputes have complete timeline data
"""

import pandas as pd

# Read the data
df = pd.read_csv('/Users/all/claude_code/payer_provider_disputes/data/primary/disputes_enriched.csv')

print(f"Total disputes in dataset: {len(df)}")
print()

# Check for missing dates
print("=== Date Field Completeness ===")
print(f"first_media_date missing: {df['first_media_date'].isna().sum()} ({df['first_media_date'].isna().sum()/len(df)*100:.1f}%)")
print(f"resolution_date missing: {df['resolution_date'].isna().sum()} ({df['resolution_date'].isna().sum()/len(df)*100:.1f}%)")
print(f"Both dates present: {((~df['first_media_date'].isna()) & (~df['resolution_date'].isna())).sum()}")
print()

# Check outcome status for those without resolution dates
print("=== Outcome Status for disputes WITHOUT resolution_date ===")
missing_resolution = df[df['resolution_date'].isna()]
print(f"Total without resolution_date: {len(missing_resolution)}")
print(missing_resolution['outcome_status'].value_counts())
print()

# Check outcome status for those without first_media_date
print("=== Outcome Status for disputes WITHOUT first_media_date ===")
missing_first = df[df['first_media_date'].isna()]
print(f"Total without first_media_date: {len(missing_first)}")
if len(missing_first) > 0:
    print(missing_first['outcome_status'].value_counts())
print()

# Show some examples of disputes without resolution dates
print("=== Sample disputes WITHOUT resolution_date ===")
print(missing_resolution[['dispute_name', 'outcome_status', 'first_media_date', 'resolution_date']].head(10))
print()

# Breakdown by outcome status
print("=== All Disputes by Outcome Status ===")
print(df['outcome_status'].value_counts())
print()

# For ongoing disputes
ongoing = df[df['outcome_status'].str.contains('Ongoing', case=False, na=False)]
print(f"=== Ongoing Disputes: {len(ongoing)} ===")
print(f"With first_media_date: {(~ongoing['first_media_date'].isna()).sum()}")
print(f"With resolution_date: {(~ongoing['resolution_date'].isna()).sum()}")
print()

# What if we use the current date as resolution for ongoing?
print("=== Potential Solutions ===")
print(f"1. Current visualization: Only disputes with BOTH dates = 87 disputes")
print(f"2. Use today's date for ongoing disputes without resolution_date")
print(f"   - Would add {((~df['first_media_date'].isna()) & df['resolution_date'].isna()).sum()} more disputes")
print(f"   - Total would be {((~df['first_media_date'].isna())).sum()} disputes")
print(f"3. Exclude disputes entirely missing first_media_date = {df['first_media_date'].isna().sum()} excluded")
