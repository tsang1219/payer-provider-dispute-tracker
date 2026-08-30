#!/usr/bin/env python3
"""
Payer-Provider Dispute Discovery Agent

This agent proactively searches for new payer-provider disputes that may not
be in the existing dataset. It searches:
- Multiple healthcare news sources (not just Becker's and Modern Healthcare)
- Regional and local news
- State-specific payers (not just national insurers)
- Mid-size health systems that may not make national news

Usage:
    python agent/dispute_discovery_agent.py discover [state]
    python agent/dispute_discovery_agent.py search "health system name"
    python agent/dispute_discovery_agent.py audit [state]

This agent generates search queries that should be run via web search tools.
Results should be reviewed and added to input/disputes_to_enrich.csv.
"""

import json
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ============================================================================
# NEWS SOURCE CONFIGURATION
# ============================================================================

# Primary national healthcare news sources
NATIONAL_NEWS_SOURCES = [
    "beckershospitalreview.com",
    "modernhealthcare.com",
    "healthcaredive.com",
    "statnews.com",
    "fiercehealthcare.com",
    "healthaffairs.org",
    "kffhealthnews.org",
    "healthcarefinancenews.com",
]

# Regional/state news sources by region
REGIONAL_NEWS_SOURCES = {
    # Northeast
    "MA": ["bostonglobe.com", "wbur.org", "telegram.com", "bizjournals.com/boston"],
    "CT": ["courant.com", "ctpost.com", "ctmirror.org"],
    "NY": ["gothamist.com", "timesunion.com", "buffalonews.com", "democratandchronicle.com"],
    "NJ": ["nj.com", "northjersey.com"],
    "PA": ["inquirer.com", "post-gazette.com", "pennlive.com", "mcall.com"],
    "RI": ["providencejournal.com", "ripr.org"],

    # Southeast
    "FL": ["sun-sentinel.com", "tampabay.com", "miamiherald.com", "orlandosentinel.com"],
    "GA": ["ajc.com", "savannahnow.com", "georgiahealthnews.com"],
    "NC": ["newsobserver.com", "charlotteobserver.com", "wunc.org", "wfae.org"],
    "SC": ["thestate.com", "postandcourier.com", "greenvilleonline.com"],
    "VA": ["virginiamercury.com", "pilotonline.com", "richmond.com"],
    "TN": ["tennessean.com", "commercialappeal.com", "timesfreepress.com"],
    "AL": ["al.com", "whnt.com"],

    # Midwest
    "MN": ["startribune.com", "mprnews.org", "twincities.com"],
    "OH": ["cleveland.com", "dispatch.com", "daytondailynews.com", "cincinnati.com"],
    "MI": ["freep.com", "detroitnews.com", "mlive.com"],
    "IL": ["chicagotribune.com", "suntimes.com", "dailyherald.com"],
    "IN": ["indystar.com", "nwitimes.com"],
    "WI": ["jsonline.com", "madison.com"],
    "IA": ["desmoinesregister.com", "thegazette.com"],
    "MO": ["stltoday.com", "kansascity.com"],

    # Southwest
    "TX": ["dallasnews.com", "houstonchronicle.com", "statesman.com", "expressnews.com", "kvue.com"],
    "AZ": ["azcentral.com", "tucson.com", "azfamily.com"],
    "NM": ["abqjournal.com"],
    "OK": ["oklahoman.com", "tulsaworld.com"],

    # West
    "CA": ["latimes.com", "sfchronicle.com", "sandiegouniontribune.com", "sacbee.com", "mercurynews.com"],
    "WA": ["seattletimes.com", "spokesman.com", "king5.com"],
    "OR": ["oregonlive.com", "oregonbusiness.com", "salemreporter.com"],
    "CO": ["denverpost.com", "coloradosun.com", "9news.com"],
    "NV": ["reviewjournal.com", "rgj.com"],

    # Other states
    "KY": ["courier-journal.com", "kentucky.com"],
    "AR": ["arkansasonline.com"],
    "LA": ["nola.com", "theadvocate.com"],
    "MS": ["clarionledger.com"],
    "WV": ["wvgazettemail.com"],
    "SD": ["argusleader.com", "keloland.com"],
    "ND": ["inforum.com", "grandforksherald.com"],
    "NE": ["omaha.com", "journalstar.com"],
    "KS": ["kansas.com", "kansascity.com"],
    "ID": ["idahostatesman.com", "idahocapitalsun.com"],
    "MT": ["billingsgazette.com", "missoulian.com"],
    "WY": ["trib.com"],
    "UT": ["sltrib.com", "deseret.com"],
    "ME": ["pressherald.com", "bangordailynews.com", "wabi.tv"],
    "NH": ["unionleader.com", "nhpr.org"],
    "VT": ["burlingtonfreepress.com", "vtdigger.org"],
    "DE": ["delawareonline.com"],
    "MD": ["baltimoresun.com", "washingtonpost.com"],
    "DC": ["washingtonpost.com", "washingtonian.com"],
}

