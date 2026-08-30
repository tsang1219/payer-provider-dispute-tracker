# Payer-Provider Dispute Tracker

A living dataset of U.S. hospital–insurer contract disputes (2021–present), with a hosted interactive web app, a monthly self-maintenance job, and visualization exports for DataWrapper and Flourish.

This is an independent, visibility-biased tracker rather than a comprehensive census. Read [METHODOLOGY.md](METHODOLOGY.md) for definitions, estimation caveats, and the correction process. Contributions are welcome through [CONTRIBUTING.md](CONTRIBUTING.md).

## Quick Start

**Canonical Dataset:** [data/primary/disputes_enriched.csv](data/primary/disputes_enriched.csv) (195 disputes after the 2026-01 dedup pass, 57 fields)

This is THE source of truth. Everything else derives from it.

**The three moving parts (built 2026-07):**

| Piece | Where | Run |
|---|---|---|
| Interactive site (map · timeline · filters · state-of-the-fight) | `site/` | `cd site && npm run dev` — deploy: see [DEPLOY.md](DEPLOY.md) |
| Monthly update job (discovery + status re-check → human review gate) | `scripts/monthly_update/` | `python3 scripts/monthly_update/monthly_update.py run` — see its [README](scripts/monthly_update/README.md) |
| Site data + viz export regeneration | `scripts/site_data/`, `scripts/visualization/` | `python3 scripts/monthly_update/monthly_update.py rebuild` |

New data enters canonical **only** through the review gate in `review/` + the `apply` command (validates, backs up, merges).

## Project Structure

```
payer_provider_disputes/
│
├── data/
│   ├── primary/
│   │   └── disputes_enriched.csv       # CANONICAL DATASET (57 columns)
│   ├── reference/
│   │   ├── health_systems_reference.json
│   │   ├── payer_market_reference.json
│   │   └── enrichment_state.json
│   └── derived/
│       ├── visualizations/
│       │   ├── datawrapper_range_plot_simple.csv   # DataWrapper (CURRENT)
│       │   ├── disputes_flourish_timeslider.csv    # Flourish animation
│       │   ├── disputes_map_ready.csv              # Flourish map
│       │   └── timeline_events.csv
│       └── exports/
│           └── disputes_enriched.json              # Airtable/API
│
├── scripts/
│   ├── visualization/
│   │   ├── regenerate_datawrapper_simple.py    # Generate DataWrapper CSV
│   │   └── create_flourish_timeslider.py       # Generate Flourish CSV
│   ├── enrichment/
│   │   ├── enrich_disputes_batch.py            # Batch enrichment
│   │   └── process_worksheet_results.py        # Process manual research
│   └── maintenance/
│       ├── validate_dates.py                   # Date validation
│       └── analyze_missing_dates.py            # Gap analysis
│
├── agent/                              # Claude Code agents (12 scripts)
├── analysis/                           # Analysis scripts (6 scripts)
├── visualizations/                     # Viz prototypes (1 script)
│
├── input/
│   └── disputes_to_enrich.csv          # Original seed data
│
├── worksheets/
│   └── search_query_worksheet.csv      # Manual research tracker
│
├── archive/
│   ├── scripts_oneoff/                 # One-time data fix scripts
│   ├── data_backups/                   # Backup CSVs and corrections
│   └── task_batches/                   # Historical batch task files
│
├── README.md                           # This file
├── SCHEMA.md                           # Field documentation (57 fields)
├── DATA_DICTIONARY.md                  # File purposes and data flow
├── SCRIPTS_GUIDE.md                    # How to run scripts
└── WORKSHEET_GUIDE.md                  # Manual research guide
```

## Documentation

| Document | Purpose |
|----------|---------|
| [SCHEMA.md](SCHEMA.md) | Complete documentation of all 57 fields |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Explains all data files and their uses |
| [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md) | How to run and when to use each script |
| [WORKSHEET_GUIDE.md](WORKSHEET_GUIDE.md) | Guide for manual research workflow |
| [agent/SKILL.md](agent/SKILL.md) | Claude Code agent instructions |

## Key Files

