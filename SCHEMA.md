# Disputes Database Schema

This document describes all 57 fields in the canonical dataset: `data/primary/disputes_enriched.csv`

**Last Updated:** July 7, 2026
**Records:** 195 disputes (203 before the 2026-01 duplicate cleanup)
**Columns:** 57 fields
**Date Range:** 2021-2025
**Mean Completeness Score:** 0.77

---

## Field Reference

### Identity Fields

| Field | Type | Description |
|-------|------|-------------|
| `dispute_id` | integer | Unique identifier for each dispute |
| `dispute_name` | string | Auto-generated name: "{system_name} vs {insurer_short} {year}" |

### Health System Fields

| Field | Type | Description |
|-------|------|-------------|
| `system_name` | string | Official health system name |
| `system_name_normalized` | string | Cleaned/shortened name for matching |
| `system_hq_city` | string | Headquarters city |
| `system_hq_state` | string | Headquarters state (2-letter code) |
| `system_hq_lat` | float | Latitude for mapping |
| `system_hq_lon` | float | Longitude for mapping |
| `system_footprint_states` | string | Comma-separated list of states where system operates |
| `system_hospital_count` | integer | Number of hospitals in the system |
| `system_type` | enum | `academic`, `large_system`, `regional`, `community`, `physician_group`, `critical_access`, `specialty_*` |
| `total_beds` | integer | Total licensed beds across all facilities |
| `is_teaching_hospital` | boolean | Whether system has academic/teaching affiliation |
| `market_share_pct` | float | Market share percentage in primary market |
| `operating_margin_pct` | float | Operating margin percentage |
| `annual_revenue_mm` | float | Annual revenue in millions USD |
| `employed_physicians` | integer | Number of employed physicians |
| `enrichment_source` | string | Source of system enrichment data |
| `state` | string | Primary state for the dispute (may differ from HQ state) |

### Insurer Fields

| Field | Type | Fill Rate | Description |
|-------|------|-----------|-------------|
| `insurer_name` | string | 100% | Full insurer name (may include parent in parentheses) |
| `insurer_name_normalized` | string | 100% | Cleaned insurer name without parent |
| `insurer_parent` | string | 49% | Parent company (e.g., "UnitedHealth Group", "Elevance Health") |
| `insurer_type` | enum | 100% | `Commercial` (146), `Medicare Advantage` (53), `Medicaid MCO` (4) |

### Timeline Fields

| Field | Type | Description |
|-------|------|-------------|
| `year_first_reported` | integer | Year dispute first appeared in media (2021-2025) |
| `quarter_first_reported` | string | Quarter: `Q1`, `Q2`, `Q3`, `Q4` |
| `first_media_date` | date | Exact date of first media coverage (ISO format) |
| `deadline_date` | date | Contract expiration or OON deadline date |
| `oon_effective_date` | date | Date patients actually went out-of-network |
| `resolution_date` | date | Date dispute was resolved (if applicable) |
| `duration_months` | float | How long the dispute lasted in months |
| `duration_days` | integer | How long the dispute lasted in days |

### Status & Outcome Fields

| Field | Type | Description |
|-------|------|-------------|
| `outcome_status` | enum | Current status (see values below) |
| `outcome_status_detail` | string | Additional context on status |
| `resolution_type` | enum | How it was resolved (see values below) |
| `resolution_terms_summary` | string | Brief description of resolution terms |
| `lawsuit_filed` | boolean | Whether litigation was involved |
| `dollar_amount_mm` | float | Dollar amounts involved (settlements, unpaid claims) in millions |

**outcome_status values (current data uses exactly three):**
- `Resolved` (87) - Contract dispute settled, back in-network
- `OON-Ongoing` (74) - Currently out-of-network, no resolution
- `OON-Permanent` (34) - Permanent network split, no agreement expected

*(Legacy values `OON-Temporary`, `OON-Negotiating`, `OON-Partial`, `Unknown` were consolidated in the 2026-01 status-correction pass and no longer appear; the site and monthly job accept only the three current values for new rows.)*

