#!/usr/bin/env python3
"""
Automated web search enrichment - searches for each dispute and extracts patient impact data
This script can be run to systematically research disputes via web search
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, Optional, Tuple

def extract_patient_count_from_text(text: str) -> Optional[int]:
    """Extract patient/member count from text - improved patterns"""
    if not text:
        return None
    
    # More comprehensive patterns
    patterns = [
        r'(\d{1,3}(?:,\d{3})*)\s*(?:patients|members|seniors|beneficiaries|enrollees)',
        r'(?:patients|members|seniors|beneficiaries)[:\s]+(?:approximately|about|more than|over)?\s*(\d{1,3}(?:,\d{3})*)',
        r'impacting\s+(?:approximately|about)?\s*(\d{1,3}(?:,\d{3})*)',
        r'affecting\s+(?:approximately|about)?\s*(\d{1,3}(?:,\d{3})*)',
        r'(\d{1,3}(?:,\d{3})*)\s+people',
        r'(\d{1,3}(?:,\d{3})*)\s+(?:UHC|UnitedHealthcare|Aetna|Humana|Cigna|Anthem|BCBS|Blue Cross)\s+members',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                count = int(match.group(1).replace(',', ''))
                # Sanity check - reasonable range for health disputes
                if 100 <= count <= 1000000:
                    return count
            except (ValueError, IndexError):
                continue
    
    return None

def extract_oon_date_from_text(text: str, year_hint: int = None) -> Optional[str]:
    """Extract OON effective date from text"""
    month_map = {
        'january': '01', 'jan': '01', 'february': '02', 'feb': '02',
        'march': '03', 'mar': '03', 'april': '04', 'apr': '04',
        'may': '05', 'june': '06', 'jun': '06', 'july': '07', 'jul': '07',
        'august': '08', 'aug': '08', 'september': '09', 'sep': '09', 'sept': '09',
        'october': '10', 'oct': '10', 'november': '11', 'nov': '11',
        'december': '12', 'dec': '12',
    }
    
    # Look for OON effective date patterns
    oon_patterns = [
        r'(?:went|goes|going)\s+out[-\s]of[-\s]network\s+(?:on|effective)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'out[-\s]of[-\s]network\s+(?:effective|on)\s+(\w+\s+\d{1,2},?\s+\d{4})',
        r'terminated\s+(?:on|effective)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'contract\s+(?:expired|ended)\s+(?:on)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
    ]
    
    for pattern in oon_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            # Parse month day, year
            m = re.search(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', date_str, re.IGNORECASE)
            if m:
                month_name = m.group(1).lower()
                day = m.group(2).zfill(2)
                year = m.group(3)
                if month_name in month_map:
                    return f"{year}-{month_map[month_name]}-{day}"
    
    return None

def process_search_results(dispute: Dict, search_text: str) -> Dict:
    """Process web search results and return updates for dispute"""
    updates = {}
    notes = []
    
    # Extract patient count
    patient_count = extract_patient_count_from_text(search_text)
    current_patients = dispute.get('patients_affected', '')
    
    if patient_count:
        if not current_patients or current_patients == '':
            updates['patients_affected'] = patient_count
            updates['patients_affected_source'] = 'web_search_extracted'
            notes.append(f"Extracted {patient_count:,} patients/members from web search")
        elif int(current_patients) != patient_count:
            # Different number found - note the discrepancy
            notes.append(f"Web search found {patient_count:,} patients (current: {current_patients})")
    
    # Extract OON date
    if not dispute.get('oon_effective_date') or dispute.get('oon_effective_date') == '':
        oon_date = extract_oon_date_from_text(search_text)
        if oon_date:
            updates['oon_effective_date'] = oon_date
            notes.append(f"Extracted OON date: {oon_date}")
    
    # Update enrichment notes
    if notes:
        existing = dispute.get('enrichment_notes', '')
        timestamp = datetime.now().strftime('%Y-%m-%d')
        if existing:
            updates['enrichment_notes'] = f"{existing}; Web search {timestamp}: {'; '.join(notes)}"
        else:
            updates['enrichment_notes'] = f"Web search {timestamp}: {'; '.join(notes)}"
    
    return updates

def update_dispute_in_csv(dispute_id: int, updates: Dict, csv_path: str = 'output/disputes_enriched.csv'):
    """Update a specific dispute in the CSV file"""
    disputes = []
    
    # Read all disputes
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        disputes = list(reader)
    
    # Find and update the dispute
    updated = False
    for dispute in disputes:
        if int(dispute.get('dispute_id', 0)) == dispute_id:
            dispute.update(updates)
            
            # Recalculate completeness
            checks = []
            checks.append(bool(dispute.get('system_hq_lat')))
            checks.append(bool(dispute.get('patients_affected')))
            checks.append(bool(dispute.get('oon_effective_date')))
            checks.append(dispute.get('dispute_type') and dispute.get('dispute_type') != 'Unknown')
            checks.append(bool(dispute.get('insurer_parent')))
            if dispute.get('outcome_status') == 'Resolved':
                checks.append(bool(dispute.get('resolution_date')))
            dispute['data_completeness_score'] = sum(checks) / len(checks)
            dispute['last_updated'] = datetime.now().isoformat()
            updated = True
            break
    
    if updated:
        # Write back
        fieldnames = list(disputes[0].keys())
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(disputes)
        return True
    return False

# Example usage function
def enrich_dispute_with_search_result(dispute_id: int, search_result_text: str):
    """Main function to enrich a dispute with web search results"""
    # Read the dispute
    disputes = []
    with open('output/disputes_enriched.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        disputes = list(reader)
    
    dispute = None
    for d in disputes:
        if int(d.get('dispute_id', 0)) == dispute_id:
            dispute = d
            break
    
    if not dispute:
        print(f"Dispute ID {dispute_id} not found")
        return False
    
    # Process search results
    updates = process_search_results(dispute, search_result_text)
    
    if updates:
        # Update the CSV
        success = update_dispute_in_csv(dispute_id, updates)
        if success:
            print(f"Successfully updated dispute ID {dispute_id}")
            if 'patients_affected' in updates:
                print(f"  - Added patient count: {updates['patients_affected']:,}")
            if 'oon_effective_date' in updates:
                print(f"  - Added OON date: {updates['oon_effective_date']}")
            return True
    
    print(f"No new data extracted for dispute ID {dispute_id}")
    return False

if __name__ == "__main__":
    print("Web Search Enrichment Helper")
    print("="*60)
    print("\nThis script provides functions to:")
    print("1. Extract patient counts and dates from web search results")
    print("2. Update dispute records with extracted data")
    print("\nUsage example:")
    print("  from automated_web_search_enrichment import enrich_dispute_with_search_result")
    print("  enrich_dispute_with_search_result(1, search_result_text)")
    print("\nOr use the web search tool and pass results to process_search_results()")
    print("="*60)