# ============================================================================
# REGIONAL PAYER CONFIGURATION
# ============================================================================

# Regional/state-specific payers often missed by national searches
REGIONAL_PAYERS = {
    # Northeast
    "MA": [
        {"name": "Tufts Health Plan", "parent": "Point32Health"},
        {"name": "Harvard Pilgrim Health Care", "parent": "Point32Health"},
        {"name": "Blue Cross Blue Shield of Massachusetts", "parent": "BCBS Association"},
        {"name": "Neighborhood Health Plan", "parent": "Point32Health"},
        {"name": "Fallon Health", "parent": None},
        {"name": "Health New England", "parent": "Baystate Health"},
    ],
    "CT": [
        {"name": "ConnectiCare", "parent": "EmblemHealth"},
        {"name": "Anthem Blue Cross Blue Shield of Connecticut", "parent": "Elevance Health"},
    ],
    "NY": [
        {"name": "Healthfirst", "parent": None},
        {"name": "EmblemHealth", "parent": None},
        {"name": "Fidelis Care", "parent": "Centene"},
        {"name": "MVP Health Care", "parent": None},
        {"name": "Independent Health", "parent": None},
        {"name": "Excellus BlueCross BlueShield", "parent": "BCBS Association"},
    ],
    "NJ": [
        {"name": "Horizon Blue Cross Blue Shield of New Jersey", "parent": "BCBS Association"},
        {"name": "AmeriHealth New Jersey", "parent": "Independence Health Group"},
    ],
    "PA": [
        {"name": "Highmark", "parent": "Highmark Health"},
        {"name": "Independence Blue Cross", "parent": "Independence Health Group"},
        {"name": "UPMC Health Plan", "parent": "UPMC"},
        {"name": "Geisinger Health Plan", "parent": "Risant Health"},
    ],
    "RI": [
        {"name": "Blue Cross Blue Shield of Rhode Island", "parent": "BCBS Association"},
        {"name": "Neighborhood Health Plan of Rhode Island", "parent": None},
    ],

    # Southeast
    "FL": [
        {"name": "Florida Blue", "parent": "GuideWell"},
        {"name": "AvMed", "parent": "SantaFe HealthCare"},
        {"name": "Simply Healthcare", "parent": "Anthem/Elevance"},
    ],
    "GA": [
        {"name": "Blue Cross Blue Shield of Georgia", "parent": "Anthem/Elevance Health"},
        {"name": "Peach State Health Plan", "parent": "Centene"},
    ],
    "NC": [
        {"name": "Blue Cross Blue Shield of North Carolina", "parent": "BCBS Association"},
        {"name": "WellCare of North Carolina", "parent": "Centene"},
    ],
    "TN": [
        {"name": "Blue Cross Blue Shield of Tennessee", "parent": "BCBS Association"},
        {"name": "TennCare", "parent": "State Medicaid"},
    ],

    # Midwest
    "MN": [
        {"name": "HealthPartners", "parent": None},
        {"name": "Blue Cross Blue Shield of Minnesota", "parent": "BCBS Association"},
        {"name": "Medica", "parent": None},
        {"name": "UCare", "parent": None},
        {"name": "PreferredOne", "parent": None},
    ],
    "OH": [
        {"name": "Medical Mutual of Ohio", "parent": None},
        {"name": "CareSource", "parent": None},
        {"name": "SummaCare", "parent": "Summa Health"},
        {"name": "Paramount", "parent": "ProMedica"},
    ],
    "MI": [
        {"name": "Blue Cross Blue Shield of Michigan", "parent": "BCBS Association"},
        {"name": "Priority Health", "parent": "Corewell Health"},
        {"name": "Health Alliance Plan", "parent": "Henry Ford Health"},
        {"name": "McLaren Health Plan", "parent": "McLaren Health Care"},
    ],
    "IL": [
        {"name": "Blue Cross Blue Shield of Illinois", "parent": "HCSC"},
        {"name": "Health Care Service Corporation", "parent": "HCSC"},
    ],

    # Texas
    "TX": [
        {"name": "Blue Cross Blue Shield of Texas", "parent": "HCSC"},
        {"name": "Superior HealthPlan", "parent": "Centene"},
        {"name": "Community Health Choice", "parent": None},
        {"name": "Scott & White Health Plan", "parent": "Baylor Scott & White"},
    ],

    # West
    "CA": [
        {"name": "Blue Shield of California", "parent": None},
        {"name": "Anthem Blue Cross of California", "parent": "Elevance Health"},
        {"name": "Kaiser Permanente", "parent": "Kaiser Foundation"},
        {"name": "Health Net", "parent": "Centene"},
        {"name": "L.A. Care Health Plan", "parent": None},
        {"name": "CalOptima", "parent": None},
    ],
    "WA": [
        {"name": "Premera Blue Cross", "parent": "BCBS Association"},
        {"name": "Regence BlueShield", "parent": "Cambia Health Solutions"},
        {"name": "Molina Healthcare of Washington", "parent": "Molina Healthcare"},
        {"name": "Community Health Plan of Washington", "parent": "Centene"},
    ],
    "OR": [
        {"name": "Regence BlueCross BlueShield of Oregon", "parent": "Cambia Health Solutions"},
        {"name": "Providence Health Plan", "parent": "Providence St. Joseph Health"},
        {"name": "Moda Health", "parent": None},
        {"name": "PacificSource Health Plans", "parent": None},
    ],
    "CO": [
        {"name": "Anthem Blue Cross Blue Shield of Colorado", "parent": "Elevance Health"},
        {"name": "Kaiser Permanente Colorado", "parent": "Kaiser Foundation"},
        {"name": "Denver Health Medical Plan", "parent": "Denver Health"},
        {"name": "Friday Health Plans", "parent": None},
    ],

    # Other notable regional payers
    "ID": [
        {"name": "Regence BlueShield of Idaho", "parent": "Cambia Health Solutions"},
        {"name": "Blue Cross of Idaho", "parent": "BCBS Association"},
    ],
    "AZ": [
        {"name": "Blue Cross Blue Shield of Arizona", "parent": "BCBS Association"},
        {"name": "Banner Health Plan", "parent": "Banner Health"},
        {"name": "Mercy Care", "parent": "Aetna/CVS"},
    ],
}

