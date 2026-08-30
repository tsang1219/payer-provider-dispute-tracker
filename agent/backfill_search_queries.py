#!/usr/bin/env python3
"""
Backfill Search Query Generator

Generates efficient search queries to find payer-provider DISPUTES (not just
network changes) that were publicly reported but missed in the original dataset.

FOCUS: Public conflicts between payers and providers, NOT:
- Routine network exits
- Product discontinuations
- Unilateral business decisions

What qualifies as a DISPUTE:
- Both sides made public statements about the conflict
- Negotiations failed or reached impasse
- Accusations made (underpayment, excessive rates, prior auth abuse)
- Deadline threats with public patient notification
- Rate demands publicly disclosed

Strategy:
1. Use CONFLICT language (dispute, impasse, failed, accuses, demands)
2. Search for negotiation breakdowns with patient impact
3. Look for articles where both sides are quoted
4. Focus on regional news that covers the conflict angle

This approach finds actual disputes, not just network changes.
"""

import json
from datetime import datetime
from typing import List, Dict

# States to backfill - prioritize underrepresented ones
PRIORITY_STATES = [
    # Tier 1: Major healthcare markets with low coverage
    {"state": "MA", "name": "Massachusetts", "priority": 1, "reason": "Major market"},
    {"state": "IL", "name": "Illinois", "priority": 1, "reason": "Major market"},
    {"state": "NJ", "name": "New Jersey", "priority": 1, "reason": "Major market"},
    {"state": "CT", "name": "Connecticut", "priority": 1, "reason": "Near major markets"},

    # Tier 2: Large states that may have missed regional disputes
    {"state": "NY", "name": "New York", "priority": 2, "reason": "Large market"},
    {"state": "PA", "name": "Pennsylvania", "priority": 2, "reason": "Large market, regional payers"},
    {"state": "OH", "name": "Ohio", "priority": 2, "reason": "Large market, regional payers"},
    {"state": "MI", "name": "Michigan", "priority": 2, "reason": "Large market, regional payers"},
    {"state": "FL", "name": "Florida", "priority": 2, "reason": "Large market, MA heavy"},
    {"state": "TX", "name": "Texas", "priority": 2, "reason": "Large market"},

    # Tier 3: Regional/smaller states
    {"state": "WI", "name": "Wisconsin", "priority": 3, "reason": "Regional payers"},
    {"state": "IN", "name": "Indiana", "priority": 3, "reason": "Regional payers"},
    {"state": "MD", "name": "Maryland", "priority": 3, "reason": "Near DC, regional market"},
    {"state": "RI", "name": "Rhode Island", "priority": 3, "reason": "Small state"},
    {"state": "NH", "name": "New Hampshire", "priority": 3, "reason": "Regional market"},
    {"state": "VT", "name": "Vermont", "priority": 3, "reason": "Small state"},
    {"state": "ME", "name": "Maine", "priority": 3, "reason": "Regional market"},
    {"state": "MN", "name": "Minnesota", "priority": 3, "reason": "Regional payers"},
    {"state": "MO", "name": "Missouri", "priority": 3, "reason": "Regional market"},
    {"state": "KY", "name": "Kentucky", "priority": 3, "reason": "Regional market"},
    {"state": "TN", "name": "Tennessee", "priority": 3, "reason": "Regional market"},
    {"state": "NC", "name": "North Carolina", "priority": 3, "reason": "Large market"},
    {"state": "GA", "name": "Georgia", "priority": 3, "reason": "Large market"},
    {"state": "VA", "name": "Virginia", "priority": 3, "reason": "Regional market"},
    {"state": "SC", "name": "South Carolina", "priority": 3, "reason": "Regional market"},
    {"state": "AL", "name": "Alabama", "priority": 3, "reason": "Regional market"},

    # Tier 4: Western/Rocky Mountain states (underrepresented)
    {"state": "CO", "name": "Colorado", "priority": 4, "reason": "Western market"},
    {"state": "AZ", "name": "Arizona", "priority": 4, "reason": "Western market"},
    {"state": "UT", "name": "Utah", "priority": 4, "reason": "Western market"},
    {"state": "NV", "name": "Nevada", "priority": 4, "reason": "Western market"},
    {"state": "OR", "name": "Oregon", "priority": 4, "reason": "Pacific Northwest"},
    {"state": "WA", "name": "Washington", "priority": 4, "reason": "Pacific Northwest"},
    {"state": "NM", "name": "New Mexico", "priority": 4, "reason": "Western market"},
    {"state": "ID", "name": "Idaho", "priority": 4, "reason": "Rural western"},
    {"state": "MT", "name": "Montana", "priority": 4, "reason": "Rural western"},
    {"state": "WY", "name": "Wyoming", "priority": 4, "reason": "Rural western"},
    {"state": "AK", "name": "Alaska", "priority": 4, "reason": "Remote state"},
    {"state": "HI", "name": "Hawaii", "priority": 4, "reason": "Island state"},

    # Tier 5: Additional states for completeness
    {"state": "IA", "name": "Iowa", "priority": 5, "reason": "Midwest"},
    {"state": "KS", "name": "Kansas", "priority": 5, "reason": "Midwest"},
    {"state": "NE", "name": "Nebraska", "priority": 5, "reason": "Midwest"},
    {"state": "SD", "name": "South Dakota", "priority": 5, "reason": "Rural"},
    {"state": "ND", "name": "North Dakota", "priority": 5, "reason": "Rural"},
    {"state": "OK", "name": "Oklahoma", "priority": 5, "reason": "Regional"},
    {"state": "AR", "name": "Arkansas", "priority": 5, "reason": "Regional"},
    {"state": "LA", "name": "Louisiana", "priority": 5, "reason": "Regional"},
    {"state": "MS", "name": "Mississippi", "priority": 5, "reason": "Regional"},
    {"state": "WV", "name": "West Virginia", "priority": 5, "reason": "Regional"},
    {"state": "DE", "name": "Delaware", "priority": 5, "reason": "Small state"},
    {"state": "DC", "name": "District of Columbia", "priority": 5, "reason": "Metro area"},
]

