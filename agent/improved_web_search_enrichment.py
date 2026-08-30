#!/usr/bin/env python3
"""
Improved Web Search Enrichment Agent
Uses better search query formats and processes results more effectively
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, Optional, List, Tuple

def generate_optimized_search_queries(dispute: Dict) -> List[str]:
    """
    Generate multiple optimized search queries for a dispute
    Different query formats can catch different articles
    """
    system = dispute.get('system_name', '')
    insurer = dispute.get('insurer_name_normalized', '')
    year = dispute.get('year_first_reported', '')
    state = dispute.get('system_hq_state', '')
    
    # Clean system name (remove parentheticals, common suffixes)
    system_clean = re.sub(r'\s*\([^)]*\)\s*', '', system).strip()
    system_clean = re.sub(r'\s+Health System$|\s+Health$|\s+Healthcare$', '', system_clean).strip()
    
    # Clean insurer name
    insurer_clean = insurer.strip()
    
    queries = []
    
    # Query 1: Exact match with quotes (most specific)
    queries.append(f'"{system_clean}" "{insurer_clean}" contract dispute {year} patients affected')
    
    # Query 2: System name + insurer + out of network
    queries.append(f'"{system_clean}" "{insurer_clean}" out of network {year} members')
    
    # Query 3: Add state context if available
    if state:
        queries.append(f'"{system_clean}" "{insurer_clean}" {state} contract {year} patients')
    
    # Query 4: Without quotes (broader match)
    queries.append(f'{system_clean} {insurer_clean} contract dispute {year} how many patients')
    
    # Query 5: News site specific
    queries.append(f'site:beckerhospitalreview.com OR site:modernhealthcare.com "{system_clean}" "{insurer_clean}" {year}')
    
    # Query 6: Hospital name + insurer + "members" or "patients"
    queries.append(f'"{system_clean}" "{insurer_clean}" {year} members patients contract')
    
    return queries

def extract_patient_count_improved(text: str) -> Optional[Tuple[int, str]]:
    """
    Improved patient count extraction with more patterns
    Returns (count, context) tuple
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # More comprehensive patterns - ordered by specificity
    patterns = [
        # Specific phrases with numbers
        (r'(\d{1,3}(?:,\d{3})*)\s*(?:patients|members|seniors|beneficiaries|enrollees|covered lives)', 'direct_count'),
        (r'(?:patients|members|seniors|beneficiaries|enrollees)[:\s]+(?:approximately|about|more than|over|nearly|up to)?\s*(\d{1,3}(?:,\d{3})*)', 'after_label'),
        (r'impacting\s+(?:approximately|about|more than|over|nearly)?\s*(\d{1,3}(?:,\d{3})*)', 'impacting'),
        (r'affecting\s+(?:approximately|about|more than|over|nearly)?\s*(\d{1,3}(?:,\d{3})*)', 'affecting'),
        (r'(\d{1,3}(?:,\d{3})*)\s+people\s+(?:are|will be|would be)', 'people_affected'),
        # Patterns with insurer name
        (r'(\d{1,3}(?:,\d{3})*)\s+(?:UnitedHealthcare|UHC|Aetna|Humana|Cigna|Anthem|BCBS|Blue Cross)\s+members', 'insurer_members'),
        # "X thousand" format
        (r'(\d{1,2}(?:\.\d)?)\s+thousand\s+(?:patients|members)', 'thousands'),
    ]
    
    found_counts = []
    
    for pattern, pattern_type in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                count_str = match.group(1)
                
                # Handle "X thousand" format
                if pattern_type == 'thousands':
                    count = int(float(count_str) * 1000)
                else:
                    count = int(count_str.replace(',', ''))
                
                # Sanity checks - reasonable range for health disputes
                if 100 <= count <= 1000000:
                    # Get context (50 chars before and after)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end].strip()
                    
                    found_counts.append((count, context, pattern_type))
            except (ValueError, IndexError):
                continue
    
    # Return the most specific match (prefer direct_count, then after_label, etc.)
    if found_counts:
        # Sort by pattern specificity
        priority = {'direct_count': 1, 'after_label': 2, 'insurer_members': 3, 
                   'impacting': 4, 'affecting': 5, 'people_affected': 6, 'thousands': 7}
        
        found_counts.sort(key=lambda x: priority.get(x[2], 99))
        best_match = found_counts[0]
        return (best_match[0], best_match[1])
    
    return None

