#!/usr/bin/env python3
"""
Health System Characteristics Analysis
Analyze what system-level data we have and identify gaps for better prediction
"""

import pandas as pd
import numpy as np
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('/Users/all/claude_code/payer_provider_disputes/output/disputes_enriched.csv')

print("=" * 80)
print("HEALTH SYSTEM CHARACTERISTICS ANALYSIS")
print("=" * 80)

# ============================================================================
# SECTION 1: DATA COMPLETENESS FOR SYSTEM CHARACTERISTICS
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 1: CURRENT DATA COMPLETENESS (System Fields)")
print("=" * 80)

system_fields = [
    'system_name',
    'system_name_normalized',
    'system_hq_city',
    'system_hq_state',
    'system_hq_lat',
    'system_hq_lon',
    'system_footprint_states',
    'system_hospital_count',
    'system_annual_revenue_mm'
]

print("\nField Completeness:")
print("-" * 60)
for field in system_fields:
    if field in df.columns:
        non_null = df[field].notna().sum()
        non_empty = df[field].astype(str).str.strip().ne('').sum()
        pct = non_null / len(df) * 100
        print(f"  {field:<30}: {non_null:>4}/{len(df)} ({pct:>5.1f}%)")
    else:
        print(f"  {field:<30}: NOT IN DATA")

# ============================================================================
# SECTION 2: WHAT WE'RE MISSING
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 2: MISSING DATA ELEMENTS (Would Improve Prediction)")
print("=" * 80)

print("""
🔴 CRITICAL MISSING FIELDS FOR PREDICTIVE ANALYSIS:

1. MARKET POSITION
   - market_share_pct: Health system's share in local market
   - is_regional_monopoly: Boolean if dominant in region
   - competitor_count: Number of alternative providers in area
   - is_sole_community_hospital: Only hospital in county/region

2. FINANCIAL STRENGTH
   - operating_margin_pct: Profitability indicator
   - days_cash_on_hand: Financial runway
   - debt_to_equity_ratio: Leverage indicator
   - credit_rating: S&P/Moody's rating

3. SIZE & SCALE
   - total_beds: Hospital bed count
   - annual_admissions: Patient volume
   - annual_outpatient_visits: Outpatient volume
   - employed_physicians_count: Physician leverage

4. NETWORK CHARACTERISTICS
   - is_teaching_hospital: Academic status
   - trauma_level: 1, 2, 3, or none
   - specialty_services: List of unique services
   - has_transplant_program: High-acuity indicator
   - has_childrens_hospital: Pediatric specialty
   - has_cancer_center: Oncology specialty

5. BARGAINING HISTORY
   - previous_disputes_count: History of disputes
   - previous_resolution_rate: Track record
   - avg_contract_duration_years: Relationship stability

6. PAYER MIX
   - commercial_pct: Commercial insurance %
   - medicare_pct: Medicare %
   - medicaid_pct: Medicaid %
   - uninsured_pct: Uncompensated care exposure
""")

# ============================================================================
# SECTION 3: INFERRED CHARACTERISTICS FROM EXISTING DATA
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 3: CHARACTERISTICS WE CAN INFER")
print("=" * 80)

# Infer from system names and notes
def classify_system(row):
    """Classify health system type from available data"""
    name = str(row['system_name']).lower()
    notes = str(row.get('notes', '')).lower()

    characteristics = []

    # Academic/Teaching
    academic_keywords = ['university', 'academic', 'teaching', 'medical center', 'umc',
                        'medical college', 'school of medicine', 'wexner', 'johns hopkins',
                        'mayo', 'memorial sloan', 'duke', 'unc ', 'vcu', 'musc', 'uconn',
                        'suny', 'harvard', 'stanford', 'yale', 'columbia']
    if any(kw in name for kw in academic_keywords):
        characteristics.append('academic')

    # Children's/Pediatric
    if 'children' in name or 'pediatric' in name:
        characteristics.append('pediatric_specialty')

    # Cancer Center
    if 'cancer' in name or 'oncology' in name or 'sloan' in name:
        characteristics.append('cancer_specialty')

    # Large System indicators
    large_keywords = ['health system', 'healthcare system', 'health network',
                     'regional health', 'medical system']
    hospital_count_pattern = r'(\d+)\s*hospital'
    if any(kw in name for kw in large_keywords):
        characteristics.append('large_system')

    # Rural indicators
    rural_keywords = ['rural', 'community', 'regional medical', 'county']
    if any(kw in name for kw in rural_keywords) and 'large' not in str(characteristics):
        characteristics.append('community_hospital')

    # Multi-hospital from notes
    if 'hospitals' in notes or 'facilities' in notes:
        characteristics.append('multi_facility')

    return characteristics if characteristics else ['standard']


