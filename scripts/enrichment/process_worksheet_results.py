#!/usr/bin/env python3
"""
Process completed worksheet results and update enriched disputes CSV
Reads search_query_worksheet.csv and updates disputes_enriched.csv with found data
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, Optional

def parse_patient_count(text: str) -> Optional[int]:
    """Parse patient count from text"""
    if not text:
        return None
    
    # Remove commas, try to convert
    try:
        text_clean = text.replace(',', '').strip()
        count = int(text_clean)
        if 100 <= count <= 1000000:  # Reasonable range
            return count
    except ValueError:
        pass
    
    return None

def parse_date(text: str) -> Optional[str]:
    """Parse date to YYYY-MM-DD format"""
    if not text:
        return None
    
    text = text.strip()
    
    # Already in YYYY-MM-DD format?
    if re.match(r'^\d{4}-\d{2}-\d{2}$', text):
        return text
    
    # Try to parse various formats
    month_map = {
        'january': '01', 'jan': '01', 'february': '02', 'feb': '02',
        'march': '03', 'mar': '03', 'april': '04', 'apr': '04',
        'may': '05', 'june': '06', 'jun': '06', 'july': '07', 'jul': '07',
        'august': '08', 'aug': '08', 'september': '09', 'sep': '09', 'sept': '09',
        'october': '10', 'oct': '10', 'november': '11', 'nov': '11',
        'december': '12', 'dec': '12',
    }
    
    # Month Day, Year format
    match = re.search(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', text, re.IGNORECASE)
    if match:
        month_name = match.group(1).lower()
        day = match.group(2).zfill(2)
        year = match.group(3)
        if month_name in month_map:
            return f"{year}-{month_map[month_name]}-{day}"
    
    # Month Year format
    match = re.search(r'(\w+)\s+(\d{4})', text, re.IGNORECASE)
    if match:
        month_name = match.group(1).lower()
        year = match.group(2)
        if month_name in month_map:
            return f"{year}-{month_map[month_name]}-01"
    
    return None

def process_worksheet_results(worksheet_csv: str = 'search_query_worksheet.csv', 
                              output_csv: str = 'output/disputes_enriched.csv'):
    """Process worksheet and update enriched disputes"""
    
    # Read worksheet
    worksheet_rows = []
    with open(worksheet_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        worksheet_rows = list(reader)
    
    # Read disputes
    disputes = []
    with open(output_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        disputes = list(reader)
    
    # Create lookup
    worksheet_lookup = {row['dispute_id']: row for row in worksheet_rows if row.get('processed', '').strip().upper() in ['YES', 'Y', 'X', 'DONE']}
    
    updates_made = 0
    
    for dispute in disputes:
        dispute_id = dispute.get('dispute_id')
        worksheet_row = worksheet_lookup.get(dispute_id)
        
        if not worksheet_row:
            continue
        
        updates = {}
        enrichment_notes = []
        
        # Process patient count
        found_patients = worksheet_row.get('found_patient_count', '').strip()
        if found_patients:
            patient_count = parse_patient_count(found_patients)
            if patient_count:
                if not dispute.get('patients_affected') or dispute.get('patients_affected') == '':
                    updates['patients_affected'] = patient_count
                    updates['patients_affected_source'] = 'manual_research'
                    enrichment_notes.append(f"Added {patient_count:,} patients from manual research")
        
        # Process OON date
        found_oon = worksheet_row.get('found_oon_date', '').strip()
        if found_oon:
            oon_date = parse_date(found_oon)
            if oon_date:
                if not dispute.get('oon_effective_date') or dispute.get('oon_effective_date') == '':
                    updates['oon_effective_date'] = oon_date
                    enrichment_notes.append(f"Added OON date: {oon_date}")
        
        # Process resolution date
        found_resolution = worksheet_row.get('found_resolution_date', '').strip()
        if found_resolution:
            resolution_date = parse_date(found_resolution)
            if resolution_date:
                if dispute.get('outcome_status') == 'Resolved' and (not dispute.get('resolution_date') or dispute.get('resolution_date') == ''):
                    updates['resolution_date'] = resolution_date
                    enrichment_notes.append(f"Added resolution date: {resolution_date}")
        
        # Process URL
        search_url = worksheet_row.get('search_result_url', '').strip()
        if search_url:
            # Update primary_source_url if empty, otherwise add to additional_sources
            if not dispute.get('primary_source_url') or dispute.get('primary_source_url') == '':
                updates['primary_source_url'] = search_url
            else:
                # Add to additional sources
                existing = dispute.get('additional_sources', '')
                if existing:
                    # Parse JSON array if it exists
                    try:
                        sources = json.loads(existing) if existing.startswith('[') else [existing]
                    except:
                        sources = [existing] if existing else []
                    if search_url not in sources:
                        sources.append(search_url)
                        updates['additional_sources'] = json.dumps(sources)
                else:
                    updates['additional_sources'] = json.dumps([search_url])
        
        # Process article text excerpt (use improved extraction if provided)
        article_text = worksheet_row.get('article_text_excerpt', '').strip()
        if article_text:
            # Use the improved extraction function
            from agent.improved_web_search_enrichment import extract_patient_count_improved, extract_dates_improved
            
            # Extract patient count if not manually provided
            if not found_patients:
                patient_data = extract_patient_count_improved(article_text)
                if patient_data:
                    count, context = patient_data
                    if not dispute.get('patients_affected') or dispute.get('patients_affected') == '':
                        updates['patients_affected'] = count
                        updates['patients_affected_source'] = 'manual_research_extracted'
                        enrichment_notes.append(f"Extracted {count:,} patients from article text")
            
            # Extract dates if not manually provided
            dates = extract_dates_improved(article_text)
            if dates['oon_effective_date'] and not found_oon:
                if not dispute.get('oon_effective_date') or dispute.get('oon_effective_date') == '':
                    updates['oon_effective_date'] = dates['oon_effective_date']
                    enrichment_notes.append(f"Extracted OON date: {dates['oon_effective_date']}")
            if dates['resolution_date'] and not found_resolution:
                if dispute.get('outcome_status') == 'Resolved' and (not dispute.get('resolution_date') or dispute.get('resolution_date') == ''):
                    updates['resolution_date'] = dates['resolution_date']
                    enrichment_notes.append(f"Extracted resolution date: {dates['resolution_date']}")
        
        # Process notes
        worksheet_notes = worksheet_row.get('notes', '').strip()
        if worksheet_notes:
            enrichment_notes.append(f"Research notes: {worksheet_notes}")
        
        # Update enrichment notes
        if enrichment_notes:
            existing = dispute.get('enrichment_notes', '')
            timestamp = datetime.now().strftime('%Y-%m-%d')
            if existing:
                updates['enrichment_notes'] = f"{existing}; Manual research {timestamp}: {'; '.join(enrichment_notes)}"
            else:
                updates['enrichment_notes'] = f"Manual research {timestamp}: {'; '.join(enrichment_notes)}"
        
        # Apply updates
        if updates:
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
            
            updates_made += 1
    
    # Write back
    if updates_made > 0:
        fieldnames = list(disputes[0].keys())
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(disputes)
        
        print(f"Updated {updates_made} disputes from worksheet results")
        return updates_made
    else:
        print("No updates to process (no rows marked as processed)")
        return 0

if __name__ == "__main__":
    import sys
    worksheet_file = sys.argv[1] if len(sys.argv) > 1 else 'search_query_worksheet.csv'
    process_worksheet_results(worksheet_file)