# Years to search - expanded to capture historical disputes
YEARS = [2025, 2024, 2023, 2022, 2021, 2020]  # Most recent first

# Regional news sources by state (for site-specific searches)
STATE_NEWS_SOURCES = {
    "MA": ["bostonglobe.com", "telegram.com", "masslive.com", "wbur.org"],
    "IL": ["chicagotribune.com", "suntimes.com", "dailyherald.com"],
    "NJ": ["nj.com", "northjersey.com", "app.com"],
    "CT": ["courant.com", "ctpost.com", "ctmirror.org"],
    "NY": ["timesunion.com", "buffalonews.com", "democratandchronicle.com", "newsday.com"],
    "PA": ["inquirer.com", "post-gazette.com", "pennlive.com", "mcall.com"],
    "OH": ["cleveland.com", "dispatch.com", "daytondailynews.com", "cincinnati.com"],
    "MI": ["freep.com", "detroitnews.com", "mlive.com"],
    "WI": ["jsonline.com", "madison.com"],
    "IN": ["indystar.com", "southbendtribune.com"],
    "MD": ["baltimoresun.com"],
    "RI": ["providencejournal.com"],
    "NH": ["unionleader.com", "nhpr.org"],
    "VT": ["burlingtonfreepress.com", "vtdigger.org"],
    "ME": ["pressherald.com", "bangordailynews.com"],
}

# Regional payers most likely to have missed disputes
REGIONAL_PAYERS_TO_SEARCH = {
    "MA": ["Blue Cross Blue Shield of Massachusetts", "Tufts Health Plan", "Harvard Pilgrim", "Point32Health"],
    "IL": ["Blue Cross Blue Shield of Illinois", "Health Care Service Corporation"],
    "NJ": ["Horizon Blue Cross Blue Shield", "AmeriHealth"],
    "CT": ["ConnectiCare", "Anthem Connecticut"],
    "NY": ["Healthfirst", "EmblemHealth", "Fidelis Care", "MVP Health Care", "Excellus"],
    "PA": ["Highmark", "Independence Blue Cross", "UPMC Health Plan", "Geisinger Health Plan"],
    "OH": ["Medical Mutual", "CareSource", "SummaCare"],
    "MI": ["Blue Cross Blue Shield of Michigan", "Priority Health", "HAP"],
    "WI": ["Group Health Cooperative", "Quartz"],
    "IN": ["Anthem Indiana", "MDwise"],
    "MD": ["CareFirst"],
    "RI": ["Blue Cross Blue Shield of Rhode Island"],
}


