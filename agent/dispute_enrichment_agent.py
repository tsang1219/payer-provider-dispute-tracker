#!/usr/bin/env python3
"""
Payer-Provider Dispute Enrichment Agent

This script processes the seed CSV and enriches each dispute with:
- Extracted data from notes
- Geocoded locations
- Web search results for dates, patient counts, resolution terms

Run in Claude Code with: python agent/dispute_enrichment_agent.py

Output: Enriched CSV and Airtable-ready JSON
"""

import csv
import json
import re
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
from pathlib import Path

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class EnrichedDispute:
    """Full enriched dispute record"""
    # Identity (from seed)
    dispute_id: int
    dispute_name: str
    
    # Parties
    system_name: str
    system_name_normalized: str
    system_hq_city: Optional[str] = None
    system_hq_state: str = ""
    system_hq_lat: Optional[float] = None
    system_hq_lon: Optional[float] = None
    system_footprint_states: Optional[List[str]] = None
    system_hospital_count: Optional[int] = None
    system_annual_revenue_mm: Optional[float] = None
    
    insurer_name: str = ""
    insurer_name_normalized: str = ""
    insurer_parent: Optional[str] = None
    insurer_type: Optional[str] = None  # Commercial, Medicare Advantage, etc.
    
    # Timeline
    year_first_reported: int = 0
    quarter_first_reported: str = ""
    first_media_date: Optional[str] = None
    deadline_date: Optional[str] = None
    oon_effective_date: Optional[str] = None
    resolution_date: Optional[str] = None

    # Date sources
    first_media_date_source: Optional[str] = None
    deadline_date_source: Optional[str] = None
    oon_effective_date_source: Optional[str] = None
    resolution_date_source: Optional[str] = None

    # Status
    outcome_status: str = ""
    outcome_status_detail: Optional[str] = None
    
    # Impact
    patients_affected: Optional[int] = None
    patients_affected_source: Optional[str] = None
    dispute_type: Optional[str] = None  # Commercial, MA, Medicaid, All MA
    
    # Negotiation details
    rate_increase_requested_pct: Optional[float] = None
    rate_info_raw: Optional[str] = None
    duration_months: Optional[int] = None
    key_issues: Optional[List[str]] = None
    
    # Resolution
    resolution_type: Optional[str] = None
    resolution_terms_summary: Optional[str] = None
    lawsuit_filed: bool = False
    dollar_amount_mm: Optional[float] = None
    
    # Sources
    primary_source: str = ""
    primary_source_url: Optional[str] = None
    additional_sources: Optional[List[str]] = None
    
    # Meta
    notes: str = ""
    enrichment_notes: str = ""
    data_completeness_score: float = 0.0
    last_updated: str = ""


@dataclass 
class TimelineEvent:
    """Individual event for time-series animation"""
    event_id: str
    dispute_id: int
    event_date: str
    event_type: str  # dispute_public, oon_effective, resolution, etc.
    event_description: str
    source: Optional[str] = None


# ============================================================================
# EXTRACTION PATTERNS
# ============================================================================

PATIENT_PATTERNS = [
    (r'(\d{1,3}(?:,\d{3})*)\s*patients', 'patients'),
    (r'(\d{1,3}(?:,\d{3})*)\s*members', 'members'),
    (r'(\d{1,3}(?:,\d{3})*)\s*seniors', 'seniors'),
    (r'(\d{1,3}(?:,\d{3})*)\s*children', 'children'),
    (r'affecting\s*(\d{1,3}(?:,\d{3})*)', 'affecting'),
    (r'impacted?\s*(\d{1,3}(?:,\d{3})*)', 'impacted'),
]

DATE_PATTERNS = [
    # "OON Jan 1, 2024" or "OON effective Jan 1, 2024"
    (r'OON\s*(?:effective\s*)?(\w+\s+\d{1,2},?\s*\d{4})', 'oon_effective'),
    # "ended Oct 1, 2021" or "terminated Dec 31, 2024"
    (r'(?:ended|terminated|expired|expiring)\s*(\w+\s+\d{1,2},?\s*\d{4})', 'deadline'),
    # "resolved June 2023" or "Resolved Feb 2024"
    (r'[Rr]esolved\s*(\w+\s*\d{4})', 'resolution'),
    # "deadline April 2024"
    (r'deadline\s*(\w+\s*\d{4})', 'deadline'),
    # Just month year like "Aug 2021"
    (r'deal\s*(?:reached\s*)?(\w+\s*\d{4})', 'resolution'),
]

