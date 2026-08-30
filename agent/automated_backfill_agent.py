#!/usr/bin/env python3
"""
Automated Backfill Agent for Payer-Provider Disputes

TWO-PHASE SEARCH STRATEGY:

Phase 1: DISCOVERY
- Run broad queries to find hospital + insurer pairs in disputes
- Extract: provider name, payer name, state, year
- Output: List of dispute pairs to investigate

Phase 2: RESOLUTION TRACKING
- For each discovered pair, search: "[Hospital]" "[Insurer]" contract
- Find EARLIEST article → First reported date
- Find MOST RECENT article → Current status (Resolved/OON-Ongoing/Settled)
- This catches disputes that were reported as ongoing but later resolved

STATUS CLASSIFICATION RULES:
========================
OON-Ongoing (active dispute with potential for resolution):
  - 2025 activity: news, negotiations, deadline extensions in current year
  - Explicit "negotiations continue" / "talks ongoing" language
  - Cooling-off periods or temporary extensions mentioned
  - Single insurer dropped (not categorical)

OON-Permanent (terminated relationship, no path back):
  - CATEGORICAL EXIT: Hospital dropped ALL MA plans (not just one insurer)
  - "Decision is final" / "not expected to return" language
  - 12+ months OON with NO news about negotiations
  - Hospital explicitly said "no contact to reconsider"
  - Multi-year stalemate (e.g., M Health Fairview-Humana OON since 2020)

Resolved:
  - Explicit agreement reached with date
  - "New contract" / "multi-year deal" language
  - Resolution date documented

DEFAULT RULE: If 12+ months old with no 2025 activity → OON-Permanent

Usage:
    python agent/automated_backfill_agent.py [--tier TIER] [--year YEAR] [--state STATE]
    python agent/automated_backfill_agent.py --phase discovery    # Just find disputes
    python agent/automated_backfill_agent.py --phase resolution   # Track known disputes

Examples:
    python agent/automated_backfill_agent.py                    # Run all tiers
    python agent/automated_backfill_agent.py --tier 1           # Just tier 1 states
    python agent/automated_backfill_agent.py --year 2022        # Just 2022
    python agent/automated_backfill_agent.py --phase resolution --input disputes.json

The agent outputs search queries that Claude Code should execute using WebSearch.
Results are collected and formatted for adding to disputes_to_enrich.csv.
"""

import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Import from backfill_search_queries
from backfill_search_queries import (
    PRIORITY_STATES,
    YEARS,
    REGIONAL_PAYERS_TO_SEARCH,
    STATE_NEWS_SOURCES,
    CONFLICT_PHRASES,
)


def generate_discovery_queries(
    tiers: Optional[List[int]] = None,
    years: Optional[List[int]] = None,
    states: Optional[List[str]] = None,
    max_queries: int = 50,
) -> List[Dict]:
    """
    PHASE 1: DISCOVERY

    Generate broad queries to find hospital + insurer pairs in disputes.
    These queries are designed to surface dispute pairs that we then
    investigate further in the resolution phase.

    Output: List of dispute pairs (provider, payer, state) to track.
    """
    queries = []

    # Filter states by tier if specified
    target_states = PRIORITY_STATES
    if tiers:
        target_states = [s for s in PRIORITY_STATES if s["priority"] in tiers]
    if states:
        states_upper = [s.upper() for s in states]
        target_states = [s for s in PRIORITY_STATES if s["state"] in states_upper]

    # Use specified years or default
    target_years = years if years else YEARS

    for state_info in target_states:
        state = state_info["state"]
        state_name = state_info["name"]
        priority = state_info["priority"]

        for year in target_years:
            # Query Type 1: Primary dispute query (comprehensive OR statement)
            # This is the main discovery query - catches most dispute reports
            queries.append({
                "query": f'{state_name} hospital insurance "contract dispute" OR "contract impasse" OR "failed negotiations" OR "stalled talks" {year}',
                "type": "discovery_primary",
                "state": state,
                "state_name": state_name,
                "year": year,
                "priority": priority,
                "phase": "discovery",
                "purpose": "Find hospital-insurer dispute pairs",
            })

            # Query Type 2: Out of network announcements (often first report)
            queries.append({
                "query": f'{state_name} hospital "out of network" OR "leaving network" insurer {year}',
                "type": "discovery_oon",
                "state": state,
                "state_name": state_name,
                "year": year,
                "priority": priority,
                "phase": "discovery",
                "purpose": "Find OON announcements that indicate disputes",
            })

            # Query Type 3: Accusation-based (both sides quoted)
            queries.append({
                "query": f'{state_name} hospital insurer accuses OR "underpaid" OR "excessive rates" OR "denied claims" {year}',
                "type": "discovery_accusations",
                "state": state,
                "state_name": state_name,
                "year": year,
                "priority": priority + 1,
                "phase": "discovery",
                "purpose": "Find disputes with public accusations",
            })

        # Regional payer discovery (spans all years)
        if state in REGIONAL_PAYERS_TO_SEARCH:
            for payer in REGIONAL_PAYERS_TO_SEARCH[state][:1]:
                queries.append({
                    "query": f'"{payer}" hospital "contract dispute" OR "out of network" OR "impasse"',
                    "type": "discovery_regional_payer",
                    "state": state,
                    "state_name": state_name,
                    "payer": payer,
                    "year": "all",
                    "priority": priority,
                    "phase": "discovery",
                    "purpose": f"Find disputes involving {payer}",
                })

    # Sort by priority
    queries.sort(key=lambda x: (x["priority"], x.get("year", 9999) if isinstance(x.get("year"), int) else 9999))

    if len(queries) > max_queries:
        queries = queries[:max_queries]

    return queries


