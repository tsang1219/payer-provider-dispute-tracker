#!/usr/bin/env python3
"""
Batch enrichment script to systematically improve dispute records
by parsing notes, extracting dates, and filling missing system data.
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

def parse_date_string(date_str: str, year_hint: int = None) -> Optional[str]:
    """Parse date string to YYYY-MM-DD format"""
    if not date_str:
        return None
    
    # Try common formats
    patterns = [
        (r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', '%B %d %Y'),  # "October 31, 2023"
        (r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', '%b %d %Y'),  # "Oct 31, 2023"
        (r'(\w+)\s+(\d{4})', '%B %Y'),  # "April 2024"
        (r'(\w+)\s+(\d{4})', '%b %Y'),  # "Apr 2024"
    ]
    
    # Month name mapping
    month_map = {
        'january': '01', 'jan': '01',
        'february': '02', 'feb': '02',
        'march': '03', 'mar': '03',
        'april': '04', 'apr': '04',
        'may': '05',
        'june': '06', 'jun': '06',
        'july': '07', 'jul': '07',
        'august': '08', 'aug': '08',
        'september': '09', 'sep': '09', 'sept': '09',
        'october': '10', 'oct': '10',
        'november': '11', 'nov': '11',
        'december': '12', 'dec': '12',
    }
    
    # Try to extract month day year pattern
    match = re.search(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', date_str, re.IGNORECASE)
    if match:
        month_name = match.group(1).lower()
        day = match.group(2).zfill(2)
        year = match.group(3)
        if month_name in month_map:
            return f"{year}-{month_map[month_name]}-{day}"
    
    # Try month year only
    match = re.search(r'(\w+)\s+(\d{4})', date_str, re.IGNORECASE)
    if match:
        month_name = match.group(1).lower()
        year = match.group(2)
        if month_name in month_map:
            return f"{year}-{month_map[month_name]}-01"
    
    return None

def extract_all_dates(notes: str, year: int) -> Dict[str, Optional[str]]:
    """Extract all possible dates from notes"""
    if not notes:
        return {'oon_effective_date': None, 'deadline_date': None, 'resolution_date': None}
    
    dates = {'oon_effective_date': None, 'deadline_date': None, 'resolution_date': None}
    
    # OON effective patterns
    oon_patterns = [
        r'OON\s+(?:effective\s+)?(\w+\s+\d{1,2},?\s+\d{4})',
        r'OON\s+(\w+\s+\d{4})',
        r'went\s+out[-\s]of[-\s]network\s+(\w+\s+\d{1,2},?\s+\d{4})',
        r'terminated\s+(\w+\s+\d{1,2},?\s+\d{4})',
        r'ended\s+(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4}).*OON',
    ]
    
    for pattern in oon_patterns:
        match = re.search(pattern, notes, re.IGNORECASE)
        if match and not dates['oon_effective_date']:
            dates['oon_effective_date'] = parse_date_string(match.group(1), year)
            break
    
    # Deadline patterns
    deadline_patterns = [
        r'contract\s+(?:expired|expiring|ended|terminated)\s+(\w+\s+\d{1,2},?\s+\d{4})',
        r'deadline\s+(\w+\s+\d{4})',
        r'expiring\s+(\w+\s+\d{4})',
    ]
    
    for pattern in deadline_patterns:
        match = re.search(pattern, notes, re.IGNORECASE)
        if match and not dates['deadline_date']:
            dates['deadline_date'] = parse_date_string(match.group(1), year)
            break
    
    # Resolution patterns
    resolution_patterns = [
        r'resolved\s+(\w+\s+\d{1,2},?\s+\d{4})',
        r'resolved\s+(\w+\s+\d{4})',
        r'deal\s+(?:reached\s+)?(\w+\s+\d{4})',
        r'agreement\s+(\w+\s+\d{4})',
    ]
    
    for pattern in resolution_patterns:
        match = re.search(pattern, notes, re.IGNORECASE)
        if match and not dates['resolution_date']:
            dates['resolution_date'] = parse_date_string(match.group(1), year)
            break
    
    return dates

def extract_patient_count(notes: str) -> Tuple[Optional[int], Optional[str]]:
    """Extract patient/member count from notes"""
    if not notes:
        return None, None
    
    patterns = [
        (r'(\d{1,3}(?:,\d{3})*)\s*patients', 'patients'),
        (r'(\d{1,3}(?:,\d{3})*)\s*members', 'members'),
        (r'(\d{1,3}(?:,\d{3})*)\s*seniors', 'seniors'),
        (r'(\d{1,3}(?:,\d{3})*)\s*children', 'children'),
    ]
    
    for pattern, source_type in patterns:
        match = re.search(pattern, notes, re.IGNORECASE)
        if match:
            try:
                count = int(match.group(1).replace(',', ''))
                return count, f"extracted_from_notes_{source_type}"
            except ValueError:
                continue
    
    return None, None

def load_health_systems() -> Dict:
    """Load health systems reference data"""
    ref_path = Path('health_systems_reference.json')
    if ref_path.exists():
        with open(ref_path, 'r') as f:
            return json.load(f)
    return {}

def find_system_in_reference(system_name: str, systems_ref: Dict) -> Optional[Dict]:
    """Find system data in reference by name matching"""
    system_name_lower = system_name.lower().strip()
    
    for key, system_data in systems_ref.items():
        name_variants = [system_data.get('name', '').lower()]
        name_variants.extend([v.lower() for v in system_data.get('name_variants', [])])
        
        # Try exact match first
        for variant in name_variants:
            if variant == system_name_lower:
                return system_data
        
        # Try normalized matching
        normalized_input = system_name_lower.replace(' health system', '').replace(' health', '').replace(' healthcare', '').replace(' hospital', '')
        
        for variant in name_variants:
            normalized_variant = variant.replace(' health system', '').replace(' health', '').replace(' healthcare', '').replace(' hospital', '')
            
            # Check if one contains the other (after normalization)
            if normalized_variant in normalized_input or normalized_input in normalized_variant:
                return system_data
            
            # Check if core name matches (e.g., "Phoenix Children's" matches "Phoenix Children's Hospital")
            if len(normalized_variant) > 5 and len(normalized_input) > 5:
                if normalized_variant in system_name_lower or system_name_lower in normalized_variant:
                    return system_data
    
    # Try partial matching for complex names
    # Handle cases like "Southwestern Health Resources/Texas Health/UT Southwestern"
    if '/' in system_name:
        parts = [p.strip() for p in system_name.split('/')]
        for part in parts:
            result = find_system_in_reference(part, systems_ref)
            if result:
                return result
    
    return None

def calculate_completeness(row: Dict) -> float:
    """Calculate data completeness score"""
    checks = []
    
    # Check coordinates
    checks.append(bool(row.get('system_hq_lat')))
    
    # Check patient count
    checks.append(bool(row.get('patients_affected')))
    
    # Check OON date
    checks.append(bool(row.get('oon_effective_date')))
    
    # Check dispute type
    checks.append(row.get('dispute_type') and row.get('dispute_type') != 'Unknown')
    
    # Check insurer parent
    checks.append(bool(row.get('insurer_parent')))
    
    # Resolution-specific
    if row.get('outcome_status') == 'Resolved':
        checks.append(bool(row.get('resolution_date')))
    
    return sum(checks) / len(checks)

def enrich_disputes_batch(input_csv: str, output_csv: str, batch_size: int = None, start_id: int = None):
    """Enrich disputes in batches"""
    
    # Load health systems reference
    systems_ref = load_health_systems()
    
    # Read all disputes
    disputes = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        disputes = list(reader)
    
    enriched_count = 0
    
    for dispute in disputes:
        dispute_id = int(dispute.get('dispute_id', 0))
        
        # Skip if before start_id
        if start_id and dispute_id < start_id:
            continue
        
        # Skip if batch limit reached
        if batch_size and enriched_count >= batch_size:
            break
        
        notes = dispute.get('notes', '')
        year = int(dispute.get('year_first_reported', 0))
        
        # Extract dates if missing
        if not dispute.get('oon_effective_date') or not dispute.get('deadline_date'):
            dates = extract_all_dates(notes, year)
            primary_source_url = dispute.get('primary_source_url', '')

            if dates['oon_effective_date'] and not dispute.get('oon_effective_date'):
                dispute['oon_effective_date'] = dates['oon_effective_date']
                # Set source - extracted from notes, so use primary source
                if not dispute.get('oon_effective_date_source'):
                    dispute['oon_effective_date_source'] = primary_source_url

            if dates['deadline_date'] and not dispute.get('deadline_date'):
                dispute['deadline_date'] = dates['deadline_date']
                if not dispute.get('deadline_date_source'):
                    dispute['deadline_date_source'] = primary_source_url

            if dates['resolution_date'] and not dispute.get('resolution_date'):
                dispute['resolution_date'] = dates['resolution_date']
                if not dispute.get('resolution_date_source'):
                    dispute['resolution_date_source'] = primary_source_url
        
        # Extract patient count if missing
        if not dispute.get('patients_affected'):
            patients, source = extract_patient_count(notes)
            if patients:
                dispute['patients_affected'] = patients
                dispute['patients_affected_source'] = source
        
        # Fill in system data from reference if missing
        system_name = dispute.get('system_name', '')
        system_data = find_system_in_reference(system_name, systems_ref)
        
        if system_data:
            if not dispute.get('system_hq_lat') and system_data.get('hq_lat'):
                dispute['system_hq_lat'] = system_data.get('hq_lat')
                dispute['system_hq_lon'] = system_data.get('hq_lon')
                dispute['system_hq_city'] = system_data.get('hq_city')
                dispute['system_hq_state'] = system_data.get('hq_state')
            
            if not dispute.get('system_hospital_count') and system_data.get('hospital_count'):
                dispute['system_hospital_count'] = system_data.get('hospital_count')
            
            if not dispute.get('system_annual_revenue_mm') and system_data.get('annual_revenue_mm'):
                dispute['system_annual_revenue_mm'] = system_data.get('annual_revenue_mm')
        
        # Recalculate completeness
        dispute['data_completeness_score'] = calculate_completeness(dispute)
        dispute['last_updated'] = datetime.now().isoformat()
        
        # Add enrichment note
        if dispute.get('enrichment_notes'):
            dispute['enrichment_notes'] += f"; Batch enriched {datetime.now().strftime('%Y-%m-%d')}"
        else:
            dispute['enrichment_notes'] = f"Batch enriched {datetime.now().strftime('%Y-%m-%d')}"
        
        enriched_count += 1
    
    # Write back
    if disputes:
        fieldnames = list(disputes[0].keys())
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(disputes)
    
    print(f"Enriched {enriched_count} disputes")
    return enriched_count

if __name__ == "__main__":
    import sys

    input_file = "output/disputes_enriched.csv"
    output_file = "output/disputes_enriched.csv"
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else None
    start_id = int(sys.argv[2]) if len(sys.argv) > 2 else None

    enrich_disputes_batch(input_file, output_file, batch_size, start_id)

    # Run patient estimation agent to fill remaining missing patient counts
    print("\nRunning patient estimation agent...")
    from agent.patient_estimation_agent import process_disputes, print_estimation_report
    total, added, updates = process_disputes(output_file)
    print(f"Patient estimation: processed {total} disputes, added estimates for {added}")
    print_estimation_report(updates)

