#!/usr/bin/env python3
"""
Web search enrichment agent
Systematically searches for patient impact data for each dispute and updates records
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, Optional, List

def search_query_for_dispute(dispute: Dict) -> str:
    """Generate optimal search query for a dispute"""
    system = dispute.get('system_name', '')
    insurer = dispute.get('insurer_name_normalized', '')
    year = dispute.get('year_first_reported', '')
    
    # Clean up system name (remove parentheticals, etc.)
    system_clean = re.sub(r'\s*\([^)]*\)\s*', '', system).strip()
    
    # Generate search query
    query = f'"{system_clean}" "{insurer}" contract dispute {year} patients members affected'
    return query

def extract_patient_count_from_text(text: str) -> Optional[int]:
    """Extract patient/member count from text"""
    if not text:
        return None
    
    # Patterns to find patient counts
    patterns = [
        r'(\d{1,3}(?:,\d{3})*)\s*(?:patients|members|seniors|beneficiaries)',
        r'(?:patients|members|seniors|beneficiaries)[:\s]+(\d{1,3}(?:,\d{3})*)',
        r'impacting\s+(\d{1,3}(?:,\d{3})*)',
        r'affecting\s+(\d{1,3}(?:,\d{3})*)',
        r'(\d{1,3}(?:,\d{3})*)\s+people',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                count = int(match.group(1).replace(',', ''))
                # Sanity check - reasonable range
                if 100 <= count <= 1000000:
                    return count
            except (ValueError, IndexError):
                continue
    
    return None

def extract_date_from_text(text: str, year_hint: int = None) -> Optional[str]:
    """Extract dates from text"""
    month_map = {
        'january': '01', 'jan': '01', 'february': '02', 'feb': '02',
        'march': '03', 'mar': '03', 'april': '04', 'apr': '04',
        'may': '05', 'june': '06', 'jun': '06', 'july': '07', 'jul': '07',
        'august': '08', 'aug': '08', 'september': '09', 'sep': '09', 'sept': '09',
        'october': '10', 'oct': '10', 'november': '11', 'nov': '11',
        'december': '12', 'dec': '12',
    }
    
    # Pattern for month year
    match = re.search(r'(\w+)\s+(\d{4})', text, re.IGNORECASE)
    if match:
        month_name = match.group(1).lower()
        year = match.group(2)
        if month_name in month_map:
            return f"{year}-{month_map[month_name]}-01"
    
    # Pattern for month day, year
    match = re.search(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', text, re.IGNORECASE)
    if match:
        month_name = match.group(1).lower()
        day = match.group(2).zfill(2)
        year = match.group(3)
        if month_name in month_map:
            return f"{year}-{month_map[month_name]}-{day}"
    
    return None

def process_dispute_with_search(dispute: Dict, search_results: str) -> Dict:
    """Process dispute with web search results"""
    updates = {}
    enrichment_note_parts = []
    
    # Extract patient count
    patient_count = extract_patient_count_from_text(search_results)
    if patient_count and (not dispute.get('patients_affected') or dispute.get('patients_affected') == ''):
        updates['patients_affected'] = patient_count
        updates['patients_affected_source'] = 'web_search'
        enrichment_note_parts.append(f"Found {patient_count:,} patients via web search")
    
    # Extract dates if missing
    if not dispute.get('oon_effective_date') or dispute.get('oon_effective_date') == '':
        oon_date = extract_date_from_text(search_results)
        if oon_date:
            updates['oon_effective_date'] = oon_date
            enrichment_note_parts.append(f"Extracted OON date: {oon_date}")
    
    if dispute.get('outcome_status') == 'Resolved' and (not dispute.get('resolution_date') or dispute.get('resolution_date') == ''):
        resolution_date = extract_date_from_text(search_results)
        if resolution_date:
            updates['resolution_date'] = resolution_date
            enrichment_note_parts.append(f"Extracted resolution date: {resolution_date}")
    
    # Update enrichment notes
    if enrichment_note_parts:
        existing_notes = dispute.get('enrichment_notes', '')
        if existing_notes:
            updates['enrichment_notes'] = f"{existing_notes}; Web search enrichment {datetime.now().strftime('%Y-%m-%d')}: {'; '.join(enrichment_note_parts)}"
        else:
            updates['enrichment_notes'] = f"Web search enrichment {datetime.now().strftime('%Y-%m-%d')}: {'; '.join(enrichment_note_parts)}"
    
    return updates

def calculate_completeness(dispute: Dict) -> float:
    """Recalculate completeness score"""
    checks = []
    checks.append(bool(dispute.get('system_hq_lat')))
    checks.append(bool(dispute.get('patients_affected')))
    checks.append(bool(dispute.get('oon_effective_date')))
    checks.append(dispute.get('dispute_type') and dispute.get('dispute_type') != 'Unknown')
    checks.append(bool(dispute.get('insurer_parent')))
    if dispute.get('outcome_status') == 'Resolved':
        checks.append(bool(dispute.get('resolution_date')))
    return sum(checks) / len(checks)

def main():
    """Main enrichment process"""
    # Read disputes
    disputes = []
    with open('output/disputes_enriched.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        disputes = list(reader)
    
    # Find disputes needing patient counts
    needs_research = []
    for d in disputes:
        if not d.get('patients_affected') or d.get('patients_affected') == '':
            needs_research.append(d)
    
    print(f"Found {len(needs_research)} disputes needing patient impact research")
    print(f"\nGenerating search queries for first 10 disputes:\n")
    
    # Generate search queries
    search_queries = []
    for i, dispute in enumerate(needs_research[:10], 1):
        query = search_query_for_dispute(dispute)
        print(f"{i}. ID {dispute['dispute_id']}: {dispute['system_name']} vs {dispute['insurer_name_normalized']} ({dispute['year_first_reported']})")
        print(f"   Query: {query}\n")
        search_queries.append((dispute, query))
    
    print("\n" + "="*80)
    print("NOTE: The web search tool needs to be called manually for each query above.")
    print("After getting search results, you can:")
    print("1. Call process_dispute_with_search() with the dispute and search results")
    print("2. Or manually review and update the CSV")
    print("="*80)
    
    # Save search queries to file for manual processing
    queries_file = {
        'generated': datetime.now().isoformat(),
        'total_needing_research': len(needs_research),
        'queries': [
            {
                'dispute_id': d['dispute_id'],
                'dispute_name': d['dispute_name'],
                'system': d['system_name'],
                'insurer': d['insurer_name_normalized'],
                'year': d['year_first_reported'],
                'query': q
            }
            for d, q in search_queries[:20]  # First 20
        ]
    }
    
    with open('web_search_queries.json', 'w') as f:
        json.dump(queries_file, f, indent=2)
    
    print(f"\nSaved search queries to web_search_queries.json")

if __name__ == "__main__":
    main()