def generate_resolution_queries(dispute_pairs: List[Dict]) -> List[Dict]:
    """
    PHASE 2: RESOLUTION TRACKING

    For each discovered dispute pair, generate queries to find:
    1. EARLIEST article → First reported date
    2. MOST RECENT article → Current status

    Input: List of dicts with 'provider' and 'payer' keys
    Output: Queries to search for each pair's timeline

    Example input:
    [
        {"provider": "UMass Memorial Health", "payer": "Blue Cross Blue Shield", "state": "MA"},
        {"provider": "Hartford HealthCare", "payer": "Cigna", "state": "CT"},
    ]
    """
    queries = []

    for pair in dispute_pairs:
        provider = pair.get("provider", "")
        payer = pair.get("payer", "")
        state = pair.get("state", "")

        if not provider or not payer:
            continue

        # Clean up payer name (remove parent company in parens)
        payer_clean = payer.split("(")[0].strip() if "(" in payer else payer

        # Query 1: General search for this pair (will show most recent first by default)
        queries.append({
            "query": f'"{provider}" "{payer_clean}" contract',
            "type": "resolution_timeline",
            "provider": provider,
            "payer": payer,
            "state": state,
            "phase": "resolution",
            "purpose": "Find all articles about this dispute pair",
            "instructions": "Look at MOST RECENT article for current status, EARLIEST for first reported date",
        })

        # Query 2: Explicit resolution search
        queries.append({
            "query": f'"{provider}" "{payer_clean}" "reach agreement" OR "resolved" OR "new contract" OR "signed"',
            "type": "resolution_outcome",
            "provider": provider,
            "payer": payer,
            "state": state,
            "phase": "resolution",
            "purpose": "Find resolution/settlement articles specifically",
            "instructions": "If found, update status to Resolved with resolution date",
        })

    return queries


def generate_targeted_queries(
    tiers: Optional[List[int]] = None,
    years: Optional[List[int]] = None,
    states: Optional[List[str]] = None,
    max_queries: int = 50,
    phase: str = "discovery",
) -> List[Dict]:
    """
    Main entry point - generates queries based on phase.

    phase="discovery" - Find new dispute pairs
    phase="all" - Both discovery and basic resolution queries
    """
    if phase == "discovery":
        return generate_discovery_queries(tiers, years, states, max_queries)
    else:
        # Default to discovery queries
        return generate_discovery_queries(tiers, years, states, max_queries)