DURATION_PATTERNS = [
    (r'(\d+)\s*months?\s*OON', 'months_oon'),
    (r'(\d+)\s*years?\s*(?:failed\s*)?negotiations?', 'years_negotiating'),
]

RATE_PATTERNS = [
    # "35% vs 3.4% offers"
    (r'(\d+(?:\.\d+)?%)\s*vs\s*(\d+(?:\.\d+)?%)', 'rate_comparison'),
    # "rates unchanged since 2020" or "rates unchanged 6 years"
    (r'rates?\s*unchanged\s*(?:since\s*)?(\d{4}|\d+\s*years?)', 'rates_unchanged'),
]

DOLLAR_PATTERNS = [
    # "$93M unpaid claims" or "$62.65M jury award"
    (r'\$(\d+(?:\.\d+)?)\s*[Mm](?:illion)?', 'millions'),
    (r'\$(\d+(?:\.\d+)?)\s*[Bb](?:illion)?', 'billions'),
]

LAWSUIT_KEYWORDS = ['lawsuit', 'sued', 'litigation', 'arbitration', 'jury', 'court', 'injunction']

MA_KEYWORDS = ['Medicare Advantage', 'MA ', 'MA,', 'MA;', 'all MA', 'MA plans', 'MA contract', 
               'seniors', 'D-SNP', 'Humana MA', 'Aetna MA', 'UHC MA']


# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

def parse_number(s: str) -> int:
    """Parse a number string like '80,000' into integer"""
    return int(s.replace(',', ''))


def extract_patients_affected(notes: str) -> tuple[Optional[int], Optional[str]]:
    """Extract patient/member count from notes"""
    if not notes:
        return None, None
    
    for pattern, source_type in PATIENT_PATTERNS:
        match = re.search(pattern, notes, re.IGNORECASE)
        if match:
            try:
                count = parse_number(match.group(1))
                return count, f"extracted_from_notes_{source_type}"
            except ValueError:
                continue
    return None, None


def extract_dates(notes: str) -> Dict[str, Optional[str]]:
    """Extract various dates from notes"""
    dates = {
        'oon_effective_date': None,
        'deadline_date': None,
        'resolution_date': None,
    }
    
    if not notes:
        return dates
    
    for pattern, date_type in DATE_PATTERNS:
        match = re.search(pattern, notes, re.IGNORECASE)
        if match:
            raw_date = match.group(1)
            # Map to our date fields
            if date_type == 'oon_effective':
                dates['oon_effective_date'] = raw_date
            elif date_type == 'deadline':
                dates['deadline_date'] = raw_date
            elif date_type == 'resolution':
                dates['resolution_date'] = raw_date
    
    return dates


