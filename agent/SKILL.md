# Payer-Provider Dispute Enrichment Agent

## Purpose
This agent systematically enriches hospital-insurer contract dispute records by researching each dispute via web search and populating missing data fields.

## Data Files
- `disputes_to_enrich.csv` - Input: disputes needing enrichment
- `disputes_enriched.csv` - Output: enriched dispute records
- `health_systems_reference.json` - Reference: health system attributes
- `enrichment_state.json` - State: tracks progress for resumability

## Workflow

### Step 1: Load State
```python
# Check enrichment_state.json for last processed dispute_id
# Resume from where we left off
```

### Step 2: For Each Dispute (batch of 5-10 at a time)

#### 2a. Research the Dispute
Search for information using these query patterns:
1. `"{system_name}" "{insurer_short_name}" contract dispute {year}`
2. `"{system_name}" out of network {year}`
3. `"{system_name}" "{insurer_short_name}" patients affected`

#### 2b. Extract These Fields
From search results, extract:

**Timeline:**
- `first_media_date` - When dispute first appeared in news (YYYY-MM-DD)
- `deadline_date` - Contract expiration or OON effective date
- `oon_effective_date` - When actually went out-of-network
- `resolution_date` - When resolved (if applicable)

**Impact:**
- `patients_affected` - Number of patients/members impacted
- `patients_affected_source` - URL or publication where found

**Negotiation Details:**
- `rate_increase_requested_pct` - Percentage increase requested (if disclosed)
- `key_issues` - Array of issues: ["rates", "prior_auth", "denial_rates", "admin_burden", "site_of_care", "reimbursement_timeline"]
- `contract_length_years` - Previous contract duration

**Resolution (if resolved):**
- `resolution_type` - One of: "Multi-year contract", "Short-term extension", "Arbitration", "State intervention", "Permanent termination"
- `resolution_terms_summary` - Brief summary of deal terms

**Sources:**
- `primary_source_url` - URL of main source
- `additional_sources` - Array of other relevant URLs

#### 2c. Enrich Health System Data
If system not in `health_systems_reference.json`, research and add:
- `ownership_type` - "Non-profit", "For-profit", "Government", "Academic"
- `is_academic_medical_center` - true/false
- `hospital_count` - Number of hospitals in system
- `annual_revenue_mm` - Annual revenue in millions (from 990 or 10-K)
- `bed_count` - Total licensed beds
- `primary_service_area` - Main metro/region served
- `system_hq_city` - Headquarters city
- `system_hq_state` - Headquarters state
- `system_hq_lat` - Latitude
- `system_hq_lon` - Longitude

#### 2d. Update State
After each dispute:
1. Write enriched record to `disputes_enriched.csv`
2. Update `enrichment_state.json` with last_processed_id
3. Update `health_systems_reference.json` if new system data found

### Step 3: Quality Checks
After each batch:
- Verify dates are in valid format (YYYY-MM-DD)
- Verify patient counts are reasonable (< 1,000,000)
- Flag any conflicts with existing data
- Calculate data_completeness_score

## Output Schema

### Dispute Record
```json
{
  "dispute_id": 123,
  "dispute_name": "Johns Hopkins vs UnitedHealthcare 2025",
  
  "system_name": "Johns Hopkins Medicine",
  "system_id": "johns_hopkins",
  "system_hq_state": "MD",
  "system_hq_city": "Baltimore",
  "system_hq_lat": 39.2904,
  "system_hq_lon": -76.6122,
  "system_ownership_type": "Non-profit",
  "system_is_academic": true,
  "system_hospital_count": 6,
  "system_annual_revenue_mm": 12500,
  
  "insurer_name": "UnitedHealthcare",
  "insurer_parent": "UnitedHealth Group",
  "insurer_type": "Multi-line",
  
  "year_first_reported": 2025,
  "quarter_first_reported": "Q3",
  "first_media_date": "2025-07-15",
  "deadline_date": "2025-08-25",
  "oon_effective_date": "2025-08-25",
  "resolution_date": null,
  
  "outcome_status": "OON-Ongoing",
  "dispute_type": "Medicare Advantage",
  
  "patients_affected": 60000,
  "patients_affected_source": "Modern Healthcare",
  
  "rate_increase_requested_pct": null,
  "key_issues": ["rates", "denial_rates", "admin_burden"],
  
  "resolution_type": null,
  "resolution_terms_summary": null,
  
  "primary_source": "Modern Healthcare",
  "primary_source_url": "https://...",
  "additional_sources": ["https://..."],
  
  "notes": "OON Aug 25; 60,000 patients",
  "enrichment_notes": "Searched 2025-01-04. Found patient count in Modern Healthcare article.",
  "data_completeness_score": 0.75,
  "last_updated": "2025-01-04T20:30:00Z"
}
```

