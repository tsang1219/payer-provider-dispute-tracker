# Seed Prompt — Payer-Provider Disputes: the living dataset (for Fable)

*Andrew Tsang / Health Is Other People. Build brief for a Fable agent running autonomously. Andrew reviews output; he is not the dev. Make strong calls where this leaves room.*

---

## The strategic goal

Andrew has spent his career inside the $217B payer-provider fight. He's built a real dataset of public hospital-insurer contract disputes. The goal isn't "a chart" — it's a **proprietary, self-maintaining dataset that other people come to**: a living authority on payer-provider standoffs that raises the credibility of healthisotherpeople.com. Think of it as *the* public tracker for these fights, hosted on his own turf and updated on a schedule so it stays current without manual work.

Three pieces, in priority order: **(1) a hosted interactive view** of the dataset, **(2) a monthly update job** that keeps it current, **(3) clean deployment** to a standalone subdomain.

---

## What exists (source of truth)

- **Canonical dataset:** `data/primary/disputes_enriched.csv` — **203 disputes, 57 fields**, 2021–2025. THE source of truth. Everything derives from it.
- **Schema:** `SCHEMA.md` (all 57 fields documented). Read it first.
- **Geocoded subset:** `data/derived/visualizations/disputes_map_ready.csv` (82 records with lat/lon).
- **Existing viz exports** (for reference, not the endpoint): DataWrapper range plot + Flourish map/timeslider CSVs under `data/derived/visualizations/`. Existing enrichment pipeline in `scripts/enrichment/` and research agents in `agent/`.
- Top insurers in the data: UnitedHealthcare, Anthem/Elevance, Aetna. Mean field completeness ~0.77.

---

## Build (1): the hosted interactive view

A **standalone, deployable web app** (React + TypeScript + Vite + Tailwind, pure static build reading the dataset as bundled JSON — match the deploy pattern of Andrew's other tools). It should present the 203 disputes as a genuine exploration tool, not a static dashboard:

- **Interactive map** — the disputes geolocated; click a dispute for its detail (parties, dates, patients affected, outcome, status). "Maps that *do stuff*" — filtering, zoom, hover detail, not a flat image.
- **Timeline** — disputes over 2021–2025 with duration ranges; who's fighting whom, how long standoffs last, how they resolved.
- **Filters** — by insurer, health system, state, outcome status, year.
- **A "state of the fight" summary** — headline numbers (active disputes, patients affected, longest-running standoffs) that update from the data.
- Aesthetic: HIOP editorial-calm (serif headings, clean sans, generous whitespace, "holds up to a 30-second and a 30-minute look"). Mobile-respectable — it'll be opened from LinkedIn.

## Build (2): the monthly update job

A runnable job (Node or Python script) that keeps the dataset current, designed to run on a **monthly schedule**:

- **Discover new disputes** — search news/public sources for payer-provider contract standoffs not yet in the dataset, extract them into the 57-field schema (reuse/extend the existing enrichment pipeline in `scripts/` and `agent/`). This is the research-agent half — build it to **stage candidates for a human review gate**, not to write directly to canonical (Andrew must be able to approve additions).
- **Update status** on existing disputes — re-check the 203 for resolution/escalation/status changes and update their fields.
- Output: an updated `disputes_enriched.csv` (via the review gate) → regenerated site data + regenerated DataWrapper/Flourish exports.
- Deliver the job as a script + a short **"how to schedule this monthly"** note (cron / launchd / GitHub Action). Do NOT attempt to stand up live infrastructure or deploy DNS yourself — scaffold it and hand the deployment step to Andrew.

## Build (3): deployment target

Proposed standalone subdomain (e.g. `disputes.healthisotherpeople.com`). Produce a static build ready to deploy; document the one deploy step. Confirm the exact subdomain with Andrew at review.

---

## Constraints

- **Data integrity is everything.** This is a credibility asset with Andrew's name on it. Every figure traces to the dataset. The discovery job must not fabricate or guess disputes — unverified candidates go to the review gate, flagged with sources.
- **The dataset stays canonical in the repo CSV** (Andrew confirmed). If an Airtable mirror is wanted later, that's a phase-2 export, not the source of truth.
- **You cannot verify the live site by eye in a headless run** — build it correctly, document how to run it locally (`npm run dev`) and what Andrew should check.

## Deliverable & review

A running static app + the update job + a short note covering: what you built, the schema/data decisions you made, how the monthly job works and how to schedule it, and the one deploy step. Flag anything you were unsure about for Andrew's call.
