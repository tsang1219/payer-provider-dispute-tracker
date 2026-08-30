# Contributing corrections and cases

Corrections, missing disputes, better sources, and methodological improvements are welcome.

## The easiest route

Open an issue with:

- the provider and insurer;
- the disputed fact or missing case;
- a public source URL;
- the date you accessed it; and
- the proposed correction.

## Pull requests

Changes to `data/primary/disputes_enriched.csv` should preserve its 57-column schema and include a source for every factual change. Do not edit generated files by hand. After changing canonical data, run:

```bash
python3 scripts/monthly_update/monthly_update.py rebuild
python3 scripts/maintenance/validate_release.py
cd site && npm ci && npm run build
```

Automated discovery may open candidate pull requests, but a maintainer reviews evidence before canonical data changes.