### Health System Reference
```json
{
  "johns_hopkins": {
    "name": "Johns Hopkins Medicine",
    "name_variants": ["Johns Hopkins", "Johns Hopkins Health System", "JHHS"],
    "ownership_type": "Non-profit",
    "is_academic_medical_center": true,
    "hospital_count": 6,
    "annual_revenue_mm": 12500,
    "bed_count": 2500,
    "employees": 43000,
    "hq_city": "Baltimore",
    "hq_state": "MD",
    "hq_lat": 39.2904,
    "hq_lon": -76.6122,
    "footprint_states": ["MD", "DC", "FL"],
    "primary_service_area": "Baltimore-Washington metro",
    "data_sources": ["Form 990", "Wikipedia"],
    "last_updated": "2025-01-04"
  }
}
```

## Search Strategy

### For Dispute Details
```
Query 1: "{system_name}" "{insurer}" contract dispute {year}
- Look for: dates, patient counts, negotiation issues

Query 2: "{system_name}" out of network "{insurer}" 
- Look for: OON effective date, duration, patient impact

Query 3: "{system_name}" "{insurer}" agreement resolved
- Look for: resolution date, terms, contract length
```

### For Health System Attributes
```
Query 1: "{system_name}" annual revenue hospitals
- Look for: revenue, hospital count, ownership

Query 2: "{system_name}" Form 990 OR 10-K
- Look for: financial details, governance

Query 3: "{system_name}" academic medical center teaching hospital
- Look for: academic affiliation, teaching status
```

## Handling Edge Cases

### Multi-State Systems
For systems operating in multiple states (e.g., Ascension, Providence):
- Use HQ location for primary lat/lon
- Populate `footprint_states` array
- Note in `enrichment_notes` if dispute is state-specific

### Multiple Insurers in One Dispute
Some disputes involve multiple payers (e.g., "UnitedHealthcare/Humana"):
- Keep as single record with combined insurer name
- Note each payer in `enrichment_notes`
- Use primary payer for `insurer_parent`

### "All MA Plans" Disputes
For hospitals dropping all Medicare Advantage:
- Set `insurer_name` = "All Medicare Advantage Plans"
- Set `insurer_parent` = null
- Set `dispute_type` = "All MA"

### Conflicting Information
If sources disagree on patient counts or dates:
- Use most authoritative source (hospital press release > news article)
- Note discrepancy in `enrichment_notes`
- Use most conservative (lower) patient count

## Progress Tracking

The agent maintains state in `enrichment_state.json`:
```json
{
  "last_processed_id": 45,
  "total_disputes": 169,
  "enriched_count": 45,
  "high_completeness_count": 23,
  "medium_completeness_count": 15,
  "low_completeness_count": 7,
  "last_run": "2025-01-04T20:30:00Z",
  "errors": [
    {"dispute_id": 32, "error": "No search results found"}
  ]
}
```

## Commands

### Start/Resume Enrichment
```
Enrich the next 10 disputes from disputes_to_enrich.csv, starting from where we left off.
```

### Enrich Specific Dispute
```
Research and enrich dispute ID 123 (Johns Hopkins vs UnitedHealthcare).
```

### Enrich Health System
```
Research and add health system attributes for "Memorial Hermann Health System".
```

### Generate Progress Report
```
Show enrichment progress and identify disputes still needing research.
```

### Export for Visualization
```
Export map-ready data with all geocoded disputes to disputes_map_ready.csv.
```