# National payers for reference
NATIONAL_PAYERS = [
    {"name": "UnitedHealthcare", "parent": "UnitedHealth Group"},
    {"name": "Anthem", "parent": "Elevance Health"},
    {"name": "Aetna", "parent": "CVS Health"},
    {"name": "Cigna", "parent": "The Cigna Group"},
    {"name": "Humana", "parent": "Humana Inc."},
    {"name": "Centene", "parent": "Centene Corporation"},
    {"name": "Molina Healthcare", "parent": "Molina Healthcare Inc."},
    {"name": "WellCare", "parent": "Centene Corporation"},
]

# ============================================================================
# HEALTH SYSTEM DATABASE (DISCOVERY TARGETS)
# ============================================================================

# Mid-size and regional health systems that may be underrepresented
# These are systems to proactively search for disputes
DISCOVERY_TARGET_SYSTEMS = {
    # Massachusetts (currently underrepresented)
    "MA": [
        {"name": "UMass Memorial Health", "city": "Worcester", "beds": 1100, "revenue_mm": 6700},
        {"name": "Tufts Medical Center", "city": "Boston", "beds": 415, "revenue_mm": 1200},
        {"name": "Baystate Health", "city": "Springfield", "beds": 716, "revenue_mm": 2500},
        {"name": "Lahey Hospital & Medical Center", "city": "Burlington", "beds": 335, "revenue_mm": 1800},
        {"name": "Beth Israel Lahey Health", "city": "Boston", "beds": 4000, "revenue_mm": 7000},
        {"name": "Steward Health Care", "city": "Dallas", "beds": 2500, "revenue_mm": 3000},  # MA operations
        {"name": "Cape Cod Healthcare", "city": "Hyannis", "beds": 350, "revenue_mm": 800},
        {"name": "Emerson Hospital", "city": "Concord", "beds": 179, "revenue_mm": 400},
        {"name": "Southcoast Health", "city": "Fall River", "beds": 650, "revenue_mm": 1100},
        {"name": "Cambridge Health Alliance", "city": "Cambridge", "beds": 205, "revenue_mm": 600},
    ],

    # Connecticut
    "CT": [
        {"name": "Yale New Haven Health", "city": "New Haven", "beds": 2600, "revenue_mm": 8500},
        {"name": "Hartford HealthCare", "city": "Hartford", "beds": 2500, "revenue_mm": 6000},
        {"name": "Trinity Health Of New England", "city": "Hartford", "beds": 800, "revenue_mm": 2000},
        {"name": "Nuvance Health", "city": "Danbury", "beds": 1000, "revenue_mm": 2200},
    ],

    # New York (mid-size systems)
    "NY": [
        {"name": "Northwell Health", "city": "New Hyde Park", "beds": 4500, "revenue_mm": 17000},
        {"name": "Rochester Regional Health", "city": "Rochester", "beds": 1200, "revenue_mm": 2500},
        {"name": "WMCHealth Network", "city": "Valhalla", "beds": 1700, "revenue_mm": 2700},
        {"name": "Catholic Health", "city": "Buffalo", "beds": 1100, "revenue_mm": 2000},
        {"name": "Bassett Healthcare Network", "city": "Cooperstown", "beds": 180, "revenue_mm": 900},
    ],

    # Rhode Island
    "RI": [
        {"name": "Care New England", "city": "Providence", "beds": 600, "revenue_mm": 1200},
        {"name": "CharterCARE Health Partners", "city": "Providence", "beds": 300, "revenue_mm": 400},
    ],

    # Additional states with underrepresented mid-size systems
    "PA": [
        {"name": "Tower Health", "city": "West Reading", "beds": 800, "revenue_mm": 1800},
        {"name": "St. Luke's University Health Network", "city": "Bethlehem", "beds": 1100, "revenue_mm": 3000},
        {"name": "Geisinger", "city": "Danville", "beds": 1700, "revenue_mm": 8000},
    ],

    "NJ": [
        {"name": "RWJBarnabas Health", "city": "West Orange", "beds": 3300, "revenue_mm": 6500},
        {"name": "Atlantic Health System", "city": "Morristown", "beds": 1200, "revenue_mm": 3500},
        {"name": "Virtua Health", "city": "Marlton", "beds": 900, "revenue_mm": 2000},
    ],

    "OH": [
        {"name": "OhioHealth", "city": "Columbus", "beds": 3000, "revenue_mm": 6000},
        {"name": "University Hospitals", "city": "Cleveland", "beds": 1500, "revenue_mm": 5500},
        {"name": "MetroHealth System", "city": "Cleveland", "beds": 700, "revenue_mm": 1500},
        {"name": "Summa Health", "city": "Akron", "beds": 650, "revenue_mm": 1200},
    ],

    "MI": [
        {"name": "Henry Ford Health", "city": "Detroit", "beds": 2100, "revenue_mm": 7500},
        {"name": "Beaumont Health", "city": "Southfield", "beds": 3400, "revenue_mm": 5000},
        {"name": "McLaren Health Care", "city": "Grand Blanc", "beds": 2000, "revenue_mm": 4500},
    ],

    "IL": [
        {"name": "Advocate Aurora Health", "city": "Downers Grove", "beds": 8000, "revenue_mm": 14000},
        {"name": "NorthShore University HealthSystem", "city": "Evanston", "beds": 800, "revenue_mm": 3000},
        {"name": "OSF HealthCare", "city": "Peoria", "beds": 2000, "revenue_mm": 4500},
        {"name": "Carle Health", "city": "Urbana", "beds": 400, "revenue_mm": 1500},
    ],
}

