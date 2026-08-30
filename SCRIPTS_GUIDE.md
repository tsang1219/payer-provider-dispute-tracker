# Scripts Guide

This document explains how to use all the scripts in the project, organized by purpose.

**Last Updated:** January 21, 2026

---

## Script Organization

```
scripts/
├── visualization/      # Generate outputs for DataWrapper, Flourish, etc.
├── enrichment/         # Enrich the canonical dataset
└── maintenance/        # Data validation and quality checks
```

---

## Visualization Scripts

### `scripts/visualization/regenerate_datawrapper_simple.py`
**Purpose:** Generate the current DataWrapper range plot CSV

**What it does:**
- Reads `data/primary/disputes_enriched.csv`
- Creates simplified timeline format with start/end dates
- Outputs to `data/derived/visualizations/datawrapper_range_plot_simple.csv`

**Usage:**
```bash
python scripts/visualization/regenerate_datawrapper_simple.py
```

**When to run:**
- After updating dispute dates in the primary CSV
- After adding new disputes
- Before uploading to DataWrapper

**Output columns:**
- `dispute_name` - Display label
- `start_date` - First media date or year/quarter
- `end_date` - Resolution date or current date (for ongoing)
- `outcome_status` - For color coding
- `patients_affected` - For sizing/tooltips
- `state` - Geographic filter

---

### `scripts/visualization/create_flourish_timeslider.py`
**Purpose:** Generate Flourish time-slider visualization format

**What it does:**
- Transforms disputes into quarterly snapshots (2021 Q1 - 2025 Q4)
- Creates 20 quarter columns showing dispute status over time
- Outputs to `data/derived/visualizations/disputes_flourish_timeslider.csv`

**Usage:**
```bash
python scripts/visualization/create_flourish_timeslider.py
```

**When to run:**
- After major updates to dispute timeline data
- When creating animated Flourish visualizations

---

### `scripts/visualization/create_datawrapper_range_plot.py`
**Purpose:** Original DataWrapper range plot generator (archived approach)

**Status:** Superseded by `regenerate_datawrapper_simple.py`

---

### `scripts/visualization/create_datawrapper_all_disputes.py`
**Purpose:** Alternative DataWrapper format including all disputes

**Status:** Experimental variant, use `regenerate_datawrapper_simple.py` for production

---

### `scripts/visualization/create_datawrapper_with_tooltips.py`
**Purpose:** DataWrapper format with rich tooltip data

**Status:** Experimental variant with detailed hover text

---

## Enrichment Scripts

### `scripts/enrichment/enrich_disputes_batch.py`
**Purpose:** Batch enrichment of disputes from notes and sources

**What it does:**
- Extracts dates from notes field using regex patterns
- Fills missing system data from health_systems_reference.json
- Calculates data completeness scores
- Updates the canonical CSV in-place

**Usage:**
```bash
python scripts/enrichment/enrich_disputes_batch.py
```

**When to run:**
- After manually adding notes to disputes
- After updating health_systems_reference.json
- When recalculating completeness scores

**Safety:** Creates backups before modifying data

---

### `scripts/enrichment/process_worksheet_results.py`
**Purpose:** Process manual research from worksheet

**What it does:**
- Reads `worksheets/search_query_worksheet.csv`
- Extracts manual research findings (dates, patient counts, URLs)
- Updates `data/primary/disputes_enriched.csv` with verified data

**Usage:**
```bash
python scripts/enrichment/process_worksheet_results.py
```

**When to run:**
- After completing manual research in the worksheet
- When integrating verified data from external research

**Workflow:**
1. Fill out search_query_worksheet.csv with findings
2. Run this script to apply updates
3. Review changes to disputes_enriched.csv

---

### `scripts/enrichment/enrich_oon_dates.py`
**Purpose:** Specifically enrich out-of-network effective dates

**What it does:**
- Focuses on finding and validating `oon_effective_date` field
- Uses web search or notes extraction
- Updates source URLs for traceability

**Usage:**
```bash
python scripts/enrichment/enrich_oon_dates.py
```

**When to run:**
- When focusing on timeline data quality
- After finding new sources with OON dates

---

### `scripts/enrichment/manual_patient_estimation.py`
**Purpose:** Calculate patient counts using estimation frameworks

**What it does:**
- Applies commercial insurance estimation
- Applies MA enrollment estimation
- Uses revenue-based fallbacks
- Adds confidence scores and sources

**Usage:**
```bash
python scripts/enrichment/manual_patient_estimation.py
```

**When to run:**
- When disputes are missing patient counts
- After updating payer_market_reference.json
- To refresh estimates with new methodology

---

### `scripts/enrichment/update_missing_patients.py`
**Purpose:** Fill missing patient counts for specific disputes

**What it does:**
- Identifies disputes with null patient_affected
- Applies appropriate estimation method
- Updates with source attribution

**Usage:**
```bash
python scripts/enrichment/update_missing_patients.py
```