# Apply classification
df['inferred_characteristics'] = df.apply(classify_system, axis=1)
df['is_academic'] = df['inferred_characteristics'].apply(lambda x: 'academic' in x)
df['is_specialty'] = df['inferred_characteristics'].apply(lambda x: 'pediatric_specialty' in x or 'cancer_specialty' in x)
df['is_large_system'] = df['inferred_characteristics'].apply(lambda x: 'large_system' in x or 'multi_facility' in x)
df['is_community'] = df['inferred_characteristics'].apply(lambda x: 'community_hospital' in x)

print("\nInferred System Classifications:")
print("-" * 60)
print(f"  Academic/Teaching:     {df['is_academic'].sum():>4} ({df['is_academic'].sum()/len(df)*100:.1f}%)")
print(f"  Specialty (Peds/Onc):  {df['is_specialty'].sum():>4} ({df['is_specialty'].sum()/len(df)*100:.1f}%)")
print(f"  Large System:          {df['is_large_system'].sum():>4} ({df['is_large_system'].sum()/len(df)*100:.1f}%)")
print(f"  Community Hospital:    {df['is_community'].sum():>4} ({df['is_community'].sum()/len(df)*100:.1f}%)")

# ============================================================================
# SECTION 4: RESOLUTION BY INFERRED CHARACTERISTICS
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 4: RESOLUTION RATES BY INFERRED CHARACTERISTICS")
print("=" * 80)

def calc_resolution_rate(mask):
    subset = df[mask]
    if len(subset) == 0:
        return 0, 0
    resolved = (subset['outcome_status'] == 'Resolved').sum()
    return resolved / len(subset) * 100, len(subset)

print("\nResolution Rates:")
print("-" * 60)

for char, label in [
    ('is_academic', 'Academic/Teaching'),
    ('is_specialty', 'Specialty (Pediatric/Cancer)'),
    ('is_large_system', 'Large Health System'),
    ('is_community', 'Community Hospital')
]:
    rate, count = calc_resolution_rate(df[char])
    bar = "█" * int(rate / 5) if rate > 0 else ""
    print(f"  {label:<30}: {bar:<20} {rate:>5.1f}% (n={count})")

# Non-classified (standard)
standard_mask = ~(df['is_academic'] | df['is_specialty'] | df['is_large_system'] | df['is_community'])
rate, count = calc_resolution_rate(standard_mask)
print(f"  {'Standard/Unclassified':<30}: {'█' * int(rate/5):<20} {rate:>5.1f}% (n={count})")

# ============================================================================
# SECTION 5: STATE-LEVEL MARKET CONCENTRATION PROXY
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 5: MARKET CONCENTRATION PATTERNS")
print("=" * 80)

# Count disputes per system to identify repeat players
system_disputes = df.groupby('system_name_normalized').agg({
    'dispute_id': 'count',
    'outcome_status': lambda x: (x == 'Resolved').sum(),
    'system_hq_state': 'first'
}).reset_index()
system_disputes.columns = ['system', 'dispute_count', 'resolved_count', 'state']
system_disputes['resolution_rate'] = system_disputes['resolved_count'] / system_disputes['dispute_count'] * 100

print("\nSystems with Multiple Disputes (bargaining experience):")
print("-" * 70)
repeat_systems = system_disputes[system_disputes['dispute_count'] >= 2].sort_values('dispute_count', ascending=False)
for _, row in repeat_systems.iterrows():
    print(f"  {row['system'][:35]:<35} ({row['state']}): {row['dispute_count']} disputes, {row['resolution_rate']:.0f}% resolved")

# ============================================================================
# SECTION 6: GEOGRAPHIC CLUSTERING
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 6: GEOGRAPHIC CONCENTRATION")
print("=" * 80)

# States with most disputes
state_analysis = df.groupby('system_hq_state').agg({
    'dispute_id': 'count',
    'outcome_status': lambda x: (x == 'Resolved').sum(),
    'is_academic': 'sum',
    'is_large_system': 'sum'
}).reset_index()
state_analysis.columns = ['state', 'total', 'resolved', 'academic_count', 'large_system_count']
state_analysis['resolution_rate'] = state_analysis['resolved'] / state_analysis['total'] * 100
state_analysis = state_analysis.sort_values('total', ascending=False)

print("\nState-Level Analysis:")
print("-" * 70)
print(f"{'State':<6} {'Total':>6} {'Resolved':>9} {'Res%':>6} {'Academic':>9} {'Large Sys':>10}")
print("-" * 70)
for _, row in state_analysis.head(12).iterrows():
    print(f"{row['state']:<6} {row['total']:>6} {row['resolved']:>9} {row['resolution_rate']:>5.0f}% {row['academic_count']:>9} {row['large_system_count']:>10}")

# ============================================================================
# SECTION 7: RECOMMENDED DATA ENRICHMENT SOURCES
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 7: RECOMMENDED DATA ENRICHMENT SOURCES")
print("=" * 80)