# ============================================================================
# QUERY GENERATION
# ============================================================================

def generate_discovery_queries(
    state: Optional[str] = None,
    system_name: Optional[str] = None,
    year: int = None,
    include_resolved: bool = True
) -> List[Dict]:
    """
    Generate discovery queries to find new disputes not in the dataset.

    Args:
        state: Limit to specific state
        system_name: Search for specific health system
        year: Year to search (default: current and previous year)
        include_resolved: Include resolved disputes in search

    Returns:
        List of query dictionaries with query text and metadata
    """
    if year is None:
        year = datetime.now().year

    queries = []

    # If searching for a specific system
    if system_name:
        queries.extend(_generate_system_queries(system_name, state, year))
        return queries

    # If searching by state
    if state:
        queries.extend(_generate_state_discovery_queries(state, year))
        return queries

    # Full discovery mode - search all underrepresented states/systems
    for st, systems in DISCOVERY_TARGET_SYSTEMS.items():
        for system in systems[:3]:  # Limit to top 3 per state for manageable queries
            queries.extend(_generate_system_queries(system["name"], st, year))

    return queries


def _generate_system_queries(system_name: str, state: str, year: int) -> List[Dict]:
    """Generate queries for a specific health system."""
    queries = []

    # Get relevant payers for the state
    payers = REGIONAL_PAYERS.get(state, []) + NATIONAL_PAYERS

    # Get news sources
    news_sources = REGIONAL_NEWS_SOURCES.get(state, []) + NATIONAL_NEWS_SOURCES

    # Clean system name
    system_clean = re.sub(r'\s+Health System$|\s+Health$|\s+Healthcare$|\s+Medical Center$', '', system_name).strip()

    # Query 1: General contract dispute search
    queries.append({
        "query": f'"{system_name}" contract dispute {year}',
        "type": "general_dispute",
        "system": system_name,
        "state": state,
        "year": year,
        "priority": 1,
    })

    # Query 2: Out of network search
    queries.append({
        "query": f'"{system_name}" out of network {year}',
        "type": "oon_search",
        "system": system_name,
        "state": state,
        "year": year,
        "priority": 1,
    })

    # Query 3: Medicare Advantage termination
    queries.append({
        "query": f'"{system_name}" Medicare Advantage contract {year}',
        "type": "ma_contract",
        "system": system_name,
        "state": state,
        "year": year,
        "priority": 2,
    })

    # Query 4: With specific regional payers
    for payer in payers[:5]:  # Top 5 payers
        payer_name = payer["name"]
        queries.append({
            "query": f'"{system_clean}" "{payer_name}" contract {year}',
            "type": "payer_specific",
            "system": system_name,
            "payer": payer_name,
            "state": state,
            "year": year,
            "priority": 2,
        })

    # Query 5: News site specific (regional)
    if state in REGIONAL_NEWS_SOURCES:
        sites = REGIONAL_NEWS_SOURCES[state][:3]
        site_query = " OR ".join([f"site:{s}" for s in sites])
        queries.append({
            "query": f'({site_query}) "{system_clean}" insurance contract {year}',
            "type": "regional_news",
            "system": system_name,
            "state": state,
            "year": year,
            "priority": 2,
        })

    # Query 6: National healthcare news
    national_sites = NATIONAL_NEWS_SOURCES[:4]
    site_query = " OR ".join([f"site:{s}" for s in national_sites])
    queries.append({
        "query": f'({site_query}) "{system_clean}" contract {year}',
        "type": "national_news",
        "system": system_name,
        "state": state,
        "year": year,
        "priority": 3,
    })

    # Query 7: Previous year (disputes often span years)
    queries.append({
        "query": f'"{system_name}" contract dispute {year - 1}',
        "type": "previous_year",
        "system": system_name,
        "state": state,
        "year": year - 1,
        "priority": 3,
    })

    return queries


