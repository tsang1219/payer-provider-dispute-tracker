#!/usr/bin/env python3
"""
Outcome Status Enrichment Agent

This agent specifically checks hospital websites for OON announcements to determine
the correct outcome_status for disputes. Hospital websites are the most authoritative
source for network status.

Search Strategy:
1. Search hospital's own website for insurer OON announcements
2. Search for resolution/agreement announcements on hospital website
3. Fall back to news sources if hospital website doesn't have info

Outcome Status Values:
- Resolved: Agreement reached, back in-network
- OON-Ongoing: Confirmed out-of-network, no resolution in sight
- OON-Temporary: Out-of-network but actively negotiating or with deadline
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from pathlib import Path


def extract_hospital_domain(system_name: str) -> Optional[str]:
    """
    Try to determine the hospital's website domain from system name.
    Returns the likely domain pattern for site-specific searches.
    """
    # Common domain patterns
    domain_mappings = {
        'WakeMed': 'wakemed.org',
        'Wellstar': 'wellstar.org',
        'Piedmont': 'piedmont.org',
        'Northside Hospital': 'northside.com',
        'Memorial Hermann': 'memorialhermann.org',
        'Providence': 'providence.org',
        'Scripps': 'scripps.org',
        'Dignity Health': 'dignityhealth.org',
        'UNC Health': 'unchealthcare.org',
        'Duke Health': 'dukehealth.org',
        'VCU Health': 'vcuhealth.org',
        'Hackensack Meridian': 'hackensackmeridianhealth.org',
        'Lifespan': 'lifespan.org',
        'Ascension': 'ascension.org',
        'Mercy Health': 'mercy.com',
        'Trinity Health': 'trinity-health.org',
        'HCA': 'hcahealthcare.com',
        'Tenet': 'tenethealth.com',
        'Community Health': 'chs.net',
        'Baptist Health': 'baptisthealth.com',
        'Bon Secours': 'bonsecours.com',
        'Allina': 'allinahealth.org',
        'Sanford': 'sanfordhealth.org',
        'Avera': 'avera.org',
        'Essentia': 'essentiahealth.org',
        'HealthPartners': 'healthpartners.com',
        'Fairview': 'fairview.org',
        'North Memorial': 'northmemorial.com',
        'Geisinger': 'geisinger.org',
        'Lehigh Valley': 'lvhn.org',
        'Jefferson Health': 'jeffersonhealth.org',
        'Main Line Health': 'mainlinehealth.org',
        'Chesapeake Regional': 'chesapeakeregional.com',
        'Hartford HealthCare': 'hartfordhealthcare.org',
        'Yale New Haven': 'ynhhs.org',
        'Vanderbilt': 'vumc.org',
        'Emory': 'emoryhealthcare.org',
        'Prisma': 'prismahealth.org',
        'Atrium': 'atriumhealth.org',
        'Novant': 'novanthealth.org',
        'CaroMont': 'caromonthealth.org',
        'Hillcrest': 'hillcrest.com',
        'Infirmary': 'infirmaryhealth.org',
        'Huntsville Hospital': 'huntsvillehospital.org',
        'Carson Tahoe': 'carsontahoe.com',
        'Broward Health': 'browardhealth.org',
        'NCH': 'nchmd.org',
        'Florida Blue': 'floridablue.com',
        'Albany Med': 'amc.edu',
        'Cape Fear Valley': 'capefearvalley.com',
        'Samaritan': 'samhealth.org',
        'St. Charles': 'stcharleshealthcare.org',
        'Comanche County': 'ccmhonline.com',
        'MU Health': 'muhealth.org',
        'ECU Health': 'ecuhealth.org',
        'WellSpan': 'wellspan.org',
        'Northern Light': 'northernlighthealth.org',
        'Aultman': 'aultman.org',
        'Prairie Lakes': 'prairielakes.com',
        'MyMichigan': 'mymichigan.org',
        'Great Plains': 'gphealth.org',
    }

    # Try exact match
    for key, domain in domain_mappings.items():
        if key.lower() in system_name.lower():
            return domain

    # Try to generate from system name
    # Remove common suffixes and create domain guess
    clean_name = system_name.lower()
    for suffix in [' health system', ' health', ' healthcare', ' medical center',
                   ' hospital', ' hospitals', ' regional', ' medical']:
        clean_name = clean_name.replace(suffix, '')

    clean_name = re.sub(r'[^a-z0-9]', '', clean_name)
    if clean_name:
        return f"{clean_name}.org"

    return None


def generate_hospital_website_queries(dispute: Dict) -> List[Dict]:
    """
    Generate search queries specifically targeting hospital websites
    for OON status announcements.

    Returns list of query dicts with query string and purpose.
    """
    system = dispute.get('system_name', '')
    insurer = dispute.get('insurer_name_normalized', '')
    year = dispute.get('year_first_reported', '')

    # Get hospital domain
    domain = extract_hospital_domain(system)

    # Clean names for search
    system_clean = re.sub(r'\s*\([^)]*\)\s*', '', system).strip()
    insurer_clean = insurer.strip()

    # Also get just the insurer brand name (e.g., "United" from "UnitedHealthcare")
    insurer_short = re.sub(r'Healthcare|Health|Insurance|Blue Cross Blue Shield', '', insurer_clean).strip()

    queries = []

    # Priority 1: Hospital website search for OON announcement
    if domain:
        queries.append({
            'query': f'site:{domain} "{insurer_clean}" out of network',
            'purpose': 'hospital_oon_announcement',
            'priority': 1
        })
        queries.append({
            'query': f'site:{domain} "{insurer_short}" insurance network',
            'purpose': 'hospital_network_status',
            'priority': 2
        })
        queries.append({
            'query': f'site:{domain} "{insurer_clean}" agreement',
            'purpose': 'hospital_resolution_announcement',
            'priority': 3
        })
        queries.append({
            'query': f'site:{domain} "{insurer_short}" contract',
            'purpose': 'hospital_contract_news',
            'priority': 4
        })

    # Priority 2: General search with hospital name + insurer + OON terms
    queries.append({
        'query': f'"{system_clean}" "{insurer_clean}" "out of network" {year}',
        'purpose': 'general_oon_search',
        'priority': 5
    })

    queries.append({
        'query': f'"{system_clean}" "{insurer_clean}" "reached agreement" OR "new contract"',
        'purpose': 'resolution_search',
        'priority': 6
    })

    # Priority 3: News sources as fallback
    queries.append({
        'query': f'site:beckershospitalreview.com OR site:modernhealthcare.com "{system_clean}" "{insurer_clean}" {year}',
        'purpose': 'news_fallback',
        'priority': 7
    })

    return queries


def extract_outcome_status_from_text(text: str, dispute: Dict) -> Dict:
    """
    Extract outcome status from hospital website or news text.

    Returns dict with:
    - outcome_status: Resolved, OON-Ongoing, OON-Temporary, or None if unclear
    - confidence: high, medium, low
    - evidence: text snippet supporting the determination
    - resolution_date: if resolved, when
    - source_type: hospital_website, news, etc.
    """
    result = {
        'outcome_status': None,
        'confidence': 'low',
        'evidence': '',
        'resolution_date': None,
        'source_type': None
    }

    if not text:
        return result

    text_lower = text.lower()

    # === RESOLVED indicators ===
    resolved_patterns = [
        (r'reached\s+(?:a\s+)?(?:new\s+)?(?:multi-?year\s+)?agreement', 'high'),
        (r'new\s+(?:multi-?year\s+)?contract\s+(?:agreement|reached|signed)', 'high'),
        (r'back\s+in[- ]network', 'high'),
        (r'remain(?:s|ing)?\s+in[- ]network', 'high'),
        (r'continued?\s+in[- ]network', 'high'),
        (r'(?:have|has)\s+agreed\s+to\s+(?:a\s+)?(?:new\s+)?(?:contract|terms)', 'high'),
        (r'contract\s+(?:has\s+been\s+)?extended', 'medium'),
        (r'resolved\s+(?:the\s+)?(?:contract\s+)?dispute', 'high'),
        (r'settled\s+(?:the\s+)?(?:contract\s+)?dispute', 'high'),
        (r'patients?\s+(?:can|will)\s+continue\s+(?:to\s+)?(?:receive|access)', 'medium'),
    ]

    for pattern, confidence in resolved_patterns:
        match = re.search(pattern, text_lower)
        if match:
            # Get context around the match
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            evidence = text[start:end].strip()

            result['outcome_status'] = 'Resolved'
            result['confidence'] = confidence
            result['evidence'] = evidence

            # Try to extract resolution date
            date_match = re.search(
                r'(?:on|effective|as of|starting)\s+(\w+\s+\d{1,2},?\s+\d{4})',
                text[max(0, match.start()-50):min(len(text), match.end()+100)],
                re.IGNORECASE
            )
            if date_match:
                result['resolution_date'] = date_match.group(1)

            return result

    # === OON-ONGOING indicators ===
    oon_ongoing_patterns = [
        (r'no\s+longer\s+(?:accept(?:s|ing)?|in[- ]network|participat)', 'high'),
        (r'(?:is|are|has|have)\s+(?:gone\s+)?out[- ]of[- ]network', 'high'),
        (r'terminated\s+(?:the\s+)?(?:contract|agreement|relationship)', 'high'),
        (r'contract\s+(?:has\s+)?(?:ended|expired|terminated)', 'medium'),
        (r'(?:will|may)\s+(?:be\s+)?out[- ]of[- ]network', 'medium'),
        (r'patients?\s+(?:will|may)\s+(?:need\s+to\s+)?(?:pay|face)\s+(?:higher|more|additional)', 'medium'),
        (r'dropped\s+(?:from\s+)?(?:the\s+)?network', 'high'),
        (r'leaving\s+(?:the\s+)?network', 'high'),
    ]

    for pattern, confidence in oon_ongoing_patterns:
        match = re.search(pattern, text_lower)
        if match:
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            evidence = text[start:end].strip()

            # Check if there's also resolution language (dispute may be old)
            # If text mentions both OON and resolution, need more context

            result['outcome_status'] = 'OON-Ongoing'
            result['confidence'] = confidence
            result['evidence'] = evidence
            return result

    # === OON-TEMPORARY indicators (negotiating, deadline mentioned) ===
    oon_temp_patterns = [
        (r'(?:continue|continuing)\s+(?:to\s+)?negotiat', 'medium'),
        (r'negotiations?\s+(?:are\s+)?(?:ongoing|continuing|underway)', 'medium'),
        (r'temporary\s+(?:extension|agreement)', 'medium'),
        (r'cooling[- ]off\s+period', 'medium'),
        (r'deadline\s+(?:of|is|was)\s+\w+\s+\d{1,2}', 'medium'),
        (r'patients?\s+should\s+(?:not\s+)?(?:be\s+)?affected\s+(?:until|through)', 'low'),
    ]

    for pattern, confidence in oon_temp_patterns:
        match = re.search(pattern, text_lower)
        if match:
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            evidence = text[start:end].strip()

            result['outcome_status'] = 'OON-Temporary'
            result['confidence'] = confidence
            result['evidence'] = evidence
            return result

    return result


def get_disputes_needing_status_check(csv_path: str = 'output/disputes_enriched.csv') -> List[Dict]:
    """
    Get all disputes that need outcome status verification.
    These are disputes with OON-Ongoing, OON-Temporary, or Unknown status.
    """
    disputes = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get('outcome_status', '')
            if status in ['OON-Ongoing', 'OON-Temporary', 'Unknown', '']:
                disputes.append(row)

    return disputes


def generate_batch_queries(limit: int = None,
                          csv_path: str = 'output/disputes_enriched.csv') -> List[Dict]:
    """
    Generate search queries for all disputes needing status checks.

    Returns list of dicts with dispute info and prioritized queries.
    """
    disputes = get_disputes_needing_status_check(csv_path)

    if limit:
        disputes = disputes[:limit]

    batch = []
    for dispute in disputes:
        queries = generate_hospital_website_queries(dispute)

        batch.append({
            'dispute_id': dispute.get('dispute_id'),
            'dispute_name': dispute.get('dispute_name'),
            'system_name': dispute.get('system_name'),
            'insurer_name': dispute.get('insurer_name_normalized'),
            'current_status': dispute.get('outcome_status'),
            'year': dispute.get('year_first_reported'),
            'hospital_domain': extract_hospital_domain(dispute.get('system_name', '')),
            'queries': queries,
            'primary_query': queries[0]['query'] if queries else None
        })

    return batch


def update_dispute_status(dispute_id: int,
                         new_status: str,
                         resolution_date: str = None,
                         notes: str = None,
                         source_url: str = None,
                         csv_path: str = 'output/disputes_enriched.csv') -> bool:
    """
    Update a dispute's outcome status in the CSV.
    """
    disputes = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        disputes = list(reader)

    updated = False
    for dispute in disputes:
        if int(dispute.get('dispute_id', 0)) == dispute_id:
            dispute['outcome_status'] = new_status

            if resolution_date:
                dispute['resolution_date'] = resolution_date

            if source_url:
                dispute['primary_source_url'] = source_url

            if notes:
                existing_notes = dispute.get('notes', '')
                if existing_notes:
                    dispute['notes'] = f"{existing_notes}; {notes}"
                else:
                    dispute['notes'] = notes

            # Update enrichment notes
            timestamp = datetime.now().strftime('%Y-%m-%d')
            enrich_note = f"Status updated to {new_status} via hospital website check ({timestamp})"
            existing_enrich = dispute.get('enrichment_notes', '')
            if existing_enrich:
                dispute['enrichment_notes'] = f"{existing_enrich}; {enrich_note}"
            else:
                dispute['enrichment_notes'] = enrich_note

            dispute['last_updated'] = datetime.now().isoformat()
            updated = True
            break

    if updated:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(disputes)

    return updated


def process_search_result(dispute_id: int,
                         search_text: str,
                         source_url: str = None,
                         csv_path: str = 'output/disputes_enriched.csv') -> Dict:
    """
    Process search result text for a dispute and update status if determined.

    Returns result dict with:
    - success: bool
    - dispute_id: int
    - determined_status: str or None
    - confidence: str
    - evidence: str
    - updated: bool (whether CSV was updated)
    """
    # Get current dispute info
    disputes = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        disputes = list(reader)

    dispute = None
    for d in disputes:
        if int(d.get('dispute_id', 0)) == dispute_id:
            dispute = d
            break

    if not dispute:
        return {
            'success': False,
            'error': f'Dispute ID {dispute_id} not found'
        }

    # Extract status from text
    extraction = extract_outcome_status_from_text(search_text, dispute)

    result = {
        'success': True,
        'dispute_id': dispute_id,
        'dispute_name': dispute.get('dispute_name'),
        'current_status': dispute.get('outcome_status'),
        'determined_status': extraction['outcome_status'],
        'confidence': extraction['confidence'],
        'evidence': extraction['evidence'],
        'resolution_date': extraction['resolution_date'],
        'updated': False
    }

    # Update if we have high confidence determination
    if extraction['outcome_status'] and extraction['confidence'] in ['high', 'medium']:
        success = update_dispute_status(
            dispute_id=dispute_id,
            new_status=extraction['outcome_status'],
            resolution_date=extraction['resolution_date'],
            notes=f"Status confirmed: {extraction['evidence'][:100]}...",
            source_url=source_url,
            csv_path=csv_path
        )
        result['updated'] = success

    return result


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Outcome Status Enrichment Agent")
        print("=" * 60)
        print("\nThis agent checks hospital websites for OON announcements")
        print("to determine the correct outcome_status for disputes.")
        print("\nUsage:")
        print("  python agent/outcome_status_enrichment_agent.py list [limit]")
        print("    - List disputes needing status verification")
        print("\n  python agent/outcome_status_enrichment_agent.py queries [limit]")
        print("    - Generate search queries for disputes")
        print("\n  python agent/outcome_status_enrichment_agent.py domains")
        print("    - Show hospital domains for searches")
        print("=" * 60)
        sys.exit(0)

    command = sys.argv[1]

    if command == 'list':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
        disputes = get_disputes_needing_status_check()
        if limit:
            disputes = disputes[:limit]

        print(f"\nDisputes needing status verification: {len(disputes)}")
        print("-" * 80)

        for d in disputes:
            print(f"ID {d['dispute_id']:3}: {d['dispute_name'][:50]}...")
            print(f"         Status: {d['outcome_status'] or 'EMPTY'}")
            domain = extract_hospital_domain(d['system_name'])
            print(f"         Domain: {domain or 'Unknown'}")
            print()

    elif command == 'queries':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        batch = generate_batch_queries(limit=limit)

        print(f"\nGenerated queries for {len(batch)} disputes")
        print("-" * 80)

        for item in batch:
            print(f"\nID {item['dispute_id']}: {item['dispute_name'][:50]}...")
            print(f"  Current status: {item['current_status'] or 'EMPTY'}")
            print(f"  Hospital domain: {item['hospital_domain'] or 'Unknown'}")
            print(f"  Primary query: {item['primary_query']}")
            print(f"  Alternative queries: {len(item['queries']) - 1}")

        # Save to file
        output_file = 'output/status_check_queries.json'
        with open(output_file, 'w') as f:
            json.dump(batch, f, indent=2)
        print(f"\nSaved to {output_file}")

    elif command == 'domains':
        disputes = get_disputes_needing_status_check()

        print("\nHospital domains for status checks:")
        print("-" * 60)

        domains_found = 0
        for d in disputes:
            domain = extract_hospital_domain(d['system_name'])
            if domain:
                domains_found += 1
                print(f"  {d['system_name'][:40]:40} -> {domain}")

        print(f"\nDomains found: {domains_found}/{len(disputes)}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
