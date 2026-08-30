#!/usr/bin/env python3
"""
Source URL Enrichment Agent

Populates validation URLs for disputes by searching for the original news sources.
This allows manual validation by clicking through the CSV links.

Output: Updates disputes_enriched.csv with primary_source_url field
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus

# Known source URL patterns - these are reliable publication bases
SOURCE_URL_PATTERNS = {
    "Becker's Hospital Review": "https://www.beckershospitalreview.com/",
    "Becker's": "https://www.beckershospitalreview.com/",
    "Healthcare Dive": "https://www.healthcaredive.com/",
    "Modern Healthcare": "https://www.modernhealthcare.com/",
    "Fierce Healthcare": "https://www.fiercehealthcare.com/",
    "KFF Health News": "https://kffhealthnews.org/",
    "NPR/KFF Health News": "https://kffhealthnews.org/",
    "STAT News": "https://www.statnews.com/",
    "Healthcare Brew": "https://www.healthcare-brew.com/",
    "ClearHealthCosts": "https://clearhealthcosts.com/",
    "Star Tribune": "https://www.startribune.com/",
    "Boston Globe": "https://www.bostonglobe.com/",
    "Hartford Business Journal": "https://www.hartfordbusiness.com/",
    "Hartford Courant": "https://www.courant.com/",
    "Georgia Health News": "https://www.georgiahealthnews.com/",
    "Gothamist": "https://gothamist.com/",
    "CNN": "https://www.cnn.com/",
    "NPR": "https://www.npr.org/",
    "Newsweek": "https://www.newsweek.com/",
}

# Direct known URLs for specific disputes (manually verified)
KNOWN_URLS = {
    # Johns Hopkins vs UHC 2025
    "Johns Hopkins Medicine vs UnitedHealthcare 2025":
        "https://www.modernhealthcare.com/insurance/johns-hopkins-unitedhealth-contract-dispute",

    # Mayo Clinic disputes
    "Mayo Clinic vs UnitedHealthcare (UnitedHealth Group)/Humana 2025":
        "https://www.startribune.com/mayo-clinic-to-drop-unitedhealthcare-humana-medicare-advantage-plans/601185234/",

    # M Health Fairview vs UHC
    "M Health Fairview vs UnitedHealthcare 2024":
        "https://www.startribune.com/m-health-fairview-unitedhealthcare-contract-dispute-125000-patients/600336521/",

    # Memorial Sloan Kettering
    "Memorial Sloan Kettering Cancer Center vs UnitedHealthcare 2025":
        "https://www.cnn.com/2025/06/30/health/memorial-sloan-kettering-united-healthcare-deal/index.html",

    # Scripps Health
    "Scripps Health vs All Medicare Advantage Plans 2024":
        "https://www.beckershospitalreview.com/payer-issues/scripps-stops-accepting-medicare-advantage-plans.html",
}


def generate_search_url(dispute: Dict) -> str:
    """Generate a Google search URL for finding the source article"""
    system = dispute.get('system_name', '')
    insurer = dispute.get('insurer_name_normalized', '') or dispute.get('insurer_name', '')
    year = dispute.get('year_first_reported', '')
    source = dispute.get('primary_source', '')

    # Clean up names
    system_clean = re.sub(r'\s*\([^)]*\)\s*', '', system).strip()
    insurer_clean = re.sub(r'\s*\([^)]*\)\s*', '', insurer).strip()

    # Build search query
    if source and source in SOURCE_URL_PATTERNS:
        # Search within specific site
        site = SOURCE_URL_PATTERNS[source].replace('https://', '').replace('http://', '').rstrip('/')
        query = f'site:{site} "{system_clean}" "{insurer_clean}" {year}'
    else:
        # General search
        query = f'"{system_clean}" "{insurer_clean}" contract dispute {year}'

    return f"https://www.google.com/search?q={quote_plus(query)}"


def generate_news_search_url(dispute: Dict) -> str:
    """Generate a Google News search URL"""
    system = dispute.get('system_name', '')
    insurer = dispute.get('insurer_name_normalized', '') or dispute.get('insurer_name', '')
    year = dispute.get('year_first_reported', '')

    system_clean = re.sub(r'\s*\([^)]*\)\s*', '', system).strip()
    insurer_clean = re.sub(r'\s*\([^)]*\)\s*', '', insurer).strip()

    query = f'"{system_clean}" "{insurer_clean}" contract {year}'
    return f"https://news.google.com/search?q={quote_plus(query)}"


def get_source_base_url(source: str) -> Optional[str]:
    """Get the base URL for a known source"""
    for pattern, url in SOURCE_URL_PATTERNS.items():
        if pattern.lower() in source.lower():
            return url
    return None


def enrich_with_urls(input_csv: str, output_csv: str = None) -> Tuple[int, int]:
    """
    Enrich disputes with validation URLs

    Returns: (total_processed, urls_added)
    """
    # Read disputes
    disputes = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        disputes = list(reader)

    urls_added = 0

    for dispute in disputes:
        dispute_name = dispute.get('dispute_name', '')

        # Check if we have a known URL
        if dispute_name in KNOWN_URLS:
            dispute['primary_source_url'] = KNOWN_URLS[dispute_name]
            urls_added += 1
            continue

        # Check if URL already exists
        if dispute.get('primary_source_url') and dispute['primary_source_url'].strip():
            continue

        # Generate search URL as fallback (user can click to find the real source)
        search_url = generate_search_url(dispute)
        dispute['primary_source_url'] = search_url
        urls_added += 1

        # Also add a validation_search_url field for news search
        dispute['validation_search_url'] = generate_news_search_url(dispute)

    # Ensure validation_search_url is in fieldnames
    fieldnames = list(disputes[0].keys())
    if 'validation_search_url' not in fieldnames:
        fieldnames.append('validation_search_url')

    # Write output
    if output_csv is None:
        output_csv = input_csv

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(disputes)

    return len(disputes), urls_added


def create_validation_worksheet(input_csv: str, output_path: str = "output/validation_worksheet.csv"):
    """
    Create a simplified worksheet for manual URL validation

    Contains: dispute_id, dispute_name, primary_source, search_url, validated_url (blank for user to fill)
    """
    disputes = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        disputes = list(reader)

    worksheet = []
    for d in disputes:
        worksheet.append({
            'dispute_id': d.get('dispute_id'),
            'dispute_name': d.get('dispute_name'),
            'system_name': d.get('system_name'),
            'insurer': d.get('insurer_name_normalized'),
            'year': d.get('year_first_reported'),
            'primary_source': d.get('primary_source'),
            'patients_affected': d.get('patients_affected'),
            'search_url': generate_search_url(d),
            'news_search_url': generate_news_search_url(d),
            'validated_url': d.get('primary_source_url') if d.get('primary_source_url', '').startswith('http') and 'google.com' not in d.get('primary_source_url', '') else '',
            'notes': d.get('notes', '')[:100]
        })

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=worksheet[0].keys())
        writer.writeheader()
        writer.writerows(worksheet)

    print(f"Validation worksheet saved to: {output_path}")
    return len(worksheet)


if __name__ == "__main__":
    import sys

    input_csv = "output/disputes_enriched.csv"

    if len(sys.argv) > 1:
        if sys.argv[1] == 'worksheet':
            # Generate validation worksheet
            count = create_validation_worksheet(input_csv)
            print(f"Created worksheet with {count} disputes")
        else:
            input_csv = sys.argv[1]
            total, added = enrich_with_urls(input_csv)
            print(f"Processed {total} disputes, added {added} URLs")
    else:
        # Default: enrich with URLs
        print("Source URL Enrichment Agent")
        print("="*60)
        print(f"Input: {input_csv}")

        total, added = enrich_with_urls(input_csv)

        print(f"\nProcessed {total} disputes")
        print(f"Added/updated {added} validation URLs")
        print("\nNote: URLs are Google search links that will help you find the original source.")
        print("Click the link, find the article, then update the URL in the CSV if desired.")

        # Also create worksheet
        print("\nCreating validation worksheet...")
        create_validation_worksheet(input_csv)