def _generate_state_discovery_queries(state: str, year: int) -> List[Dict]:
    """Generate broad discovery queries for a state."""
    queries = []

    # State-wide searches
    state_name = _get_state_name(state)

    # Query 1: General state healthcare dispute search
    queries.append({
        "query": f'{state_name} hospital insurance contract dispute {year}',
        "type": "state_general",
        "state": state,
        "year": year,
        "priority": 1,
    })

    # Query 2: Medicare Advantage in state
    queries.append({
        "query": f'{state_name} hospital Medicare Advantage out of network {year}',
        "type": "state_ma",
        "state": state,
        "year": year,
        "priority": 1,
    })

    # Query 3: With regional payers
    if state in REGIONAL_PAYERS:
        for payer in REGIONAL_PAYERS[state][:3]:
            queries.append({
                "query": f'"{payer["name"]}" hospital contract dispute {year}',
                "type": "payer_state",
                "payer": payer["name"],
                "state": state,
                "year": year,
                "priority": 2,
            })

    # Query 4: Regional news site search
    if state in REGIONAL_NEWS_SOURCES:
        sites = REGIONAL_NEWS_SOURCES[state][:3]
        site_query = " OR ".join([f"site:{s}" for s in sites])
        queries.append({
            "query": f'({site_query}) hospital insurance contract out of network {year}',
            "type": "state_regional_news",
            "state": state,
            "year": year,
            "priority": 2,
        })

    # Query 5: Each target system in the state
    if state in DISCOVERY_TARGET_SYSTEMS:
        for system in DISCOVERY_TARGET_SYSTEMS[state]:
            queries.extend(_generate_system_queries(system["name"], state, year))

    return queries