# CONFLICT indicators - language that signals actual disputes, not just network changes
CONFLICT_PHRASES = [
    "contract dispute",
    "failed negotiations",
    "negotiations failed",
    "impasse",
    "stalled talks",
    "accuses",
    "accused",
    "underpaid",
    "underpayment",
    "denials",
    "denial rates",
    "prior authorization",
    "reimbursement rates",
    "rate increase",
    "demands",
    "patients caught",
    "patients scrambling",
    "deadline looms",
]

# Words that indicate BOTH SIDES are engaged (not unilateral)
BILATERAL_INDICATORS = [
    "both sides",
    "hospital says",
    "insurer says",
    "responded",
    "countered",
    "rejected",
    "refuses",
]

# Exclude these - signs of routine changes, not disputes
EXCLUSION_SIGNALS = [
    "exiting market",
    "discontinuing",
    "no longer offering",
    "product change",
    "plan change",
]


def generate_backfill_queries(
    states: List[str] = None,
    years: List[int] = None,
    include_google_news: bool = True
) -> List[Dict]:
    """
    Generate queries focused on finding actual DISPUTES (conflicts), not network changes.

    Returns queries designed to find disputes where:
    - Both sides made public statements
    - Negotiations failed or reached impasse
    - Accusations were made publicly
    - Patients were caught in the middle
    """
    if states is None:
        states = [s["state"] for s in PRIORITY_STATES]
    if years is None:
        years = YEARS

    queries = []

    for state_info in PRIORITY_STATES:
        state = state_info["state"]
        state_name = state_info["name"]
        priority = state_info["priority"]

        if state not in states:
            continue

        for year in years:
            # Query Type 1: Contract DISPUTE (primary - best signal)
            queries.append({
                "query": f'{state_name} hospital insurance "contract dispute" {year}',
                "type": "dispute_primary",
                "state": state,
                "year": year,
                "priority": priority,
                "expected_results": "Direct dispute coverage",
            })

            # Query Type 2: Failed negotiations / impasse
            queries.append({
                "query": f'{state_name} hospital insurer "failed negotiations" OR "impasse" OR "stalled" {year}',
                "type": "failed_negotiations",
                "state": state,
                "year": year,
                "priority": priority,
                "expected_results": "Negotiation breakdowns",
            })

            # Query Type 3: Accusations (underpayment, denial rates)
            queries.append({
                "query": f'{state_name} hospital accuses insurer OR "underpaid" OR "denial rates" {year}',
                "type": "accusations",
                "state": state,
                "year": year,
                "priority": priority,
                "expected_results": "Public accusations",
            })

            # Query Type 4: Deadline threats with patient impact
            queries.append({
                "query": f'{state_name} hospital insurance deadline patients "lose coverage" OR "scrambling" {year}',
                "type": "deadline_threat",
                "state": state,
                "year": year,
                "priority": priority,
                "expected_results": "Deadline-driven disputes",
            })

            # Query Type 5: Rate dispute language
            queries.append({
                "query": f'{state_name} hospital "reimbursement rates" OR "rate increase" insurer dispute {year}',
                "type": "rate_dispute",
                "state": state,
                "year": year,
                "priority": priority + 1,
                "expected_results": "Rate-focused disputes",
            })

            # Query Type 6: Regional news with dispute focus
            if state in STATE_NEWS_SOURCES:
                sites = STATE_NEWS_SOURCES[state][:2]
                site_query = " OR ".join([f"site:{s}" for s in sites])
                queries.append({
                    "query": f'({site_query}) hospital insurance dispute OR impasse {year}',
                    "type": "regional_news_dispute",
                    "state": state,
                    "year": year,
                    "priority": priority,
                    "sources": sites,
                    "expected_results": "Local dispute coverage",
                })

        # Query Type 7: Regional payer disputes
        if state in REGIONAL_PAYERS_TO_SEARCH:
            for payer in REGIONAL_PAYERS_TO_SEARCH[state][:2]:
                queries.append({
                    "query": f'"{payer}" hospital "contract dispute" OR "failed" OR accuses 2024 OR 2025',
                    "type": "regional_payer_dispute",
                    "state": state,
                    "payer": payer,
                    "year": "2024-2025",
                    "priority": priority,
                    "expected_results": f"Disputes with {payer}",
                })

    return queries


