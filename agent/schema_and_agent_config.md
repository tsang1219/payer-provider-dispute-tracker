# Payer-Provider Dispute Tracker: Schema & Agent Configuration

## Enhanced Data Schema

### Core Dispute Record

```yaml
# IDENTITY (from seed data)
dispute_id: integer                    # Your existing ID
dispute_name: string                   # Auto-generated: "{system_name} vs {insurer_short} {year}"

# PARTIES (from seed + enrichment)
system_name: string                    # From seed
system_name_normalized: string         # Cleaned/standardized name
system_hq_city: string                 # ENRICHMENT
system_hq_state: string                # From seed (state field)
system_hq_lat: float                   # ENRICHMENT (geocoded)
system_hq_lon: float                   # ENRICHMENT (geocoded)
system_footprint_states: string[]      # ENRICHMENT (multi-state systems)
system_hospital_count: integer         # ENRICHMENT
system_annual_revenue_mm: float        # ENRICHMENT (millions)
system_market_share_pct: float         # ENRICHMENT (in primary market)

insurer_name: string                   # From seed
insurer_name_normalized: string        # Parent company name
insurer_parent: string                 # Extracted from parens
insurer_type: enum                     # [Commercial, Medicare Advantage, Medicaid MCO, Multi-line]
insurer_market_share_state_pct: float  # ENRICHMENT

# TIMELINE (from seed + enrichment)
year_first_reported: integer           # From seed
quarter_first_reported: string         # From seed
first_media_date: date                 # ENRICHMENT (ISO format)
deadline_date: date                    # ENRICHMENT (contract expiration/OON date)
oon_effective_date: date               # ENRICHMENT (when actually went OON)
resolution_date: date                  # ENRICHMENT
back_in_network_date: date             # ENRICHMENT (if resolved)

# STATUS (from seed)
outcome_status: enum                   # From seed: [Resolved, OON-Temporary, OON-Ongoing, Unknown]
outcome_status_detail: string          # ENRICHMENT (more context)

# IMPACT METRICS (from seed notes + enrichment)
patients_affected: integer             # ENRICHMENT (extract from notes or search)
patients_affected_source: string       # How we got this number
dispute_type: enum                     # [Commercial, Medicare Advantage, Medicaid, All MA, Multi-type]
contract_type: enum                    # [Full network, Hospital only, Physician only, Specific service]

# NEGOTIATION DETAILS (enrichment)
rate_increase_requested_pct: float     # If disclosed
rate_increase_achieved_pct: float      # If resolved and disclosed
prior_contract_years: integer          # How long previous contract lasted
key_issues: string[]                   # [rates, prior_auth, denial_rates, admin_burden, site_of_care]

# RESOLUTION (enrichment)
resolution_type: enum                  # [Multi-year contract, Short-term extension, Arbitration, 
                                       #  State intervention, Permanent termination, Unknown, null]
resolution_terms_summary: string       # Brief summary
lawsuit_filed: boolean                 # If litigation involved
lawsuit_outcome: string                # If applicable

# SOURCES & META
primary_source: string                 # From seed
primary_source_url: string             # ENRICHMENT
additional_sources: string[]           # ENRICHMENT (URLs)
notes: string                          # From seed
enrichment_notes: string               # Agent notes during enrichment
last_updated: datetime
data_completeness_score: float         # 0-1, calculated
```

### Timeline Events Table (for animation)

```yaml
# Flattened events for time-series animation
event_id: string                       # Auto-generated
dispute_id: integer                    # FK to dispute
event_date: date                       # ISO format
event_type: enum                       # [dispute_public, deadline_announced, oon_effective, 
                                       #  extension_granted, resolution_announced, back_in_network]
event_description: string              # Brief description
source_url: string                     # Where we learned this
```

### Reference Tables

```yaml
# Health Systems Reference
system_id: string
system_name: string
system_name_variants: string[]         # Alternative names
hq_city: string
hq_state: string
lat: float
lon: float
hospital_count: integer
annual_revenue_mm: float
ownership_type: enum                   # [Non-profit, For-profit, Government, Academic]
footprint_states: string[]

# Payers Reference
payer_id: string
payer_name: string
payer_name_variants: string[]
parent_company: string
payer_type: enum
market_share_by_state: json            # {state: percentage}
```

---

## Agent Configuration

### Environment Setup

```bash
# Required for Claude Code agent
pip install anthropic requests pandas airtable-python-wrapper geopy
```

### Agent Workflow

```python
"""
Payer-Provider Dispute Enrichment Agent
Run from Claude Code or as standalone script
"""

WORKFLOW_STAGES = [
    "parse_existing_notes",      # Extract data already in notes field
    "geocode_systems",           # Get lat/lon for health system HQs
    "search_dispute_details",    # Web search for dates, patient counts, terms
    "enrich_system_data",        # Revenue, bed count, market share
    "enrich_payer_data",         # Market share by state
    "calculate_completeness",    # Score each record
    "export_to_airtable"         # Push to Airtable
]
```

### Stage 1: Parse Existing Notes

Many records have extractable data in the notes field. Patterns to extract:

```python
EXTRACTION_PATTERNS = {
    "patients_affected": [
        r"(\d{1,3}(?:,\d{3})*)\s*patients",           # "80,000 patients"
        r"(\d{1,3}(?:,\d{3})*)\s*(?:members|seniors)", # "30,000 seniors"
        r"affecting\s*(\d{1,3}(?:,\d{3})*)",          # "affecting 17,000"
    ],
    "oon_date": [
        r"OON\s*(?:effective\s*)?(\w+\s+\d{1,2}(?:,?\s*\d{4})?)",  # "OON Jan 1, 2024"
        r"(?:ended|terminated|expired)\s*(\w+\s+\d{1,2},?\s*\d{4})", # "ended Oct 1, 2021"
    ],
    "duration": [
        r"(\d+)\s*months?\s*OON",                     # "11 months OON"
    ],
    "rate_info": [
        r"(\d+(?:\.\d+)?%)\s*(?:vs|offer|increase)",  # "35% vs 3.4%"
        r"rates?\s*unchanged\s*(?:since\s*)?(\d{4})", # "rates unchanged since 2020"
    ],
    "dollar_amounts": [
        r"\$(\d+(?:\.\d+)?[MB])",                     # "$93M unpaid claims"
    ],
}
```

### Stage 2: Search Queries per Dispute

```python
def generate_search_queries(row):
    """Generate search queries for a dispute row"""
    system = row['system_name']
    insurer = row['insurer_name'].split('(')[0].strip()  # Remove parent company
    year = row['year_first_reported']
    
    return [
        f"{system} {insurer} contract dispute {year}",
        f"{system} out of network {insurer}",
        f"{system} {insurer} negotiation patients affected",
        f"{system} {insurer} contract resolution",
    ]
```

### Stage 3: Data Sources for Enrichment

```yaml
Health System Data:
  - IRS Form 990 (via ProPublica Nonprofit Explorer API)
  - SEC EDGAR (for publicly traded systems)
  - State hospital cost reports
  - AHA Hospital Database (if access available)
  - Wikipedia/official websites for HQ location

Payer Market Share:
  - State insurance department annual reports
  - KFF State Health Facts
  - CMS Medicare Advantage enrollment data
  - Mark Farrah Associates (if access available)

Geocoding:
  - Nominatim (OpenStreetMap) - free
  - Google Maps Geocoding API - paid but accurate
  - US Census Geocoder - free, US-only
```

### Airtable Configuration

```yaml
Base Name: "Payer-Provider Disputes"

Tables:
  Disputes:
    - All fields from schema above
    - Link to Health Systems table
    - Link to Payers table
    - Link to Timeline Events table
    
  Health Systems:
    - Reference data for each unique system
    - Linked from Disputes (many-to-one)
    
  Payers:
    - Reference data for each payer
    - Linked from Disputes (many-to-one)
    
  Timeline Events:
    - Individual events for animation
    - Linked from Disputes (one-to-many)
    
  Sources:
    - All URLs with extraction notes
    - Linked from Disputes (many-to-many)

Views:
  - "By Year" - Group by year_first_reported
  - "By Payer" - Group by insurer_parent
  - "By Status" - Group by outcome_status
  - "Needs Enrichment" - Filter: data_completeness_score < 0.5
  - "Map Ready" - Filter: has lat/lon coordinates
```

---

## Visualization Specifications

### Choropleth Map with Time Animation

```yaml
Map Type: US State choropleth with point overlay

Base Layer:
  - State boundaries
  - Color intensity = number of active disputes in state

Point Layer:
  - Position = health system HQ lat/lon
  - Size = patients_affected (scaled logarithmically)
  - Color = outcome_status
    - Red: OON-Ongoing
    - Orange: OON-Temporary  
    - Green: Resolved
    - Gray: Unknown
  - Opacity = recency (more recent = more opaque)

Time Animation:
  - Slider: Q1 2021 → Q4 2025
  - Points appear on first_media_date or dispute_public_date
  - Points change color as status changes
  - Points fade after resolution_date + 90 days

Interaction:
  - Hover: Show dispute summary tooltip
  - Click: Open detail panel with full timeline
  - Filter controls: by payer, by status, by dispute_type

Legend:
  - Status colors
  - Size scale (patient impact)
  - Active dispute count
```

### Flourish Implementation Notes

```yaml
Flourish Template: "Projection map"

Data Format Required:
  - Latitude, Longitude columns
  - Size column (patients_affected)
  - Color column (outcome_status)
  - Time column (for animation)
  - Name column (for tooltip)

Columns to Prepare:
  - animation_frame: Concatenate year + quarter (e.g., "2024-Q1")
  - tooltip_text: Pre-formatted summary
  - size_normalized: Log-scaled patient count
```

---

## Next Steps

1. **Immediate**: Run note parsing to extract embedded data
2. **Day 1**: Geocode all health systems with confirmed HQs
3. **Day 2-3**: Web search enrichment for top 50 disputes by patient impact
4. **Day 4**: Populate Airtable with enriched data
5. **Day 5**: Create Flourish prototype with available data
6. **Ongoing**: Iteratively enrich remaining records

---

## Sample Agent Prompts

### For Claude Code - Single Dispute Enrichment

```
Research the following hospital-insurer contract dispute and extract structured data:

Dispute: {system_name} vs {insurer_name} ({state}, {year})
Current notes: {notes}

Find and return:
1. Exact dates (when dispute went public, OON effective date, resolution date)
2. Number of patients/members affected
3. Key negotiation issues (rates, prior auth, denial rates, etc.)
4. Resolution terms if resolved
5. Health system HQ city for geocoding
6. Any lawsuit or arbitration outcomes

Format as JSON matching the schema above.
```

### For Batch Processing

```
Process the following batch of disputes. For each:
1. Parse the notes field for extractable data
2. Search for additional details
3. Return structured JSON

Skip disputes marked as "FTI Aggregate" - these are placeholders.

Disputes:
{batch_of_10_disputes}
```