---

## Maintenance Scripts

### `scripts/maintenance/validate_dates.py`
**Purpose:** Validate date logic and consistency

**What it does:**
- Checks for dates in wrong order (resolution before OON)
- Flags impossible dates (future dates, dates before 2015)
- Validates source URLs exist for key dates
- Outputs validation report

**Usage:**
```bash
python scripts/maintenance/validate_dates.py
```

**When to run:**
- After batch date updates
- Before generating visualizations
- As part of data quality checks

**Output:**
- Prints violations to console
- May output `date_corrections_needed.csv` for review

---

### `scripts/maintenance/analyze_missing_dates.py`
**Purpose:** Analyze patterns in missing date fields

**What it does:**
- Counts missing dates by field type
- Identifies disputes needing enrichment
- Suggests research priorities

**Usage:**
```bash
python scripts/maintenance/analyze_missing_dates.py
```

**When to run:**
- During planning for enrichment work
- To understand data gaps
- Before creating research worksheets

---

## Agent Scripts

The `agent/` folder contains specialized Claude Code agents. See [agent/SKILL.md](agent/SKILL.md) for usage.

**Key agents:**
- `dispute_enrichment_agent.py` - Main enrichment agent
- `improved_web_search_enrichment.py` - Web search utilities
- `patient_estimation_agent.py` - Patient count estimation
- `automated_backfill_agent.py` - Finding new disputes
- `dispute_discovery_agent.py` - Discovery via search

---

## Analysis Scripts

The `analysis/` folder contains analysis and research scripts:

- `dispute_pattern_analyzer.py` - Pattern analysis and insights
- `predict_outcome.py` - Outcome prediction model
- `complete_system_enrichment.py` - System-level enrichment
- `enrich_top_systems.py` - Top 30 systems focus
- `add_coordinates.py` - Geocoding utilities
- `health_system_characteristics_analysis.py` - System analysis

---

## Archived Scripts

`archive/scripts_oneoff/` contains one-time scripts used for historical data fixes:

**Categories:**
- Date validation and correction scripts
- URL enrichment utilities
- Patient count corrections
- Data migration scripts

**These should NOT be re-run** as they were for specific one-time fixes.

---

## Common Workflows

### Workflow 1: Add New Disputes
```bash
# 1. Add to disputes_enriched.csv manually or via agent
# 2. Run batch enrichment
python scripts/enrichment/enrich_disputes_batch.py

# 3. Validate data
python scripts/maintenance/validate_dates.py

# 4. Regenerate visualizations
python scripts/visualization/regenerate_datawrapper_simple.py
python scripts/visualization/create_flourish_timeslider.py
```

### Workflow 2: Update Timeline Data
```bash
# 1. Make manual corrections to CSV or use worksheet
python scripts/enrichment/process_worksheet_results.py

# 2. Validate changes
python scripts/maintenance/validate_dates.py

# 3. Regenerate DataWrapper file
python scripts/visualization/regenerate_datawrapper_simple.py
```

### Workflow 3: Quality Check
```bash
# 1. Check for date issues
python scripts/maintenance/validate_dates.py

# 2. Analyze missing data
python scripts/maintenance/analyze_missing_dates.py

# 3. Enrich as needed
python scripts/enrichment/enrich_disputes_batch.py
```

---

## Best Practices

1. **Always backup before running enrichment scripts**
   - Most scripts create automatic backups
   - Check `archive/data_backups/` for recent backups

2. **Run validation after changes**
   - Use `validate_dates.py` after date updates
   - Check completeness scores after enrichment

3. **Regenerate visualization files when needed**
   - After timeline changes → regenerate datawrapper_simple
   - After adding disputes → regenerate all viz files
   - Before publishing → run all viz generators

4. **Document manual changes**
   - Add notes to `enrichment_notes` field
   - Include source URLs when adding data
   - Set `manually_verified=True` for verified data

5. **Keep canonical CSV clean**
   - All changes flow through scripts, not manual edits
   - If manual edits needed, recalculate completeness scores
   - Update `last_updated` timestamp

---

## Script Dependencies

All scripts depend on:
- `pandas` - Data manipulation
- `data/primary/disputes_enriched.csv` - Canonical dataset
- `data/reference/health_systems_reference.json` - System lookup

Some scripts also use:
- `data/reference/payer_market_reference.json` - Patient estimation
- `worksheets/search_query_worksheet.csv` - Manual research input

---

## Troubleshooting

**Script fails with "file not found":**
- Check you're running from project root
- Verify input file exists at expected path

**Dates look wrong after enrichment:**
- Run `validate_dates.py` to check logic
- Review `enrichment_notes` for extraction issues

**Completeness scores not updating:**
- Re-run `enrich_disputes_batch.py`
- Check that required fields are filled

**Visualization file missing columns:**
- Check generator script for recent changes
- Verify canonical CSV has expected columns