def format_for_claude_code(queries: List[Dict], phase: str = "discovery") -> str:
    """
    Format queries as instructions for Claude Code to execute.
    """
    output = []
    output.append("=" * 70)

    if phase == "discovery":
        output.append("PHASE 1: DISCOVERY - Find Dispute Pairs")
        output.append("=" * 70)
        output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        output.append(f"Total queries: {len(queries)}")
        output.append("")
        output.append("GOAL: Find hospital + insurer pairs involved in disputes")
        output.append("")
        output.append("FOR EACH SEARCH RESULT:")
        output.append("1. Extract: Provider name, Payer name, State")
        output.append("2. Note if it looks like a real DISPUTE (both sides quoted, accusations)")
        output.append("3. Skip routine network exits without conflict")
        output.append("4. Save dispute pairs for Phase 2 resolution tracking")
        output.append("")
        output.append("DISPUTE SIGNALS (need at least 2):")
        output.append("- Both sides made public statements")
        output.append("- Accusations (underpaid, excessive rates, denied claims)")
        output.append("- Impasse/failed negotiations language")
        output.append("- Patient impact with deadline threats")
    elif phase == "resolution":
        output.append("PHASE 2: RESOLUTION TRACKING - Get Status Updates")
        output.append("=" * 70)
        output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        output.append(f"Total queries: {len(queries)}")
        output.append("")
        output.append("GOAL: For each dispute pair, find current status")
        output.append("")
        output.append("FOR EACH SEARCH:")
        output.append("1. Find EARLIEST article → First reported date")
        output.append("2. Find MOST RECENT article → Current status")
        output.append("3. Classify status using rules below")
        output.append("")
        output.append("STATUS CLASSIFICATION RULES:")
        output.append("-" * 40)
        output.append("OON-Ongoing (use ONLY if):")
        output.append("  • 2025 activity (news, negotiations, extensions)")
        output.append("  • 'Negotiations continue' / 'talks ongoing' language")
        output.append("  • Single insurer dropped (not categorical)")
        output.append("")
        output.append("OON-Permanent (use if):")
        output.append("  • CATEGORICAL EXIT: Dropped ALL MA plans")
        output.append("  • 12+ months old with NO 2025 activity")
        output.append("  • 'Decision is final' language")
        output.append("  • 'No contact to reconsider' language")
        output.append("")
        output.append("Resolved:")
        output.append("  • Agreement reached with documented date")
        output.append("  • 'New contract' / 'multi-year deal' language")
        output.append("")
        output.append("DEFAULT: 12+ months + no 2025 news → OON-Permanent")
    else:
        output.append("AUTOMATED BACKFILL SEARCH INSTRUCTIONS")
        output.append("=" * 70)
        output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        output.append(f"Total queries: {len(queries)}")

    output.append("")
    output.append("=" * 70)
    output.append("QUERIES TO EXECUTE")
    output.append("=" * 70)

    # Group by state (for discovery) or by provider (for resolution)
    if phase == "resolution":
        # For resolution, group by provider
        for i, q in enumerate(queries, 1):
            provider = q.get('provider', 'Unknown')
            payer = q.get('payer', 'Unknown')
            state = q.get('state', '')
            output.append(f"\n[{i}] {provider} vs {payer} ({state})")
            output.append(f"    Query: {q['query']}")
            output.append(f"    Type: {q['type']}")
            if q.get('instructions'):
                output.append(f"    → {q['instructions']}")
            output.append("")
    else:
        # For discovery, group by state
        by_state = {}
        for q in queries:
            state = q.get("state", "Unknown")
            if state not in by_state:
                by_state[state] = []
            by_state[state].append(q)

        for state in sorted(by_state.keys()):
            state_queries = by_state[state]
            state_name = state_queries[0].get("state_name", state)
            output.append(f"\n### {state_name} ({state}) ###\n")

            for i, q in enumerate(state_queries, 1):
                output.append(f"[{state}-{i}] {q['query']}")
                year_str = q.get('year', 'N/A')
                query_phase = q.get('phase', 'unknown')
                output.append(f"      Type: {q['type']} | Year: {year_str} | Phase: {query_phase}")
                output.append("")

    return "\n".join(output)


def generate_claude_code_script(queries: List[Dict]) -> str:
    """
    Generate a script that Claude Code can execute to run all searches.
    This outputs the queries in a format ready for batch execution.
    """
    script = []
    script.append("# Batch search queries for Claude Code")
    script.append("# Run each of these as WebSearch queries")
    script.append("")
    script.append("QUERIES = [")
    for q in queries:
        script.append(f'    "{q["query"]}",  # {q["state"]} {q["year"]}')
    script.append("]")
    script.append("")
    script.append("# Expected output format for each finding:")
    script.append("# {")
    script.append("#     'provider': 'Health System Name',")
    script.append("#     'payer': 'Insurance Company (Parent)',")
    script.append("#     'state': 'XX',")
    script.append("#     'year': 2024,")
    script.append("#     'quarter': 'Q1',")
    script.append("#     'status': 'Resolved|OON-Ongoing',")
    script.append("#     'source': 'Publication Name',")
    script.append("#     'patients_affected': 50000,")
    script.append("#     'notes': 'Key details about the dispute'")
    script.append("# }")

    return "\n".join(script)