**resolution_type values:**
- `Multi-year contract` - New long-term agreement
- `Short-term extension` - Temporary agreement
- `Arbitration` - Resolved through arbitration
- `State intervention` - State regulators involved
- `Permanent termination` - No resolution, permanent OON
- `Unknown` - Resolution type unclear

### Impact Fields

| Field | Type | Description |
|-------|------|-------------|
| `patients_affected` | float | Number of patients impacted |
| `patients_affected_source` | string | How patient count was determined (see below) |
| `dispute_type` | enum | `Commercial`, `Medicare Advantage`, `Medicaid`, `All MA`, `Multi-type`, `Unknown` |

**patients_affected_source values:**
- `extracted_from_notes_patients` - Extracted from notes field
- `estimated_commercial_estimation` - Calculated from market data
- `estimated_ma_enrollment_estimation` - Calculated from MA enrollment
- `known_calibration` - Verified from reliable source
- `revenue_based_estimation` - Estimated from revenue data

### Negotiation Details

| Field | Type | Description |
|-------|------|-------------|
| `rate_increase_requested_pct` | float | Rate increase requested by provider |
| `rate_info_raw` | string | Raw rate information from sources |
| `leading_factors` | string | Primary factors driving the dispute |
| `key_issues` | string | Main negotiation sticking points |
| `resolution_terms` | string | Detailed terms of resolution |

### Source & Documentation Fields

| Field | Type | Description |
|-------|------|-------------|
| `primary_source` | string | Main news/media source |
| `primary_source_url` | string | URL to primary source |
| `additional_sources` | string | Additional source URLs |
| `first_media_date_source` | string | URL where first media coverage was found |
| `resolution_date_source` | string | URL confirming resolution (if applicable) |
| `deadline_date_source` | string | URL mentioning contract deadline |
| `oon_effective_date_source` | string | URL confirming OON effective date |
| `notes` | string | Original notes from seed data |
| `enrichment_notes` | string | Notes added during enrichment process |

### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `data_completeness_score` | float | 0-1 score indicating data completeness |
| `last_updated` | datetime | When record was last modified (ISO format) |
| `manually_verified` | boolean | Whether data has been manually verified |

---

## Data Quality Notes

### Completeness Score Calculation
The `data_completeness_score` (0.0-1.0) is calculated based on 10 points:

| Component | Points | Description |
|-----------|--------|-------------|
| Coordinates | 2 | Has lat/lon for mapping |
| Patient count | 2 | Has patients_affected > 0 |
| OON date | 1 | Has oon_effective_date |
| Resolution date | 1 | Has resolution_date (or ongoing dispute) |
| Source URL | 1 | Has primary_source_url |
| Insurer parent | 1 | Has insurer_parent filled |
| System type | 1 | Has system_type categorization |
| Notes | 1 | Has substantive notes/enrichment_notes |

**Current Distribution:**
- Mean: 0.77
- Min: 0.50, Max: 1.00
- 104 records at 70%+ completeness

### Patient Count Estimation
When exact patient counts aren't available, they're estimated using:
1. **Commercial estimation**: Annual patients × payer market share × 0.8 adjustment
2. **MA enrollment estimation**: State MA enrollment × payer share × hospital share
3. **Revenue-based**: Derived from system revenue and payer mix

### Common Data Gaps
- `first_media_date` - Often only year/quarter known
- `oon_effective_date` - Not always publicly reported
- `patients_affected` - Frequently estimated rather than exact
- `resolution_terms_summary` - Details often confidential

---

## Example Record

```csv
dispute_id: 1
dispute_name: "Dignity Health vs Anthem Blue Cross 2021"
system_name: "Dignity Health"
system_hq_state: "CA"
system_hq_lat: 37.7749
system_hq_lon: -122.4194
insurer_name: "Anthem Blue Cross"
year_first_reported: 2021
outcome_status: "Resolved"
patients_affected: 48000
data_completeness_score: 0.5
```
