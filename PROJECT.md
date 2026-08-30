# Payer–Provider Dispute Tracker

A public, independently maintained record of U.S. hospital–insurer contract disputes. The project combines a canonical dataset, a static interactive tracker, and a human-reviewed update pipeline.

## Goal

Restore and publish the existing tracker as a useful public asset. The first release does not need to claim perfect or comprehensive coverage; it must make its scope, estimates, sources, and correction process legible.

## Production sequence

1. Restore a reproducible, validated release pipeline.
2. Publish the canonical data, methodology, and tracker through a public GitHub repository and deployed site.
3. Re-promote the original analysis with refreshed findings and visuals.
4. Develop a distinct Health Affairs article only after the refreshed longitudinal data supports a defensible new finding.

## Operating principles

- `data/primary/disputes_enriched.csv` is canonical.
- Automation discovers and stages evidence; a human approves canonical changes.
- A release may contain known limitations, but those limitations must be explicit.
- Corrections are expected and welcomed through a documented public process.
- Derived files are generated, never hand-maintained.
- A failed rebuild must not leave a partially refreshed release.

## Roles and gates

- **Andrew:** approves additions and status changes; decides what findings to promote; owns article judgment and voice.
- **Agents/automation:** discover candidates, assemble evidence, validate structure, regenerate artifacts, and prepare releases.
- **Release gate:** validation and production site build must both pass before deployment.

## Current state

- **Stage:** restoration
- **Canonical records:** 195
- **Immediate next action:** establish a green local release from the existing canonical dataset.
- **Public release:** pending repository and deployment validation.

## Routing

- Canonical data: `data/primary/disputes_enriched.csv`
- Review queue: `review/`
- Update pipeline: `scripts/monthly_update/`
- Release validation: `scripts/maintenance/validate_release.py`
- Web application: `site/`
- Methodology and public orientation: `README.md`, `SCHEMA.md`, `METHODOLOGY.md`