def generate_quick_backfill(states: List[str] = None) -> List[Dict]:
    """
    Generate a minimal set of CONFLICT-focused queries for quick backfill.
    ~15-20 queries total, focused on actual disputes (not network changes).
    """
    if states is None:
        # Just tier 1 states
        states = ["MA", "IL", "NJ", "CT"]

    queries = []

    for state_info in PRIORITY_STATES:
        state = state_info["state"]
        state_name = state_info["name"]

        if state not in states:
            continue

        # Query 1: Contract dispute (best signal)
        queries.append({
            "query": f'{state_name} hospital insurance "contract dispute" 2024 OR 2025',
            "type": "quick_dispute",
            "state": state,
            "year": "2024-2025",
            "priority": 1,
            "description": "Contract disputes",
        })

        # Query 2: Failed negotiations / impasse
        queries.append({
            "query": f'{state_name} hospital insurer "impasse" OR "failed negotiations" 2024 OR 2025',
            "type": "quick_impasse",
            "state": state,
            "year": "2024-2025",
            "priority": 1,
            "description": "Negotiation failures",
        })

        # Query 3: Accusations and rate conflicts
        queries.append({
            "query": f'{state_name} hospital accuses insurer OR "underpaid" OR "reimbursement" dispute 2024 OR 2025',
            "type": "quick_accusations",
            "state": state,
            "year": "2024-2025",
            "priority": 1,
            "description": "Public accusations",
        })

        # Query 4: Regional payer disputes
        if state in REGIONAL_PAYERS_TO_SEARCH:
            payer = REGIONAL_PAYERS_TO_SEARCH[state][0]
            queries.append({
                "query": f'"{payer}" hospital dispute OR impasse OR accuses 2024 OR 2025',
                "type": "quick_payer_dispute",
                "state": state,
                "payer": payer,
                "year": "2024-2025",
                "priority": 1,
                "description": f"Disputes with {payer}",
            })

    return queries


def format_for_manual_search(queries: List[Dict]) -> str:
    """Format queries for easy copy-paste into search engines."""
    output = []
    output.append("=" * 70)
    output.append("BACKFILL SEARCH QUERIES")
    output.append("=" * 70)
    output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    output.append(f"Total queries: {len(queries)}")
    output.append("")
    output.append("Instructions:")
    output.append("1. Copy each query into Google or Google News")
    output.append("2. Look for articles about hospital-insurer contract disputes")
    output.append("3. Note any disputes not in the current dataset")
    output.append("4. Add findings to input/disputes_to_enrich.csv")
    output.append("")
    output.append("=" * 70)

    # Group by state
    by_state = {}
    for q in queries:
        state = q.get("state", "Other")
        if state not in by_state:
            by_state[state] = []
        by_state[state].append(q)

    for state in sorted(by_state.keys()):
        state_queries = by_state[state]
        state_name = next((s["name"] for s in PRIORITY_STATES if s["state"] == state), state)

        output.append(f"\n### {state_name} ({state}) - {len(state_queries)} queries ###\n")

        for i, q in enumerate(state_queries, 1):
            output.append(f"[{state}-{i}] {q['query']}")
            output.append(f"      Type: {q['type']} | Year: {q.get('year', 'N/A')}")
            output.append("")

    return "\n".join(output)


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python backfill_search_queries.py full [state1,state2,...]")
        print("  python backfill_search_queries.py quick [state1,state2,...]")
        print("  python backfill_search_queries.py list-states")
        print("")
        print("Examples:")
        print("  python backfill_search_queries.py quick MA,IL,NJ")
        print("  python backfill_search_queries.py full")
        return

    command = sys.argv[1].lower()

    if command == "list-states":
        print("\nPriority states for backfill:\n")
        for s in PRIORITY_STATES:
            print(f"  [{s['priority']}] {s['state']}: {s['name']} - {s['reason']}")
        return

    # Parse state filter
    states = None
    if len(sys.argv) > 2:
        states = [s.strip().upper() for s in sys.argv[2].split(",")]

    if command == "quick":
        queries = generate_quick_backfill(states)
        print(format_for_manual_search(queries))

        # Save to file
        with open("backfill_queries_quick.json", "w") as f:
            json.dump(queries, f, indent=2)
        print(f"\nSaved to: backfill_queries_quick.json")

    elif command == "full":
        queries = generate_backfill_queries(states)
        print(format_for_manual_search(queries))

        # Save to file
        with open("backfill_queries_full.json", "w") as f:
            json.dump(queries, f, indent=2)
        print(f"\nSaved to: backfill_queries_full.json")

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