def extract_dates_improved(text: str, year_hint: int = None) -> Dict[str, Optional[str]]:
    """
    Improved date extraction from text
    Returns dict with oon_effective_date, resolution_date, deadline_date
    """
    dates = {'oon_effective_date': None, 'deadline_date': None, 'resolution_date': None}
    
    if not text:
        return dates
    
    month_map = {
        'january': '01', 'jan': '01', 'february': '02', 'feb': '02',
        'march': '03', 'mar': '03', 'april': '04', 'apr': '04',
        'may': '05', 'june': '06', 'jun': '06', 'july': '07', 'jul': '07',
        'august': '08', 'aug': '08', 'september': '09', 'sep': '09', 'sept': '09',
        'october': '10', 'oct': '10', 'november': '11', 'nov': '11',
        'december': '12', 'dec': '12',
    }
    
    def parse_date(date_str: str) -> Optional[str]:
        """Parse date string to YYYY-MM-DD"""
        # Pattern: Month Day, Year
        match = re.search(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', date_str, re.IGNORECASE)
        if match:
            month_name = match.group(1).lower()
            day = match.group(2).zfill(2)
            year = match.group(3)
            if month_name in month_map:
                return f"{year}-{month_map[month_name]}-{day}"
        
        # Pattern: Month Year
        match = re.search(r'(\w+)\s+(\d{4})', date_str, re.IGNORECASE)
        if match:
            month_name = match.group(1).lower()
            year = match.group(2)
            if month_name in month_map:
                return f"{year}-{month_map[month_name]}-01"
        
        return None
    
    # OON effective date patterns
    oon_patterns = [
        r'(?:went|goes|going)\s+out[-\s]of[-\s]network\s+(?:on|effective)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'out[-\s]of[-\s]network\s+(?:effective|on)\s+(\w+\s+\d{1,2},?\s+\d{4})',
        r'OON\s+(?:effective|on)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'terminated\s+(?:on|effective)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'contract\s+(?:expired|ended)\s+(?:on)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'ended\s+(\w+\s+\d{1,2},?\s+\d{4})',
    ]
    
    for pattern in oon_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and not dates['oon_effective_date']:
            parsed = parse_date(match.group(1))
            if parsed:
                dates['oon_effective_date'] = parsed
                break
    
    # Resolution date patterns
    resolution_patterns = [
        r'resolved\s+(?:on|in)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'reached\s+(?:an\s+)?agreement\s+(?:on|in)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'deal\s+(?:was\s+)?reached\s+(?:on|in)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'settled\s+(?:on|in)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
    ]
    
    for pattern in resolution_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and not dates['resolution_date']:
            parsed = parse_date(match.group(1))
            if parsed:
                dates['resolution_date'] = parsed
                break
    
    # Deadline patterns
    deadline_patterns = [
        r'contract\s+(?:expires|expired|expiring)\s+(?:on)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
        r'deadline\s+(?:of|is)?\s*(\w+\s+\d{1,2},?\s+\d{4})',
    ]
    
    for pattern in deadline_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and not dates['deadline_date']:
            parsed = parse_date(match.group(1))
            if parsed:
                dates['deadline_date'] = parsed
                break
    
    return dates

def process_search_result_for_dispute(dispute: Dict, search_result_text: str, source_url: str = None) -> Dict:
    """
    Process web search result text and extract relevant information
    Returns dict of updates to apply to dispute record

    Args:
        dispute: Dispute record dict
        search_result_text: Text content from web search
        source_url: URL of the source (for date attribution)
    """
    updates = {}
    enrichment_notes = []

    if not search_result_text:
        return updates

    # Extract patient count
    patient_data = extract_patient_count_improved(search_result_text)
    current_patients = dispute.get('patients_affected', '')

    if patient_data:
        patient_count, context = patient_data
        if not current_patients or current_patients == '':
            updates['patients_affected'] = patient_count
            updates['patients_affected_source'] = 'web_search_extracted'
            enrichment_notes.append(f"Found {patient_count:,} patients/members via web search (context: {context[:100]}...)")
        elif int(current_patients) != patient_count:
            # Different number found - note but don't overwrite without validation
            enrichment_notes.append(f"Web search found {patient_count:,} patients (existing: {current_patients}) - needs validation")

    # Extract dates
    dates = extract_dates_improved(search_result_text)
    year = int(dispute.get('year_first_reported', 0) or 0)

    # Fallback source URL if not provided
    if not source_url:
        source_url = dispute.get('primary_source_url', '')

    # OON date
    if dates['oon_effective_date']:
        if not dispute.get('oon_effective_date') or dispute.get('oon_effective_date') == '':
            updates['oon_effective_date'] = dates['oon_effective_date']
            updates['oon_effective_date_source'] = source_url
            enrichment_notes.append(f"Extracted OON date: {dates['oon_effective_date']}")

    # Resolution date (if resolved)
    if dispute.get('outcome_status') == 'Resolved' and dates['resolution_date']:
        if not dispute.get('resolution_date') or dispute.get('resolution_date') == '':
            updates['resolution_date'] = dates['resolution_date']
            updates['resolution_date_source'] = source_url
            enrichment_notes.append(f"Extracted resolution date: {dates['resolution_date']}")

    # Deadline date
    if dates['deadline_date']:
        if not dispute.get('deadline_date') or dispute.get('deadline_date') == '':
            updates['deadline_date'] = dates['deadline_date']
            updates['deadline_date_source'] = source_url
    
    # Update enrichment notes
    if enrichment_notes:
        existing_notes = dispute.get('enrichment_notes', '')
        timestamp = datetime.now().strftime('%Y-%m-%d')
        if existing_notes:
            updates['enrichment_notes'] = f"{existing_notes}; Web search enrichment {timestamp}: {'; '.join(enrichment_notes)}"
        else:
            updates['enrichment_notes'] = f"Web search enrichment {timestamp}: {'; '.join(enrichment_notes)}"
    
    return updates

def update_dispute_record(dispute_id: int, updates: Dict, csv_path: str = 'output/disputes_enriched.csv') -> bool:
    """
    Update a specific dispute record in the CSV file
    """
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

def enrich_dispute(dispute_id: int, search_result_text: str) -> Dict:
    """
    Main function to enrich a dispute with web search results
    Returns dict with success status and updates made
    """
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
        return {'success': False, 'error': f'Dispute ID {dispute_id} not found'}
    
    # Process search results
    updates = process_search_result_for_dispute(dispute, search_result_text)
    
    if updates:
        # Update the CSV
        success = update_dispute_record(dispute_id, updates)
        if success:
            return {
                'success': True,
                'dispute_id': dispute_id,
                'updates': updates,
                'message': f'Successfully updated dispute ID {dispute_id}'
            }
        else:
            return {'success': False, 'error': 'Failed to update CSV file'}
    
    return {'success': False, 'error': 'No new data extracted from search results'}

# Batch processing functions
def generate_search_queries_for_batch(dispute_ids: List[int] = None, limit: int = 10) -> List[Dict]:
    """
    Generate optimized search queries for a batch of disputes
    """
    disputes = []
    with open('output/disputes_enriched.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        disputes = list(reader)
    
    # Filter disputes needing research
    needs_research = []
    for d in disputes:
        if not d.get('patients_affected') or d.get('patients_affected') == '':
            if dispute_ids is None or int(d.get('dispute_id', 0)) in dispute_ids:
                needs_research.append(d)
    
    # Limit
    needs_research = needs_research[:limit]
    
    # Generate queries
    queries_list = []
    for dispute in needs_research:
        queries = generate_optimized_search_queries(dispute)
        queries_list.append({
            'dispute_id': dispute.get('dispute_id'),
            'dispute_name': dispute.get('dispute_name'),
            'system': dispute.get('system_name'),
            'insurer': dispute.get('insurer_name_normalized'),
            'year': dispute.get('year_first_reported'),
            'queries': queries,
            'recommended_query': queries[0]  # Most specific query first
        })
    
    return queries_list

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'generate':
        # Generate queries
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        queries = generate_search_queries_for_batch(limit=limit)
        
        print(f"Generated {len(queries)} search query sets\n")
        for item in queries:
            print(f"Dispute ID {item['dispute_id']}: {item['dispute_name']}")
            print(f"  Recommended: {item['recommended_query']}")
            print(f"  Alternative queries: {len(item['queries']) - 1}")
            print()
        
        # Save to file
        with open('improved_search_queries.json', 'w') as f:
            json.dump(queries, f, indent=2)
        print(f"Saved to improved_search_queries.json")
    else:
        print("Improved Web Search Enrichment Agent")
        print("="*60)
        print("\nUsage:")
        print("  python agent/improved_web_search_enrichment.py generate [limit]")
        print("    - Generate optimized search queries")
        print("\n  from improved_web_search_enrichment import enrich_dispute")
        print("  result = enrich_dispute(dispute_id, search_result_text)")
        print("="*60)

