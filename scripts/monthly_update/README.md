# Monthly update job

`monthly_update.py` keeps the dispute tracker current. Stdlib-only Python (3.9+),
no API keys — discovery runs on Google News RSS. The canonical CSV
(`data/primary/disputes_enriched.csv`) is never written without a human approval
step and a timestamped backup.

## The loop

```
┌─ monthly (automated, safe — never touches canonical) ─────────────┐
│  python3 scripts/monthly_update/monthly_update.py run             │
│    discover → review/candidates_YYYY-MM.csv   (new standoffs)     │
│    status   → review/status_check_YYYY-MM.csv (ongoing re-checks) │
│    rebuild  → site JSON + DataWrapper/Flourish/map exports        │
└───────────────────────────────────────────────────────────────────┘
                 │
                 ▼  Andrew (or a Claude session) reviews the two CSVs:
                    · candidates: open each url, fill the canonical columns
                      (system_name, state, insurer_name, first_media_date,
                      outcome_status, hq lat/lon for the map …), set approve=YES
                    · status_check: verify the linked coverage, set approve=YES
                      + new_status (+ resolution_date & source if Resolved)
                 │
                 ▼
┌─ apply (the only path into canonical) ────────────────────────────┐
│  python3 scripts/monthly_update/monthly_update.py apply           │
│    validates every approved row (status enum, dates, state codes, │
│    duplicate guard) — refuses bad rows with reasons               │
│    backs up canonical → data/primary/*.backup_TIMESTAMP           │
│    appends new disputes / updates statuses → rebuilds everything  │
└───────────────────────────────────────────────────────────────────┘
                 │
                 ▼
       cd site && npm run build     → deploy dist/ (see DEPLOY.md)
```

### Integrity rules baked in

- Discovery **stages** candidates with their source URL; every canonical field
  the job can't read from the source is left blank — never guessed.
- `apply` only accepts rows marked `approve=YES`, validates them, and skips
  anything that matches an already-tracked dispute (`matches_existing_id`).
- Every canonical write is preceded by a timestamped backup next to the CSV.
- `review/seen_items.json` remembers every headline ever staged, so re-runs
  don't re-surface the same items.

### Commands

| Command | What it does | Touches canonical? |
|---|---|---|
| `run` | discover + status + rebuild (the cron entry) | **No** |
| `discover [--days 45]` | stage new-dispute candidates from news | No |
| `status [--days 60] [--limit N]` | re-check every OON-Ongoing dispute for news | No |
| `apply [--month YYYY-MM]` | merge approved review rows | **Yes** (backup first) |
| `rebuild` | regenerate site JSON + viz exports | No (reads it) |

`status` fetches one RSS query per ongoing dispute (~75 requests at ~1.2 s
spacing — a couple of minutes). Rows flagged `possible-resolution` sort to the
top of the review file.

### Claude-assisted review (optional but recommended)

The review gate is designed so a Claude Code session can do the legwork:
*"Open `review/candidates_2026-08.csv`, visit each URL, fill the canonical
columns from the article, and leave `approve` blank for me."* Andrew then
scans the pre-filled sheet, flips `approve` to YES on the real ones, and runs
`apply`. The human approval column is the gate; the agent never sets it.

## Scheduling

The public repository runs lightweight discovery weekly and status review monthly through `.github/workflows/`. Both create review pull requests; neither writes canonical data.

For a local-only installation, pick one of the options below.

Pick one:

**launchd (this Mac, recommended — matches the AIOS pattern).** Save as
`~/Library/LaunchAgents/com.hiop.dispute-tracker-monthly.plist`, then
`launchctl load` it:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.hiop.dispute-tracker-monthly</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string>
    <string>/Users/all/ai_os/projects/payer_provider_disputes/scripts/monthly_update/monthly_update.py</string>
    <string>run</string>
  </array>
  <key>StartCalendarInterval</key><dict>
    <key>Day</key><integer>1</integer>
    <key>Hour</key><integer>7</integer>
    <key>Minute</key><integer>30</integer>
  </dict>
  <key>StandardOutPath</key><string>/Users/all/ai_os/projects/payer_provider_disputes/review/last_run.log</string>
  <key>StandardErrorPath</key><string>/Users/all/ai_os/projects/payer_provider_disputes/review/last_run.log</string>
</dict></plist>
```

Then a `review the dispute-tracker candidates` item lands naturally in the
monthly rhythm (the log + the two dated CSVs in `review/` are the artifact).

**cron equivalent:**

```
30 7 1 * * /usr/bin/python3 /Users/all/ai_os/projects/payer_provider_disputes/scripts/monthly_update/monthly_update.py run >> /Users/all/ai_os/projects/payer_provider_disputes/review/last_run.log 2>&1
```

**GitHub Action** (if the repo moves to GitHub): monthly `schedule:` workflow
that runs `run` and opens a PR with the `review/` diffs — the PR review *is*
the approval gate, and `apply` runs after merge. Sketch:

```yaml
on:
  schedule: [{cron: "30 12 1 * *"}]
jobs:
  sweep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python3 scripts/monthly_update/monthly_update.py run
      - uses: peter-evans/create-pull-request@v6
        with: {title: "Monthly dispute sweep", branch: monthly-sweep}
```

## After `apply`: shipping the refreshed site

```
cd site && npm run build        # bundles the regenerated JSON
# deploy dist/ — one step, see ../../DEPLOY.md
```