def extract_duration(notes: str) -> Optional[int]:
    """Extract duration in months if mentioned"""
    if not notes:
        return None
    
    for pattern, _ in DURATION_PATTERNS:
        match = re.search(pattern, notes, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


def extract_rate_info(notes: str) -> Optional[str]:
    """Extract rate/pricing information"""
    if not notes:
        return None
    
    for pattern, _ in RATE_PATTERNS:
        match = re.search(pattern, notes, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def extract_dollar_amount(notes: str) -> Optional[float]:
    """Extract dollar amounts in millions"""
    if not notes:
        return None
    
    for pattern, unit in DOLLAR_PATTERNS:
        match = re.search(pattern, notes, re.IGNORECASE)
        if match:
            try:
                amount = float(match.group(1))
                if unit == 'billions':
                    amount *= 1000
                return amount
            except ValueError:
                continue
    return None


def check_lawsuit(notes: str) -> bool:
    """Check if lawsuit/litigation is mentioned"""
    if not notes:
        return False
    notes_lower = notes.lower()
    return any(kw in notes_lower for kw in LAWSUIT_KEYWORDS)


def determine_dispute_type(insurer_name: str, notes: str) -> str:
    """Determine if dispute is Commercial, MA, or both"""
    combined = f"{insurer_name} {notes}".lower()
    
    if 'all medicare advantage' in combined or 'all ma' in combined:
        return 'All MA'
    
    # Check for MA keywords
    is_ma = any(kw.lower() in combined for kw in MA_KEYWORDS)
    
    # Check for commercial keywords
    is_commercial = 'commercial' in combined or 'marketplace' in combined
    
    if is_ma and is_commercial:
        return 'Multi-type'
    elif is_ma:
        return 'Medicare Advantage'
    elif is_commercial:
        return 'Commercial'
    else:
        return 'Unknown'  # Will need manual review or enrichment


def extract_insurer_parent(insurer_name: str) -> tuple[str, Optional[str]]:
    """Extract normalized name and parent company from insurer field"""
    # Pattern: "UnitedHealthcare (UnitedHealth Group)"
    match = re.match(r'^(.+?)\s*\(([^)]+)\)\s*$', insurer_name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return insurer_name.strip(), None


def normalize_system_name(name: str) -> str:
    """Normalize health system name for matching"""
    # Remove common suffixes
    normalized = name
    for suffix in [' Health System', ' Health', ' Medical Center', ' Healthcare', 
                   ' Hospital', ' Hospitals', ' Regional', ' Medical']:
        normalized = normalized.replace(suffix, '')
    return normalized.strip()


# ============================================================================
# HEALTH SYSTEM HQ DATABASE
# ============================================================================

# Pre-populated HQ locations for common systems (expand as needed)
SYSTEM_HQ_DATABASE = {
    "Dignity Health": {"city": "San Francisco", "state": "CA", "lat": 37.7749, "lon": -122.4194},
    "Montefiore Health System": {"city": "Bronx", "state": "NY", "lat": 40.8448, "lon": -73.8648},
    "Northside Hospital": {"city": "Atlanta", "state": "GA", "lat": 33.7490, "lon": -84.3880},
    "Wellstar Health System": {"city": "Marietta", "state": "GA", "lat": 33.9526, "lon": -84.5499},
    "Memorial Hermann Health System": {"city": "Houston", "state": "TX", "lat": 29.7604, "lon": -95.3698},
    "Lehigh Valley Health Network": {"city": "Allentown", "state": "PA", "lat": 40.6084, "lon": -75.4902},
    "UNC Health": {"city": "Chapel Hill", "state": "NC", "lat": 35.9132, "lon": -79.0558},
    "Providence": {"city": "Renton", "state": "WA", "lat": 47.4829, "lon": -122.2171},
    "Jefferson Health": {"city": "Philadelphia", "state": "PA", "lat": 39.9526, "lon": -75.1652},
    "Mount Sinai Health System": {"city": "New York", "state": "NY", "lat": 40.7900, "lon": -73.9526},
    "Prisma Health": {"city": "Greenville", "state": "SC", "lat": 34.8526, "lon": -82.3940},
    "Scripps Health": {"city": "San Diego", "state": "CA", "lat": 32.7157, "lon": -117.1611},
    "Mayo Clinic": {"city": "Rochester", "state": "MN", "lat": 44.0225, "lon": -92.4699},
    "Mass General Brigham": {"city": "Boston", "state": "MA", "lat": 42.3601, "lon": -71.0589},
    "Johns Hopkins Medicine": {"city": "Baltimore", "state": "MD", "lat": 39.2904, "lon": -76.6122},
    "NewYork-Presbyterian": {"city": "New York", "state": "NY", "lat": 40.8408, "lon": -73.9418},
    "Ascension Texas": {"city": "Austin", "state": "TX", "lat": 30.2672, "lon": -97.7431},
    "Bon Secours Mercy Health": {"city": "Cincinnati", "state": "OH", "lat": 39.1031, "lon": -84.5120},
    "WakeMed": {"city": "Raleigh", "state": "NC", "lat": 35.7796, "lon": -78.6382},
    "Piedmont Healthcare": {"city": "Atlanta", "state": "GA", "lat": 33.7879, "lon": -84.3727},
    "Allina Health": {"city": "Minneapolis", "state": "MN", "lat": 44.9778, "lon": -93.2650},
    "M Health Fairview": {"city": "Minneapolis", "state": "MN", "lat": 44.9778, "lon": -93.2650},
    "Sanford Health": {"city": "Sioux Falls", "state": "SD", "lat": 43.5460, "lon": -96.7313},
    "Avera": {"city": "Sioux Falls", "state": "SD", "lat": 43.5460, "lon": -96.7313},
    "Corewell Health": {"city": "Grand Rapids", "state": "MI", "lat": 42.9634, "lon": -85.6681},
    "Ballad Health": {"city": "Johnson City", "state": "TN", "lat": 36.3134, "lon": -82.3535},
    "Baptist Health": {"city": "Louisville", "state": "KY", "lat": 38.2527, "lon": -85.7585},
    "Kettering Health": {"city": "Dayton", "state": "OH", "lat": 39.7589, "lon": -84.1916},
    "Salem Health": {"city": "Salem", "state": "OR", "lat": 44.9429, "lon": -123.0351},
    "Centra Health": {"city": "Lynchburg", "state": "VA", "lat": 37.4138, "lon": -79.1422},
    "VCU Health": {"city": "Richmond", "state": "VA", "lat": 37.5407, "lon": -77.4360},
    "Brown University Health": {"city": "Providence", "state": "RI", "lat": 41.8240, "lon": -71.4128},
    "Lifespan": {"city": "Providence", "state": "RI", "lat": 41.8240, "lon": -71.4128},
    "Hackensack Meridian Health": {"city": "Edison", "state": "NJ", "lat": 40.5187, "lon": -74.4121},
    "MultiCare": {"city": "Tacoma", "state": "WA", "lat": 47.2529, "lon": -122.4443},
    "South Shore Health": {"city": "Weymouth", "state": "MA", "lat": 42.2210, "lon": -70.9397},
    "Kootenai Health": {"city": "Coeur d'Alene", "state": "ID", "lat": 47.6777, "lon": -116.7805},
    "UConn Health": {"city": "Farmington", "state": "CT", "lat": 41.7270, "lon": -72.7997},
    "Bronson Healthcare": {"city": "Kalamazoo", "state": "MI", "lat": 42.2917, "lon": -85.5872},
}


def get_system_location(system_name: str) -> Dict:
    """Look up system HQ from database"""
    # Try exact match
    if system_name in SYSTEM_HQ_DATABASE:
        return SYSTEM_HQ_DATABASE[system_name]
    
    # Try normalized match
    normalized = normalize_system_name(system_name)
    for db_name, location in SYSTEM_HQ_DATABASE.items():
        if normalize_system_name(db_name) == normalized:
            return location
    
    # Try partial match
    for db_name, location in SYSTEM_HQ_DATABASE.items():
        if normalized in db_name or db_name in system_name:
            return location
    
    return {}


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_seed_row(row: Dict) -> EnrichedDispute:
    """Process a single row from the seed CSV"""
    
    # Parse insurer name and parent
    insurer_normalized, insurer_parent = extract_insurer_parent(row.get('insurer_name', ''))
    
    # Get system location
    system_name = row.get('system_name', '')
    location = get_system_location(system_name)
    
    # Extract from notes
    notes = row.get('notes', '')
    patients, patients_source = extract_patients_affected(notes)
    dates = extract_dates(notes)
    duration = extract_duration(notes)
    rate_info = extract_rate_info(notes)
    dollar_amount = extract_dollar_amount(notes)
    has_lawsuit = check_lawsuit(notes)
    dispute_type = determine_dispute_type(row.get('insurer_name', ''), notes)
    
    # Build enriched record
    dispute = EnrichedDispute(
        # Identity
        dispute_id=int(row.get('dispute_id', 0)),
        dispute_name=f"{system_name} vs {insurer_normalized} {row.get('year_first_reported', '')}",
        
        # Parties
        system_name=system_name,
        system_name_normalized=normalize_system_name(system_name),
        system_hq_city=location.get('city'),
        system_hq_state=row.get('state', location.get('state', '')),
        system_hq_lat=location.get('lat'),
        system_hq_lon=location.get('lon'),
        
        insurer_name=row.get('insurer_name', ''),
        insurer_name_normalized=insurer_normalized,
        insurer_parent=insurer_parent,
        
        # Timeline
        year_first_reported=int(row.get('year_first_reported', 0)),
        quarter_first_reported=row.get('quarter_first_reported', ''),
        first_media_date=row.get('first_media_date') or None,
        deadline_date=row.get('deadline_date') or dates.get('deadline_date'),
        oon_effective_date=dates.get('oon_effective_date'),
        resolution_date=row.get('resolution_date') or dates.get('resolution_date'),

        # Date sources
        first_media_date_source=row.get('first_media_date_source') or row.get('primary_source_url'),
        deadline_date_source=row.get('deadline_date_source') or row.get('primary_source_url'),
        oon_effective_date_source=row.get('oon_effective_date_source') or row.get('primary_source_url'),
        resolution_date_source=row.get('resolution_date_source') or row.get('primary_source_url'),

        # Status
        outcome_status=row.get('outcome_status', ''),
        
        # Impact
        patients_affected=patients,
        patients_affected_source=patients_source,
        dispute_type=dispute_type,
        
        # Negotiation
        duration_months=duration,
        rate_info_raw=rate_info,
        
        # Resolution
        lawsuit_filed=has_lawsuit,
        dollar_amount_mm=dollar_amount,
        
        # Sources
        primary_source=row.get('primary_source', ''),
        notes=notes,
        
        # Meta
        last_updated=datetime.now().isoformat(),
    )
    
    # Calculate completeness score
    dispute.data_completeness_score = calculate_completeness(dispute)
    
    return dispute


def calculate_completeness(dispute: EnrichedDispute) -> float:
    """Calculate data completeness score (0-1)"""
    fields_to_check = [
        dispute.system_hq_lat is not None,      # Has coordinates
        dispute.patients_affected is not None,   # Has patient count
        dispute.oon_effective_date is not None,  # Has OON date
        dispute.dispute_type != 'Unknown',       # Has dispute type
        dispute.insurer_parent is not None,      # Has parent company
    ]
    
    # Add resolution-specific checks
    if dispute.outcome_status == 'Resolved':
        fields_to_check.extend([
            dispute.resolution_date is not None,
        ])
    
    return sum(fields_to_check) / len(fields_to_check)


def generate_timeline_events(dispute: EnrichedDispute) -> List[TimelineEvent]:
    """Generate timeline events for animation"""
    events = []
    
    # Dispute went public
    if dispute.year_first_reported:
        quarter_month_map = {'Q1': '02', 'Q2': '05', 'Q3': '08', 'Q4': '11'}
        month = quarter_month_map.get(dispute.quarter_first_reported, '06')
        public_date = f"{dispute.year_first_reported}-{month}-01"
        
        events.append(TimelineEvent(
            event_id=f"{dispute.dispute_id}_public",
            dispute_id=dispute.dispute_id,
            event_date=public_date,
            event_type="dispute_public",
            event_description=f"Dispute between {dispute.system_name} and {dispute.insurer_name_normalized} became public",
            source=dispute.primary_source
        ))
    
    # OON effective (if we have the date)
    if dispute.oon_effective_date:
        events.append(TimelineEvent(
            event_id=f"{dispute.dispute_id}_oon",
            dispute_id=dispute.dispute_id,
            event_date=dispute.oon_effective_date,  # May need date parsing
            event_type="oon_effective",
            event_description=f"{dispute.system_name} went out-of-network with {dispute.insurer_name_normalized}",
        ))
    
    # Resolution (if resolved)
    if dispute.outcome_status == 'Resolved' and dispute.resolution_date:
        events.append(TimelineEvent(
            event_id=f"{dispute.dispute_id}_resolved",
            dispute_id=dispute.dispute_id,
            event_date=dispute.resolution_date,  # May need date parsing
            event_type="resolution",
            event_description=f"Dispute resolved between {dispute.system_name} and {dispute.insurer_name_normalized}",
        ))
    
    return events


def process_csv(input_path: str, output_dir: str = "output"):
    """Process the full seed CSV and generate enriched output"""
    
    Path(output_dir).mkdir(exist_ok=True)
    
    enriched_disputes = []
    all_timeline_events = []
    skipped = []
    
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip FTI aggregate rows
            if 'FTI Aggregate' in row.get('system_name', ''):
                skipped.append(row)
                continue
            
            # Process row
            dispute = process_seed_row(row)
            enriched_disputes.append(dispute)
            
            # Generate timeline events
            events = generate_timeline_events(dispute)
            all_timeline_events.extend(events)
    
    # Write enriched CSV
    enriched_csv_path = Path(output_dir) / "disputes_enriched.csv"
    if enriched_disputes:
        fieldnames = list(asdict(enriched_disputes[0]).keys())
        with open(enriched_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for dispute in enriched_disputes:
                writer.writerow(asdict(dispute))
    
    # Write timeline events CSV
    events_csv_path = Path(output_dir) / "timeline_events.csv"
    if all_timeline_events:
        event_fieldnames = list(asdict(all_timeline_events[0]).keys())
        with open(events_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=event_fieldnames)
            writer.writeheader()
            for event in all_timeline_events:
                writer.writerow(asdict(event))
    
    # Write JSON for Airtable import
    json_path = Path(output_dir) / "disputes_enriched.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump([asdict(d) for d in enriched_disputes], f, indent=2)
    
    # Write map-ready data (only records with coordinates)
    map_ready = [d for d in enriched_disputes if d.system_hq_lat is not None]
    map_csv_path = Path(output_dir) / "disputes_map_ready.csv"
    if map_ready:
        fieldnames = ['dispute_id', 'dispute_name', 'system_name', 'insurer_name_normalized',
                      'system_hq_lat', 'system_hq_lon', 'system_hq_state', 'system_hq_city',
                      'year_first_reported', 'quarter_first_reported', 'outcome_status',
                      'patients_affected', 'dispute_type', 'notes']
        with open(map_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for dispute in map_ready:
                row = {k: getattr(dispute, k) for k in fieldnames}
                writer.writerow(row)
    
    # Print summary
    print(f"\n{'='*60}")
    print("DISPUTE ENRICHMENT SUMMARY")
    print(f"{'='*60}")
    print(f"Total rows processed: {len(enriched_disputes)}")
    print(f"Skipped (FTI aggregates): {len(skipped)}")
    print(f"Map-ready (with coordinates): {len(map_ready)}")
    print(f"\nBy completeness score:")
    high = sum(1 for d in enriched_disputes if d.data_completeness_score >= 0.6)
    medium = sum(1 for d in enriched_disputes if 0.3 <= d.data_completeness_score < 0.6)
    low = sum(1 for d in enriched_disputes if d.data_completeness_score < 0.3)
    print(f"  High (≥60%): {high}")
    print(f"  Medium (30-60%): {medium}")
    print(f"  Low (<30%): {low}")
    print(f"\nBy outcome status:")
    for status in ['Resolved', 'OON-Ongoing', 'OON-Temporary', 'Unknown']:
        count = sum(1 for d in enriched_disputes if d.outcome_status == status)
        print(f"  {status}: {count}")
    print(f"\nPatients affected (extracted):")
    with_patients = [d for d in enriched_disputes if d.patients_affected]
    print(f"  Records with patient counts: {len(with_patients)}")
    if with_patients:
        total_patients = sum(d.patients_affected for d in with_patients)
        print(f"  Total patients affected: {total_patients:,}")
    print(f"\nOutput files:")
    print(f"  {enriched_csv_path}")
    print(f"  {events_csv_path}")
    print(f"  {json_path}")
    print(f"  {map_csv_path}")
    print(f"{'='*60}\n")
    
    return enriched_disputes, all_timeline_events


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Default input path - adjust as needed
    input_path = sys.argv[1] if len(sys.argv) > 1 else "Payer-Provider_Disputes_Seed_List_20251221.csv"
    
    if not Path(input_path).exists():
        print(f"Error: Input file not found: {input_path}")
        print("Usage: python agent/dispute_enrichment_agent.py [input_csv_path]")
        sys.exit(1)
    
    disputes, events = process_csv(input_path)