def _get_state_name(abbrev: str) -> str:
    """Convert state abbreviation to full name."""
    state_names = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
        "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
        "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
        "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
        "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
        "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
        "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
        "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
        "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
        "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
        "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
        "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
        "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia"
    }
    return state_names.get(abbrev, abbrev)


# ============================================================================
# COVERAGE AUDIT
# ============================================================================

def audit_coverage(existing_csv: str = "input/disputes_to_enrich.csv") -> Dict:
    """
    Audit the existing dataset for coverage gaps.

    Returns:
        Dictionary with coverage statistics and recommendations
    """
    # Read existing disputes
    existing_systems = set()
    state_counts = {}
    payer_counts = {}

    try:
        with open(existing_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                system = row.get('system_name', '')
                state = row.get('state', '')
                insurer = row.get('insurer_name', '')

                if 'FTI Aggregate' not in system:
                    existing_systems.add(system.lower())
                    state_counts[state] = state_counts.get(state, 0) + 1

                    # Normalize insurer name
                    insurer_norm = re.sub(r'\s*\([^)]*\)\s*', '', insurer).strip()
                    payer_counts[insurer_norm] = payer_counts.get(insurer_norm, 0) + 1
    except FileNotFoundError:
        print(f"Warning: {existing_csv} not found")

    # Identify missing systems
    missing_systems = {}
    for state, systems in DISCOVERY_TARGET_SYSTEMS.items():
        missing = []
        for system in systems:
            name_lower = system["name"].lower()
            # Check if any variant of the name exists
            found = any(name_lower in existing or existing in name_lower
                       for existing in existing_systems)
            if not found:
                missing.append(system)
        if missing:
            missing_systems[state] = missing

    # Identify underrepresented states
    underrepresented_states = []
    for state in DISCOVERY_TARGET_SYSTEMS.keys():
        count = state_counts.get(state, 0)
        expected_min = len(DISCOVERY_TARGET_SYSTEMS.get(state, [])) // 2
        if count < max(expected_min, 2):
            underrepresented_states.append({
                "state": state,
                "current_count": count,
                "target_systems": len(DISCOVERY_TARGET_SYSTEMS.get(state, [])),
            })

    # Identify missing regional payers
    missing_payers = {}
    for state, payers in REGIONAL_PAYERS.items():
        missing = []
        for payer in payers:
            payer_lower = payer["name"].lower()
            found = any(payer_lower in existing.lower() or existing.lower() in payer_lower
                       for existing in payer_counts.keys())
            if not found:
                missing.append(payer)
        if missing:
            missing_payers[state] = missing

    return {
        "total_disputes": sum(state_counts.values()),
        "states_with_disputes": len(state_counts),
        "state_coverage": state_counts,
        "underrepresented_states": sorted(underrepresented_states,
                                          key=lambda x: x["current_count"]),
        "missing_systems": missing_systems,
        "missing_regional_payers": missing_payers,
        "top_payers": sorted(payer_counts.items(), key=lambda x: -x[1])[:15],
        "recommendations": _generate_recommendations(
            missing_systems, underrepresented_states, missing_payers
        ),
    }


def _generate_recommendations(
    missing_systems: Dict,
    underrepresented_states: List,
    missing_payers: Dict
) -> List[str]:
    """Generate actionable recommendations based on audit."""
    recommendations = []

    # Priority 1: Underrepresented states
    if underrepresented_states:
        states = [s["state"] for s in underrepresented_states[:5]]
        recommendations.append(
            f"HIGH PRIORITY: Search for disputes in underrepresented states: {', '.join(states)}"
        )

    # Priority 2: Missing major systems
    high_revenue_missing = []
    for state, systems in missing_systems.items():
        for sys in systems:
            if sys.get("revenue_mm", 0) > 2000:
                high_revenue_missing.append(f"{sys['name']} ({state})")

    if high_revenue_missing:
        recommendations.append(
            f"HIGH PRIORITY: Major health systems missing from dataset: {', '.join(high_revenue_missing[:5])}"
        )

    # Priority 3: Missing regional payers
    if missing_payers:
        states_with_missing = list(missing_payers.keys())[:5]
        recommendations.append(
            f"MEDIUM PRIORITY: Regional payers not represented in states: {', '.join(states_with_missing)}"
        )

    return recommendations


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def format_queries_for_execution(queries: List[Dict]) -> str:
    """Format queries for manual or automated execution."""
    output = []
    output.append("=" * 70)
    output.append("DISPUTE DISCOVERY QUERIES")
    output.append("=" * 70)
    output.append(f"Generated: {datetime.now().isoformat()}")
    output.append(f"Total queries: {len(queries)}")
    output.append("")

    # Group by priority
    priority_groups = {}
    for q in queries:
        p = q.get("priority", 99)
        if p not in priority_groups:
            priority_groups[p] = []
        priority_groups[p].append(q)

    for priority in sorted(priority_groups.keys()):
        group = priority_groups[priority]
        output.append(f"\n--- Priority {priority} ({len(group)} queries) ---\n")

        for i, q in enumerate(group, 1):
            output.append(f"[{i}] {q['query']}")
            meta = []
            if q.get('system'):
                meta.append(f"System: {q['system']}")
            if q.get('payer'):
                meta.append(f"Payer: {q['payer']}")
            if q.get('state'):
                meta.append(f"State: {q['state']}")
            if meta:
                output.append(f"    ({', '.join(meta)})")
            output.append("")

    return "\n".join(output)


def save_queries_json(queries: List[Dict], output_path: str = "discovery_queries.json"):
    """Save queries to JSON for automated processing."""
    output = {
        "generated": datetime.now().isoformat(),
        "total_queries": len(queries),
        "queries": queries,
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    return output_path


# ============================================================================
# RESULT PROCESSING
# ============================================================================

def parse_discovery_result(search_result_text: str, query_meta: Dict) -> Optional[Dict]:
    """
    Parse a search result to extract dispute information.

    Returns dict ready to be added to disputes_to_enrich.csv if a dispute is found.
    """
    if not search_result_text:
        return None

    text = search_result_text.lower()

    # Check for dispute indicators
    dispute_indicators = [
        "contract dispute", "out of network", "out-of-network",
        "contract terminated", "contract expired", "failed negotiations",
        "dropped from", "leaving network", "exiting network",
        "no longer in-network", "will no longer accept",
    ]

    has_dispute = any(indicator in text for indicator in dispute_indicators)

    if not has_dispute:
        return None

    # Extract information
    result = {
        "system_name": query_meta.get("system", ""),
        "insurer_name": query_meta.get("payer", ""),
        "state": query_meta.get("state", ""),
        "year_first_reported": query_meta.get("year", datetime.now().year),
        "quarter_first_reported": _determine_quarter(search_result_text),
        "outcome_status": _determine_status(search_result_text),
        "primary_source": query_meta.get("type", "web_search"),
        "notes": _extract_key_details(search_result_text),
        "discovery_date": datetime.now().isoformat(),
    }

    return result


def _determine_quarter(text: str) -> str:
    """Determine the quarter from text context."""
    text_lower = text.lower()
    month_to_quarter = {
        "january": "Q1", "february": "Q1", "march": "Q1",
        "april": "Q2", "may": "Q2", "june": "Q2",
        "july": "Q3", "august": "Q3", "september": "Q3",
        "october": "Q4", "november": "Q4", "december": "Q4",
    }

    for month, quarter in month_to_quarter.items():
        if month in text_lower:
            return quarter

    return "Q4"  # Default to Q4 if unclear


def _determine_status(text: str) -> str:
    """Determine dispute status from text."""
    text_lower = text.lower()

    if any(word in text_lower for word in ["resolved", "reached agreement", "new contract", "deal reached"]):
        return "Resolved"
    elif any(word in text_lower for word in ["ongoing", "continues", "still out of network"]):
        return "OON-Ongoing"
    elif any(word in text_lower for word in ["temporary", "extension", "cooling off"]):
        return "OON-Temporary"
    else:
        return "Unknown"


def _extract_key_details(text: str) -> str:
    """Extract key details for notes field."""
    details = []

    # Look for patient counts
    patient_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:patients|members|seniors)', text, re.IGNORECASE)
    if patient_match:
        details.append(f"{patient_match.group(1)} patients/members")

    # Look for dates
    date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}', text, re.IGNORECASE)
    if date_match:
        details.append(f"Date mentioned: {date_match.group(0)}")

    return "; ".join(details) if details else "Discovered via web search"


# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "discover":
        # Generate discovery queries
        state = sys.argv[2].upper() if len(sys.argv) > 2 else None
        year = int(sys.argv[3]) if len(sys.argv) > 3 else None

        print(f"\nGenerating discovery queries...")
        if state:
            print(f"State filter: {state}")

        queries = generate_discovery_queries(state=state, year=year)

        # Print formatted output
        print(format_queries_for_execution(queries))

        # Save to JSON
        output_path = save_queries_json(queries)
        print(f"\nQueries saved to: {output_path}")
        print(f"Total queries generated: {len(queries)}")

    elif command == "search":
        # Search for specific system
        if len(sys.argv) < 3:
            print("Usage: python dispute_discovery_agent.py search \"Health System Name\" [state]")
            return

        system_name = sys.argv[2]
        state = sys.argv[3].upper() if len(sys.argv) > 3 else None

        print(f"\nGenerating queries for: {system_name}")
        queries = generate_discovery_queries(system_name=system_name, state=state)

        print(format_queries_for_execution(queries))

        # Save
        output_path = save_queries_json(queries, f"discovery_{system_name.replace(' ', '_')}.json")
        print(f"\nQueries saved to: {output_path}")

    elif command == "audit":
        # Audit coverage
        state_filter = sys.argv[2].upper() if len(sys.argv) > 2 else None

        print("\nAuditing dataset coverage...")
        audit = audit_coverage()

        print("\n" + "=" * 70)
        print("COVERAGE AUDIT REPORT")
        print("=" * 70)
        print(f"\nTotal disputes in dataset: {audit['total_disputes']}")
        print(f"States with disputes: {audit['states_with_disputes']}")

        print("\n--- State Coverage ---")
        for state, count in sorted(audit['state_coverage'].items(), key=lambda x: -x[1])[:15]:
            print(f"  {state}: {count}")

        print("\n--- Underrepresented States ---")
        for state_info in audit['underrepresented_states'][:10]:
            print(f"  {state_info['state']}: {state_info['current_count']} disputes "
                  f"(target systems: {state_info['target_systems']})")

        print("\n--- Missing Major Systems ---")
        for state, systems in list(audit['missing_systems'].items())[:5]:
            print(f"  {state}:")
            for sys in systems[:3]:
                print(f"    - {sys['name']} (${sys.get('revenue_mm', 'N/A')}M revenue)")

        print("\n--- Top Payers in Dataset ---")
        for payer, count in audit['top_payers'][:10]:
            print(f"  {payer}: {count}")

        print("\n--- Recommendations ---")
        for i, rec in enumerate(audit['recommendations'], 1):
            print(f"  {i}. {rec}")

        # Save full audit
        with open("coverage_audit.json", 'w', encoding='utf-8') as f:
            json.dump(audit, f, indent=2, default=str)
        print(f"\nFull audit saved to: coverage_audit.json")

    elif command == "payers":
        # List regional payers
        state = sys.argv[2].upper() if len(sys.argv) > 2 else None

        if state:
            payers = REGIONAL_PAYERS.get(state, [])
            print(f"\nRegional payers in {state}:")
            for p in payers:
                parent = f" ({p['parent']})" if p.get('parent') else ""
                print(f"  - {p['name']}{parent}")
        else:
            print("\nRegional payers by state:")
            for state, payers in sorted(REGIONAL_PAYERS.items()):
                print(f"\n{state}:")
                for p in payers[:5]:
                    print(f"  - {p['name']}")

    elif command == "systems":
        # List target systems
        state = sys.argv[2].upper() if len(sys.argv) > 2 else None

        if state:
            systems = DISCOVERY_TARGET_SYSTEMS.get(state, [])
            print(f"\nTarget systems in {state}:")
            for s in systems:
                print(f"  - {s['name']} ({s['city']}, ${s.get('revenue_mm', 'N/A')}M)")
        else:
            print("\nDiscovery target systems by state:")
            for state, systems in sorted(DISCOVERY_TARGET_SYSTEMS.items()):
                print(f"\n{state}:")
                for s in systems[:5]:
                    print(f"  - {s['name']}")

    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