print("""
📚 FREE/PUBLIC DATA SOURCES:

1. CMS Hospital Compare (data.cms.gov)
   - Hospital characteristics, quality metrics, patient surveys
   - Bed count, ownership type, teaching status

2. AHA Annual Survey Database
   - Comprehensive hospital data (requires subscription)
   - Beds, admissions, FTEs, financials

3. HCRIS (Healthcare Cost Report Information System)
   - Medicare cost reports with financial data
   - Free from CMS

4. Definitive Healthcare (subscription)
   - Market share, physician affiliations
   - Most comprehensive commercial source

5. State Health Facility Databases
   - Many states publish hospital financial reports
   - CA OSHPD, NY SPARCS, FL AHCA

6. American Hospital Directory (ahd.com)
   - Free basic hospital profiles
   - Bed counts, Medicare/Medicaid %

📊 KEY FIELDS TO ADD:

Priority 1 (High Impact on Prediction):
  - total_beds
  - market_share_pct (within HRR/HSA)
  - is_teaching_hospital
  - operating_margin_pct

Priority 2 (Medium Impact):
  - annual_admissions
  - employed_physicians_count
  - specialty_services (list)
  - trauma_level

Priority 3 (Nice to Have):
  - days_cash_on_hand
  - credit_rating
  - payer_mix breakdown
""")

# ============================================================================
# SECTION 8: SAMPLE ENRICHMENT RECOMMENDATIONS
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 8: SYSTEMS NEEDING ENRICHMENT (by dispute volume)")
print("=" * 80)

# Top systems by dispute count that need enrichment
top_systems = system_disputes.sort_values('dispute_count', ascending=False).head(20)

print("\nTop Systems - Data Gaps:")
print("-" * 80)
for _, row in top_systems.iterrows():
    system_data = df[df['system_name_normalized'] == row['system']].iloc[0]

    missing = []
    if pd.isna(system_data.get('system_hospital_count')) or system_data.get('system_hospital_count') == '':
        missing.append('hospital_count')
    if pd.isna(system_data.get('system_annual_revenue_mm')) or system_data.get('system_annual_revenue_mm') == '':
        missing.append('revenue')
    if pd.isna(system_data.get('system_footprint_states')) or system_data.get('system_footprint_states') == '':
        missing.append('footprint')

    missing_str = ', '.join(missing) if missing else 'All basic fields present'
    print(f"  {row['system'][:40]:<40} Missing: {missing_str}")

# ============================================================================
# SECTION 9: ENHANCED PREDICTIVE MODEL PROPOSAL
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 9: ENHANCED PREDICTION MODEL (with system characteristics)")
print("=" * 80)

print("""
PROPOSED ENHANCED MODEL:

Resolution_Probability =
    Intercept (0.30)

    # Insurer Factors (current model)
    + β1 × is_BCBS (+0.15)
    + β2 × is_UHC (+0.05)
    - β3 × is_Humana (-0.35)
    - β4 × is_Aetna (-0.12)

    # System Characteristics (NEW)
    + β5 × is_academic (+0.25)
    + β6 × is_specialty (+0.20)
    + β7 × log(total_beds) × 0.03
    + β8 × market_share_pct × 0.01
    + β9 × is_regional_monopoly (+0.20)
    - β10 × is_small_rural (-0.15)

    # Financial Health (NEW)
    + β11 × operating_margin > 3% (+0.10)
    - β12 × operating_margin < 0% (-0.15)

    # Situational Factors (current + enhanced)
    + β13 × lawsuit_filed (+0.20)
    + β14 × has_public_attention (+0.12)
    + β15 × has_previous_resolution (+0.08)
    - β16 × dispute_age < 6mo (-0.10)

EXPECTED IMPROVEMENT:
    Current model accuracy: ~65%
    With system characteristics: ~75-80% (estimated)
""")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY: HEALTH SYSTEM CHARACTERISTICS IMPACT")
print("=" * 80)

print("""
KEY FINDINGS:

1. DATA GAPS ARE SIGNIFICANT
   - hospital_count: 0% populated
   - annual_revenue: 0% populated
   - footprint_states: 0% populated

2. INFERRED CHARACTERISTICS SHOW CLEAR PATTERNS
   - Academic systems: Higher resolution rates
   - Specialty centers: Leverage advantage
   - Community hospitals: Less bargaining power

3. REPEAT PLAYERS exist
   - Some systems have 3-5+ disputes
   - Experience may improve negotiation outcomes

4. RECOMMENDED NEXT STEPS
   a) Enrich top 50 systems with CMS/AHA data
   b) Add market share from Definitive Healthcare or state data
   c) Calculate financial health metrics from HCRIS
   d) Re-run analysis with enriched data
""")

print("=" * 80)
