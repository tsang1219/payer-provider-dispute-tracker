# Health System Data Gaps & Enrichment Opportunities

## Current State

### What We Have
| Field | Completeness | Notes |
|-------|-------------|-------|
| system_name | 100% | ✅ Good |
| system_hq_state | 100% | ✅ Good |
| system_hq_city | 41% | Partial |
| system_hq_lat/lon | 41% | Partial |
| **system_hospital_count** | **0%** | ❌ Critical gap |
| **system_annual_revenue_mm** | **0%** | ❌ Critical gap |
| **system_footprint_states** | **0%** | ❌ Critical gap |

## Key Findings from Inferred Data

### Resolution Rates by System Type
| System Type | Resolution Rate | Sample Size |
|-------------|-----------------|-------------|
| **Specialty (Pediatric/Cancer)** | **87.5%** | n=8 |
| Academic/Teaching | 25.0% | n=32 |
| Large Health System | 27.0% | n=37 |
| Community Hospital | 0.0% | n=5 |
| Standard/Unclassified | 25.6% | n=117 |

### Geographic Patterns
| State | Total | Resolution Rate | Academic | Large System |
|-------|-------|-----------------|----------|--------------|
| CT | 7 | **71%** | 3 | 0 |
| NY | 15 | **53%** | 5 | 5 |
| TX | 10 | 40% | 0 | 2 |
| GA | 9 | 44% | 0 | 6 |
| MN | 16 | **19%** | 3 | 0 |
| NC | 12 | **17%** | 5 | 0 |
| PA | 8 | **12%** | 0 | 3 |
| VA | 7 | **0%** | 3 | 0 |

---

## Priority Data to Collect

### Priority 1: High Impact on Prediction

| Field | Why It Matters | Source |
|-------|----------------|--------|
| `total_beds` | Size = leverage | CMS, AHA |
| `market_share_pct` | Monopoly power | Definitive HC |
| `is_teaching_hospital` | Prestige/necessity | CMS |
| `operating_margin_pct` | Financial strength | HCRIS |

### Priority 2: Medium Impact

| Field | Why It Matters | Source |
|-------|----------------|--------|
| `annual_admissions` | Volume = importance | CMS |
| `employed_physicians_count` | Network control | AHA |
| `specialty_services` | Unique offerings | CMS |
| `trauma_level` | Essential service | State data |

### Priority 3: Nice to Have

| Field | Why It Matters | Source |
|-------|----------------|--------|
| `days_cash_on_hand` | Negotiation runway | HCRIS |
| `credit_rating` | Financial stability | S&P/Moody's |
| `payer_mix` | Revenue dependency | HCRIS |

---

## Free Data Sources

### 1. CMS Hospital Compare
- **URL**: https://data.cms.gov/provider-data/
- **Fields**: Beds, ownership, teaching status, quality scores
- **Format**: CSV download

### 2. HCRIS (Medicare Cost Reports)
- **URL**: https://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/Cost-Reports
- **Fields**: Financials, payer mix, bed counts
- **Format**: CSV (large files)

### 3. American Hospital Directory
- **URL**: https://www.ahd.com/
- **Fields**: Basic hospital profiles
- **Format**: Web lookup (free) or API (paid)

### 4. State Databases
- **CA**: OSHPD (now HCAI)
- **NY**: SPARCS
- **FL**: AHCA
- **TX**: DSHS

---

## Recommended Enrichment Workflow

```
1. Export unique health system list from disputes
2. Match to CMS Provider IDs (NPI or CCN)
3. Pull CMS Hospital Compare data
4. Pull HCRIS financial data
5. Calculate market share from state discharge data
6. Merge back to disputes dataset
7. Re-run predictive analysis
```

---

## Predictive Rules to Refine

Based on this analysis, update the prediction model:

```python
# STRONGEST PREDICTORS (confirmed)
if provider_type == "specialty_pediatric_cancer":
    resolution_boost = +0.50  # 87.5% vs 25% baseline

if provider_type == "community_rural":
    resolution_penalty = -0.25  # 0% resolution

# NEW GEOGRAPHIC FACTORS
if state in ["CT", "NY"]:
    resolution_boost = +0.15
elif state in ["VA", "PA", "MN"]:
    resolution_penalty = -0.15

# REPEAT PLAYERS
if system_previous_disputes >= 2:
    # Mixed effect - need more data
    pass
```

---

## Quick Win: Manual Enrichment for Top 20 Systems

| System | State | Disputes | Est. Beds | Est. Revenue | Priority |
|--------|-------|----------|-----------|--------------|----------|
| Hackensack Meridian | NJ | 4 | ~7,000 | $8B | HIGH |
| NewYork-Presbyterian | NY | 4 | ~2,600 | $10B | HIGH |
| M Health Fairview | MN | 4 | ~2,000 | $6B | HIGH |
| South Shore Health | MA | 4 | ~400 | $1B | MEDIUM |
| Phoenix Children's | AZ | 3 | ~600 | $2B | HIGH |
| Mayo Clinic | MN | 2 | ~1,200 | $16B | HIGH |
| Memorial Sloan Kettering | NY | 2 | ~500 | $7B | HIGH |
| Johns Hopkins | MD | 1 | ~1,100 | $12B | HIGH |

---

## Key Insight

**Specialty providers (pediatric + cancer) are essentially "must-have"** for insurers:
- 87.5% resolution rate (vs 25% average)
- Parents and cancer patients will switch insurers
- Reputational damage for insurers is severe
- These disputes almost always resolve favorably for providers