| File | Records | Purpose |
|------|---------|---------|
| `data/primary/disputes_enriched.csv` | 195 | **CANONICAL** - all analysis starts here |
| `data/derived/visualizations/datawrapper_range_plot_simple.csv` | 58 | Resolved disputes lasting at least 30 days |
| `data/derived/visualizations/disputes_flourish_timeslider.csv` | 195 | Flourish time animation |
| `data/derived/visualizations/disputes_map_ready.csv` | 195 | Geocoded records for maps |
| `data/derived/exports/disputes_enriched.json` | 195 | JSON export |

## Common Tasks

### Update Timeline Data
```bash
# After updating dates in disputes_enriched.csv
python scripts/maintenance/validate_dates.py
python scripts/visualization/regenerate_datawrapper_simple.py
```

### Add New Disputes
```bash
# 1. Add to disputes_enriched.csv
# 2. Run enrichment
python scripts/enrichment/enrich_disputes_batch.py

# 3. Validate
python scripts/maintenance/validate_dates.py

# 4. Regenerate visualizations
python scripts/visualization/regenerate_datawrapper_simple.py
python scripts/visualization/create_flourish_timeslider.py
```

### Process Manual Research
```bash
# After filling out search_query_worksheet.csv
python scripts/enrichment/process_worksheet_results.py
```

## Visualization Setup

### DataWrapper Timeline
1. Use [datawrapper_range_plot_simple.csv](data/derived/visualizations/datawrapper_range_plot_simple.csv)
2. Create "Range plot" in DataWrapper
3. Map columns:
   - Start: `start_date`
   - End: `end_date`
   - Label: `dispute_name`
   - Color: `outcome_status`

### Flourish Map
1. Use [disputes_map_ready.csv](data/derived/visualizations/disputes_map_ready.csv)
2. Create "Projection map"
3. Map columns:
   - Latitude: `system_hq_lat`
   - Longitude: `system_hq_lon`
   - Size: `patients_affected`
   - Color: `outcome_status`

### Flourish Time Animation
1. Use [disputes_flourish_timeslider.csv](data/derived/visualizations/disputes_flourish_timeslider.csv)
2. Has 20 quarter columns (2021 Q1 - 2025 Q4)
3. Enable time slider

## Data Flow

```
input/disputes_to_enrich.csv (seed)
         │
         ▼
    [Enrichment]
         │
         ▼
data/primary/disputes_enriched.csv ◄── CANONICAL (57 columns)
         │
         ├──► DataWrapper (datawrapper_range_plot_simple.csv)
         ├──► Flourish map (disputes_map_ready.csv)
         ├──► Flourish animation (disputes_flourish_timeslider.csv)
         └──► Airtable (disputes_enriched.json)
```

## Project Statistics (restoration baseline: 2026-08-30)

- **195 disputes** (2021–2025; was 203 before the 2026-01 duplicate cleanup)
- **57 data fields** per dispute
- **195 disputes** geocoded for mapping (all of them)
- **Outcome statuses in data:** Resolved (87), OON-Ongoing (74), OON-Permanent (34)
- **Top insurer families:** UnitedHealth Group, Humana, CVS Health/Aetna, Elevance

The records themselves were last substantively updated in January 2026. The restoration release preserves that baseline while the reviewed backfill proceeds; “generated on” dates must not be read as “all records researched on” dates.

## Release validation

```bash
python3 scripts/monthly_update/monthly_update.py rebuild
python3 scripts/maintenance/validate_release.py
cd site && npm ci && npm run build
```

The rebuild stages every derived artifact, validates the staged release, and only then replaces public files. A failure cannot leave a partially refreshed release.

## File Organization Principles

1. **One canonical CSV** - `disputes_enriched.csv` is the single source of truth
2. **Derived outputs** - All visualization files generated from canonical
3. **Archive old files** - Backups and one-time scripts in `archive/`
4. **Script organization** - By purpose (visualization, enrichment, maintenance)
5. **Clear documentation** - Each file type has a purpose documented

## Getting Help

- **Scripts:** See [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md)
- **Data fields:** See [SCHEMA.md](SCHEMA.md)
- **File purposes:** See [DATA_DICTIONARY.md](DATA_DICTIONARY.md)
- **Agent usage:** See [agent/SKILL.md](agent/SKILL.md)