def load_disputes_from_csv(csv_path: str) -> List[Dict]:
    """
    Load existing disputes from CSV to generate resolution queries.
    Filters to OON-Ongoing disputes that need status updates.
    """
    import csv

    disputes = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle both old and new column name formats
            status = row.get('outcome_status', row.get('status', ''))
            provider = row.get('system_name', row.get('provider', ''))
            payer = row.get('insurer_name', row.get('payer', ''))
            state = row.get('state', '')
            year = row.get('year_first_reported', row.get('year', ''))

            # Focus on disputes that might need resolution updates
            if status in ['OON-Ongoing', 'Unknown', '']:
                disputes.append({
                    'provider': provider,
                    'payer': payer,
                    'state': state,
                    'year': year,
                    'current_status': status,
                })
    return disputes


def main():
    parser = argparse.ArgumentParser(description="Generate backfill search queries")
    parser.add_argument("--tier", type=int, help="Only include states from this tier (1-5)")
    parser.add_argument("--tiers", type=str, help="Comma-separated tiers (e.g., '1,2,3')")
    parser.add_argument("--year", type=int, help="Only search this year")
    parser.add_argument("--years", type=str, help="Comma-separated years (e.g., '2022,2023')")
    parser.add_argument("--state", type=str, help="Comma-separated states (e.g., 'CA,TX,FL')")
    parser.add_argument("--max", type=int, default=50, help="Max queries to generate")
    parser.add_argument("--format", choices=["instructions", "script", "json"],
                       default="instructions", help="Output format")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--phase", choices=["discovery", "resolution"],
                       default="discovery", help="Search phase: discovery (find pairs) or resolution (track status)")
    parser.add_argument("--input", type=str, help="Input CSV for resolution phase (disputes_to_enrich.csv)")

    args = parser.parse_args()

    # Parse arguments
    tiers = None
    if args.tier:
        tiers = [args.tier]
    elif args.tiers:
        tiers = [int(t.strip()) for t in args.tiers.split(",")]

    years = None
    if args.year:
        years = [args.year]
    elif args.years:
        years = [int(y.strip()) for y in args.years.split(",")]

    states = None
    if args.state:
        states = [s.strip() for s in args.state.split(",")]

    # Generate queries based on phase
    if args.phase == "resolution":
        # Load dispute pairs from CSV or JSON
        if args.input:
            if args.input.endswith('.csv'):
                dispute_pairs = load_disputes_from_csv(args.input)
            else:
                with open(args.input) as f:
                    dispute_pairs = json.load(f)
        else:
            # Default to disputes_to_enrich.csv
            default_csv = Path(__file__).parent.parent / "input" / "disputes_to_enrich.csv"
            if default_csv.exists():
                dispute_pairs = load_disputes_from_csv(str(default_csv))
            else:
                print("Error: No input file specified for resolution phase")
                print("Use --input to specify a CSV or JSON file with dispute pairs")
                return

        # Filter by state if specified
        if states:
            states_upper = [s.upper() for s in states]
            dispute_pairs = [d for d in dispute_pairs if d.get('state', '').upper() in states_upper]

        queries = generate_resolution_queries(dispute_pairs)
        if args.max and len(queries) > args.max:
            queries = queries[:args.max]
    else:
        # Discovery phase
        queries = generate_targeted_queries(
            tiers=tiers,
            years=years,
            states=states,
            max_queries=args.max,
            phase="discovery",
        )

    # Format output
    if args.format == "instructions":
        output = format_for_claude_code(queries, phase=args.phase)
    elif args.format == "script":
        output = generate_claude_code_script(queries)
    elif args.format == "json":
        output = json.dumps(queries, indent=2)

    # Write or print
    if args.output:
        Path(args.output).write_text(output)
        print(f"Written to: {args.output}")
    else:
        print(output)

    # Summary
    print(f"\n{'='*70}")
    print(f"PHASE: {args.phase.upper()}")
    print(f"Generated {len(queries)} queries")
    if args.phase == "discovery":
        if tiers:
            print(f"Tiers: {tiers}")
        if years:
            print(f"Years: {years}")
        if states:
            print(f"States: {states}")
    else:
        print(f"Tracking {len(queries)//2} dispute pairs for resolution status")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
