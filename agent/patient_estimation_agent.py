#!/usr/bin/env python3
"""
Patient Estimation Agent

Uses the payer_market_reference.json and patient_estimation_framework.md
to estimate patient counts for disputes that are missing this data.

Estimation Methods:
1. MA Enrollment Estimation - for Medicare Advantage disputes
2. Commercial Insurance Estimation - for commercial disputes
3. Known Calibration - uses known patient counts from similar disputes
4. Revenue-Based Estimation - when hospital revenue data is available
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class PatientEstimate:
    """Structured patient count estimate"""
    count: int
    confidence: str  # high, medium, low
    method: str
    range_low: Optional[int] = None
    range_high: Optional[int] = None
    notes: str = ""


# Load reference data
def load_market_reference() -> Dict:
    """Load the payer market reference data"""
    ref_path = Path(__file__).parent.parent / "payer_market_reference.json"
    with open(ref_path, 'r') as f:
        return json.load(f)


# Health system data (estimated annual patients and market share)
# This supplements the data in the enrichment agent
HEALTH_SYSTEM_DATA = {
    # Major academic systems
    "Johns Hopkins Medicine": {"annual_patients": 400000, "market_share": 0.30, "type": "major_academic"},
    "Mass General Brigham": {"annual_patients": 600000, "market_share": 0.35, "type": "major_academic"},
    "NewYork-Presbyterian": {"annual_patients": 500000, "market_share": 0.25, "type": "major_academic"},
    "Mayo Clinic": {"annual_patients": 300000, "market_share": 0.25, "type": "major_academic"},
    "Duke Health": {"annual_patients": 250000, "market_share": 0.20, "type": "major_academic"},
    "UNC Health": {"annual_patients": 350000, "market_share": 0.22, "type": "large_community"},
    "VCU Health": {"annual_patients": 200000, "market_share": 0.18, "type": "major_academic"},
    "Memorial Sloan Kettering Cancer Center": {"annual_patients": 150000, "market_share": 0.15, "type": "specialty"},

    # Large regional systems
    "Wellstar Health System": {"annual_patients": 300000, "market_share": 0.25, "type": "large_community"},
    "Northside Hospital": {"annual_patients": 280000, "market_share": 0.28, "type": "large_community"},
    "Piedmont Healthcare": {"annual_patients": 250000, "market_share": 0.22, "type": "large_community"},
    "Memorial Hermann Health System": {"annual_patients": 400000, "market_share": 0.18, "type": "large_community"},
    "WakeMed": {"annual_patients": 180000, "market_share": 0.20, "type": "large_community"},
    "Prisma Health": {"annual_patients": 220000, "market_share": 0.30, "type": "large_community"},
    "Jefferson Health": {"annual_patients": 350000, "market_share": 0.15, "type": "large_community"},
    "Hartford HealthCare": {"annual_patients": 200000, "market_share": 0.25, "type": "large_community"},
    "Hackensack Meridian Health": {"annual_patients": 280000, "market_share": 0.22, "type": "large_community"},
    "Lehigh Valley Health Network": {"annual_patients": 180000, "market_share": 0.28, "type": "large_community"},
    "Providence": {"annual_patients": 400000, "market_share": 0.20, "type": "large_community"},
    "Allina Health": {"annual_patients": 200000, "market_share": 0.18, "type": "large_community"},
    "M Health Fairview": {"annual_patients": 220000, "market_share": 0.20, "type": "large_community"},
    "HealthPartners": {"annual_patients": 180000, "market_share": 0.15, "type": "large_community"},
    "Bon Secours Mercy Health": {"annual_patients": 300000, "market_share": 0.15, "type": "large_community"},
    "Ascension Texas": {"annual_patients": 250000, "market_share": 0.12, "type": "large_community"},
    "Baylor Scott & White": {"annual_patients": 500000, "market_share": 0.25, "type": "large_community"},
    "HCA Healthcare (38 hospitals)": {"annual_patients": 800000, "market_share": 0.20, "type": "large_community"},
    "Trinity Health": {"annual_patients": 350000, "market_share": 0.15, "type": "large_community"},

    # Mid-size systems
    "Corewell Health": {"annual_patients": 150000, "market_share": 0.22, "type": "mid_size"},
    "Bronson Healthcare": {"annual_patients": 80000, "market_share": 0.25, "type": "mid_size"},
    "Salem Health": {"annual_patients": 70000, "market_share": 0.30, "type": "mid_size"},
    "Kootenai Health": {"annual_patients": 50000, "market_share": 0.35, "type": "mid_size"},
    "South Shore Health": {"annual_patients": 40000, "market_share": 0.15, "type": "mid_size"},
    "UConn Health": {"annual_patients": 60000, "market_share": 0.12, "type": "mid_size"},
    "Scripps Health": {"annual_patients": 150000, "market_share": 0.12, "type": "mid_size"},
    "MultiCare": {"annual_patients": 120000, "market_share": 0.18, "type": "mid_size"},
    "Baptist Health": {"annual_patients": 150000, "market_share": 0.20, "type": "mid_size"},
    "Kettering Health": {"annual_patients": 100000, "market_share": 0.18, "type": "mid_size"},
    "Centra Health": {"annual_patients": 80000, "market_share": 0.40, "type": "mid_size"},
    "Ballad Health": {"annual_patients": 120000, "market_share": 0.65, "type": "dominant_regional"},
    "Sanford Health": {"annual_patients": 200000, "market_share": 0.45, "type": "dominant_regional"},
    "Avera": {"annual_patients": 150000, "market_share": 0.35, "type": "mid_size"},
    "Essentia Health": {"annual_patients": 100000, "market_share": 0.25, "type": "mid_size"},

    # Smaller/rural systems
    "Infirmary Health": {"annual_patients": 50000, "market_share": 0.30, "type": "mid_size"},
    "Cape Fear Valley Health": {"annual_patients": 60000, "market_share": 0.35, "type": "mid_size"},
    "Samaritan Health Services": {"annual_patients": 40000, "market_share": 0.30, "type": "mid_size"},
    "Stillwater Medical Center": {"annual_patients": 25000, "market_share": 0.45, "type": "single_hospital"},
    "Conway Regional Health System": {"annual_patients": 30000, "market_share": 0.40, "type": "single_hospital"},
    "Brookings Health System": {"annual_patients": 15000, "market_share": 0.50, "type": "single_hospital"},
    "Great Plains Health": {"annual_patients": 20000, "market_share": 0.45, "type": "single_hospital"},
    "Prairie Lakes Healthcare System": {"annual_patients": 15000, "market_share": 0.40, "type": "single_hospital"},
    "Cameron Regional Medical Center": {"annual_patients": 12000, "market_share": 0.45, "type": "single_hospital"},

    # Children's hospitals (specialty)
    "Phoenix Children's Hospital": {"annual_patients": 80000, "market_share": 0.40, "type": "specialty"},
    "Johns Hopkins All Children's Hospital": {"annual_patients": 60000, "market_share": 0.30, "type": "specialty"},

    # === ADDITIONAL SYSTEMS (added to fill gaps) ===

    # Large academic/teaching systems
    "Montefiore Health System": {"annual_patients": 350000, "market_share": 0.18, "type": "major_academic"},
    "Vanderbilt Health": {"annual_patients": 300000, "market_share": 0.25, "type": "major_academic"},
    "MUSC Health": {"annual_patients": 180000, "market_share": 0.28, "type": "major_academic"},
    "University of Florida Health": {"annual_patients": 250000, "market_share": 0.20, "type": "major_academic"},
    "MU Health Care": {"annual_patients": 120000, "market_share": 0.22, "type": "major_academic"},
    "SUNY Upstate University Hospital": {"annual_patients": 80000, "market_share": 0.15, "type": "major_academic"},
    "Brown University Health": {"annual_patients": 150000, "market_share": 0.30, "type": "major_academic"},

    # Large regional/multi-hospital systems
    "Dignity Health": {"annual_patients": 400000, "market_share": 0.15, "type": "large_community"},
    "Baylor Scott & White Health": {"annual_patients": 500000, "market_share": 0.25, "type": "large_community"},
    "Southwestern Health Resources": {"annual_patients": 350000, "market_share": 0.18, "type": "large_community"},
    "CommonSpirit Health": {"annual_patients": 400000, "market_share": 0.15, "type": "large_community"},
    "Lifespan": {"annual_patients": 180000, "market_share": 0.35, "type": "large_community"},
    "Northern Light Health": {"annual_patients": 120000, "market_share": 0.30, "type": "large_community"},
    "MercyOne": {"annual_patients": 150000, "market_share": 0.25, "type": "large_community"},
    "Broward Health": {"annual_patients": 200000, "market_share": 0.15, "type": "large_community"},
    "Main Line Health": {"annual_patients": 150000, "market_share": 0.12, "type": "large_community"},
    "St. Peter's Health Partners": {"annual_patients": 100000, "market_share": 0.18, "type": "large_community"},
    "Albany Med Health System": {"annual_patients": 120000, "market_share": 0.22, "type": "large_community"},

    # Mid-size regional systems
    "Northeast Georgia Health System": {"annual_patients": 150000, "market_share": 0.30, "type": "mid_size"},
    "Southeast Georgia Health System": {"annual_patients": 60000, "market_share": 0.35, "type": "mid_size"},
    "Huntsville Hospital Health System": {"annual_patients": 100000, "market_share": 0.35, "type": "mid_size"},
    "NCH Healthcare System": {"annual_patients": 80000, "market_share": 0.20, "type": "mid_size"},
    "EvergreenHealth": {"annual_patients": 60000, "market_share": 0.15, "type": "mid_size"},
    "Hillcrest HealthCare System": {"annual_patients": 80000, "market_share": 0.25, "type": "mid_size"},
    "CaroMont": {"annual_patients": 70000, "market_share": 0.25, "type": "mid_size"},
    "Community Healthcare System": {"annual_patients": 80000, "market_share": 0.20, "type": "mid_size"},
    "Powers Health": {"annual_patients": 50000, "market_share": 0.18, "type": "mid_size"},
    "Methodist Health Care": {"annual_patients": 100000, "market_share": 0.20, "type": "mid_size"},
    "Aspirus Health": {"annual_patients": 80000, "market_share": 0.22, "type": "mid_size"},
    "MyMichigan Health": {"annual_patients": 70000, "market_share": 0.20, "type": "mid_size"},
    "CHI Memorial": {"annual_patients": 60000, "market_share": 0.18, "type": "mid_size"},
    "North Memorial Health": {"annual_patients": 100000, "market_share": 0.12, "type": "mid_size"},
    "Adena Health System": {"annual_patients": 50000, "market_share": 0.30, "type": "mid_size"},
    "Spartanburg Regional Healthcare": {"annual_patients": 80000, "market_share": 0.30, "type": "mid_size"},
    "Lexington Medical Center": {"annual_patients": 90000, "market_share": 0.28, "type": "mid_size"},
    "North Mississippi Health Services": {"annual_patients": 70000, "market_share": 0.35, "type": "mid_size"},
    "Bayhealth": {"annual_patients": 60000, "market_share": 0.25, "type": "mid_size"},
    "WVU Medicine Uniontown Hospital": {"annual_patients": 25000, "market_share": 0.30, "type": "single_hospital"},

    # Smaller/community hospitals
    "Catawba Valley Medical Center": {"annual_patients": 40000, "market_share": 0.35, "type": "single_hospital"},
    "Chesapeake Regional Medical Center": {"annual_patients": 45000, "market_share": 0.25, "type": "single_hospital"},
    "Baton Rouge General": {"annual_patients": 60000, "market_share": 0.20, "type": "mid_size"},
    "Arkansas Methodist Medical Center": {"annual_patients": 20000, "market_share": 0.40, "type": "single_hospital"},
    "North Kansas City Hospital": {"annual_patients": 50000, "market_share": 0.18, "type": "mid_size"},
    "Carson Tahoe Health": {"annual_patients": 35000, "market_share": 0.30, "type": "mid_size"},
    "Montrose Regional Health": {"annual_patients": 25000, "market_share": 0.45, "type": "single_hospital"},
    "Iowa Specialty Hospitals": {"annual_patients": 15000, "market_share": 0.30, "type": "single_hospital"},
    "Blessing Health": {"annual_patients": 40000, "market_share": 0.35, "type": "mid_size"},
    "LMH Health": {"annual_patients": 35000, "market_share": 0.40, "type": "single_hospital"},
    "Kimball Health Services": {"annual_patients": 8000, "market_share": 0.50, "type": "single_hospital"},

    # Physician staffing companies (special case - use national estimates)
    "TeamHealth": {"annual_patients": 500000, "market_share": 0.05, "type": "physician_staffing"},
    "Envision Healthcare": {"annual_patients": 600000, "market_share": 0.05, "type": "physician_staffing"},

    # Specialty/OB-GYN practices
    "Capital Women's Care": {"annual_patients": 30000, "market_share": 0.10, "type": "specialty"},

    # Additional systems with variant names
    "Baylor Scott and White": {"annual_patients": 500000, "market_share": 0.25, "type": "large_community"},
    "Baylor Scott White": {"annual_patients": 500000, "market_share": 0.25, "type": "large_community"},
}

# Payer market share by state (commercial)
PAYER_COMMERCIAL_SHARE = {
    "UnitedHealthcare": {
        "default": 0.15,
        "MN": 0.25, "TX": 0.18, "GA": 0.15, "NC": 0.12, "NY": 0.12,
        "FL": 0.14, "PA": 0.10, "OH": 0.15, "MI": 0.18, "CA": 0.08
    },
    "Anthem": {
        "default": 0.12,
        "GA": 0.20, "VA": 0.22, "OH": 0.18, "CA": 0.15, "IN": 0.25,
        "MO": 0.18, "NY": 0.08
    },
    "Aetna": {
        "default": 0.08,
        "CT": 0.20, "PA": 0.12, "TX": 0.10, "NJ": 0.12
    },
    "Cigna": {
        "default": 0.10,
        "CT": 0.18, "PA": 0.12, "TN": 0.15, "SC": 0.12, "RI": 0.15
    },
    "Humana": {
        "default": 0.05,
        "KY": 0.15, "FL": 0.10, "TX": 0.08
    },
    "BCBS": {
        "default": 0.25,
        "TX": 0.35, "NC": 0.30, "TN": 0.30, "SC": 0.28, "MO": 0.32,
        "NJ": 0.28, "MN": 0.22
    },
    "Florida Blue": {
        "default": 0.30,
        "FL": 0.35
    },
    "Horizon": {
        "default": 0.25,
        "NJ": 0.35
    }
}


def normalize_payer_name(payer_name: str) -> str:
    """Normalize payer name for lookups"""
    name = payer_name.lower()

    if 'united' in name or 'uhc' in name:
        return 'UnitedHealthcare'
    if 'anthem' in name or 'elevance' in name:
        return 'Anthem'
    if 'aetna' in name:
        return 'Aetna'
    if 'cigna' in name:
        return 'Cigna'
    if 'humana' in name:
        return 'Humana'
    if 'florida blue' in name:
        return 'Florida Blue'
    if 'horizon' in name:
        return 'Horizon'
    if 'bcbs' in name or 'blue cross' in name or 'blue shield' in name:
        return 'BCBS'

    return payer_name


def normalize_system_name(system_name: str) -> str:
    """Normalize health system name for lookups"""
    # Handle HTML entities and special characters
    name = system_name
    name = name.replace('\\u0026', '&')
    name = name.replace('&amp;', '&')
    name = name.replace('&', ' and ')  # Standardize to 'and'

    # Remove parentheticals
    name = re.sub(r'\s*\([^)]*\)\s*', '', name).strip()

    # Remove common suffixes
    name = re.sub(r'\s+Health System$|\s+Health$|\s+Healthcare$', '', name).strip()

    # Normalize whitespace and lowercase for matching
    name = ' '.join(name.split())
    return name.lower()


def get_payer_commercial_share(payer: str, state: str) -> float:
    """Get payer's commercial market share in a state"""
    payer_norm = normalize_payer_name(payer)

    if payer_norm in PAYER_COMMERCIAL_SHARE:
        shares = PAYER_COMMERCIAL_SHARE[payer_norm]
        return shares.get(state, shares.get('default', 0.10))

    return 0.10  # Default assumption


def get_payer_ma_share(payer: str, state: str, market_ref: Dict) -> float:
    """Get payer's MA market share in a state using reference data"""
    payer_norm = normalize_payer_name(payer)
    state_data = market_ref.get('state_ma_enrollment_estimates', {}).get(state, {})

    # If this payer is the top payer in the state
    if state_data.get('top_payer', '').lower() in payer_norm.lower():
        return state_data.get('top_share', 15) / 100.0

    # Use national data to estimate
    national = market_ref.get('national_ma_enrollment_2024', {})
    payer_data = None

    for key, data in national.items():
        if payer_norm.lower() in key.lower():
            payer_data = data
            break

    if payer_data:
        return payer_data.get('market_share_pct', 10) / 100.0

    return 0.10  # Default 10%


def estimate_ma_patients(dispute: Dict, market_ref: Dict) -> Optional[PatientEstimate]:
    """
    Estimate patients for Medicare Advantage disputes

    Formula: state_ma_enrollment × payer_state_share × hospital_market_share
    """
    state = dispute.get('system_hq_state', '')
    if not state:
        return None

    payer = dispute.get('insurer_name_normalized', '') or dispute.get('insurer_name', '')
    system_name = dispute.get('system_name', '')

    # Get state MA enrollment
    state_data = market_ref.get('state_ma_enrollment_estimates', {}).get(state, {})
    state_ma_enrollment = state_data.get('total_ma', 0)

    if not state_ma_enrollment:
        return None

    # Get payer's MA share in state
    payer_share = get_payer_ma_share(payer, state, market_ref)

    # Get hospital market share
    system_data = None
    for name, data in HEALTH_SYSTEM_DATA.items():
        if normalize_system_name(name) in normalize_system_name(system_name) or \
           normalize_system_name(system_name) in normalize_system_name(name):
            system_data = data
            break

    if system_data:
        hospital_share = system_data.get('market_share', 0.15)
    else:
        # Use benchmark based on system type heuristics
        if 'children' in system_name.lower() or 'pediatric' in system_name.lower():
            hospital_share = 0.30  # Specialty
        elif any(x in system_name.lower() for x in ['university', 'academic', 'medical center']):
            hospital_share = 0.20  # Academic
        else:
            hospital_share = 0.15  # Default community

    # Calculate estimate
    estimated = int(state_ma_enrollment * payer_share * hospital_share)

    # Calculate range (±30%)
    range_low = int(estimated * 0.7)
    range_high = int(estimated * 1.3)

    return PatientEstimate(
        count=estimated,
        confidence="medium",
        method="ma_enrollment_estimation",
        range_low=range_low,
        range_high=range_high,
        notes=f"Calculated: {state_ma_enrollment:,} state MA × {payer_share:.0%} payer share × {hospital_share:.0%} hospital share"
    )


def estimate_commercial_patients(dispute: Dict, market_ref: Dict) -> Optional[PatientEstimate]:
    """
    Estimate patients for commercial disputes

    Formula: hospital_annual_patients × payer_commercial_share × 0.8
    """
    state = dispute.get('system_hq_state', '')
    payer = dispute.get('insurer_name_normalized', '') or dispute.get('insurer_name', '')
    system_name = dispute.get('system_name', '')

    # Get hospital data
    system_data = None
    for name, data in HEALTH_SYSTEM_DATA.items():
        if normalize_system_name(name) in normalize_system_name(system_name) or \
           normalize_system_name(system_name) in normalize_system_name(name):
            system_data = data
            break

    if not system_data:
        return None

    annual_patients = system_data.get('annual_patients', 0)
    if not annual_patients:
        return None

    # Get payer's commercial share
    payer_share = get_payer_commercial_share(payer, state)

    # Apply adjustment factor (0.8 for payer mix variation)
    estimated = int(annual_patients * payer_share * 0.8)

    # Calculate range (±25%)
    range_low = int(estimated * 0.75)
    range_high = int(estimated * 1.25)

    return PatientEstimate(
        count=estimated,
        confidence="medium",
        method="commercial_estimation",
        range_low=range_low,
        range_high=range_high,
        notes=f"Calculated: {annual_patients:,} annual patients × {payer_share:.0%} payer share × 0.8 adjustment"
    )


def calibrate_estimate(dispute: Dict, market_ref: Dict) -> Optional[PatientEstimate]:
    """
    Use known patient counts from similar disputes to calibrate estimates
    """
    system_name = dispute.get('system_name', '')
    payer = dispute.get('insurer_name_normalized', '') or dispute.get('insurer_name', '')
    state = dispute.get('system_hq_state', '')

    known_counts = market_ref.get('known_patient_counts_for_calibration', {})

    # Check for exact matches
    for key, data in known_counts.items():
        if data.get('state') == state:
            # Same state - use as reference
            reported = data.get('reported', 0)
            if reported > 0:
                # Scale based on relative system size
                system_data = None
                for name, sdata in HEALTH_SYSTEM_DATA.items():
                    if normalize_system_name(name) in normalize_system_name(system_name):
                        system_data = sdata
                        break

                if system_data:
                    # Use market share as scaling factor
                    estimated = int(reported * system_data.get('market_share', 0.15) / 0.20)

                    return PatientEstimate(
                        count=estimated,
                        confidence="low",
                        method="calibration_estimate",
                        range_low=int(estimated * 0.5),
                        range_high=int(estimated * 1.5),
                        notes=f"Calibrated from {key} ({reported:,} patients)"
                    )

    return None


def estimate_patients(dispute: Dict, market_ref: Dict) -> Optional[PatientEstimate]:
    """
    Main estimation function - tries multiple methods in order of reliability
    """
    dispute_type = dispute.get('dispute_type', 'Unknown')

    # Determine if MA or commercial
    is_ma = dispute_type in ['Medicare Advantage', 'All MA'] or \
            'ma' in dispute.get('notes', '').lower() or \
            'medicare advantage' in dispute.get('notes', '').lower()

    is_commercial = dispute_type == 'Commercial' or \
                   'commercial' in dispute.get('notes', '').lower()

    # Try appropriate estimation method
    if is_ma:
        estimate = estimate_ma_patients(dispute, market_ref)
        if estimate:
            return estimate

    if is_commercial or not is_ma:
        estimate = estimate_commercial_patients(dispute, market_ref)
        if estimate:
            return estimate

    # Fall back to calibration
    estimate = calibrate_estimate(dispute, market_ref)
    if estimate:
        return estimate

    return None


def process_disputes(input_csv: str, output_csv: str = None) -> Tuple[int, int, List[Dict]]:
    """
    Process all disputes and estimate missing patient counts

    Returns: (total_processed, estimates_added, list of updates)
    """
    market_ref = load_market_reference()

    # Read disputes
    disputes = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        disputes = list(reader)

    total_processed = 0
    estimates_added = 0
    updates = []

    for dispute in disputes:
        # Skip if already has patient count
        if dispute.get('patients_affected') and dispute.get('patients_affected') != '':
            continue

        total_processed += 1
        estimate = estimate_patients(dispute, market_ref)

        if estimate:
            estimates_added += 1

            # Update dispute record
            dispute['patients_affected'] = estimate.count
            dispute['patients_affected_source'] = f"estimated_{estimate.method}"

            # Add to enrichment notes
            existing_notes = dispute.get('enrichment_notes', '')
            timestamp = datetime.now().strftime('%Y-%m-%d')
            new_note = f"Patient estimation {timestamp}: {estimate.count:,} ({estimate.confidence} confidence, {estimate.method}). {estimate.notes}"

            if existing_notes:
                dispute['enrichment_notes'] = f"{existing_notes}; {new_note}"
            else:
                dispute['enrichment_notes'] = new_note

            # Update completeness score
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

            updates.append({
                'dispute_id': dispute.get('dispute_id'),
                'dispute_name': dispute.get('dispute_name'),
                'estimated_patients': estimate.count,
                'range': f"{estimate.range_low:,} - {estimate.range_high:,}",
                'confidence': estimate.confidence,
                'method': estimate.method,
                'notes': estimate.notes
            })

    # Write updated CSV
    if output_csv is None:
        output_csv = input_csv

    fieldnames = list(disputes[0].keys())
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(disputes)

    return total_processed, estimates_added, updates


def print_estimation_report(updates: List[Dict]):
    """Print a summary report of estimations"""
    print("\n" + "="*80)
    print("PATIENT ESTIMATION REPORT")
    print("="*80)

    if not updates:
        print("\nNo new estimates generated.")
        return

    print(f"\nGenerated {len(updates)} patient estimates:\n")

    # Group by confidence
    by_confidence = {'medium': [], 'low': []}
    for u in updates:
        conf = u.get('confidence', 'low')
        by_confidence.setdefault(conf, []).append(u)

    for confidence in ['medium', 'low']:
        items = by_confidence.get(confidence, [])
        if items:
            print(f"\n{confidence.upper()} CONFIDENCE ({len(items)} estimates):")
            print("-" * 60)
            for u in items[:10]:  # Show first 10
                print(f"  ID {u['dispute_id']:3}: {u['dispute_name'][:45]:<45}")
                print(f"           Estimated: {u['estimated_patients']:>8,} patients (range: {u['range']})")
                print(f"           Method: {u['method']}")
            if len(items) > 10:
                print(f"  ... and {len(items) - 10} more")

    # Summary stats
    total_estimated = sum(u['estimated_patients'] for u in updates)
    print(f"\n" + "-"*60)
    print(f"Total estimated patients across all disputes: {total_estimated:,}")
    print("="*80 + "\n")


if __name__ == "__main__":
    import sys

    # Default paths
    input_csv = "output/disputes_enriched.csv"

    if len(sys.argv) > 1:
        input_csv = sys.argv[1]

    if not Path(input_csv).exists():
        print(f"Error: Input file not found: {input_csv}")
        print("Usage: python agent/patient_estimation_agent.py [input_csv]")
        sys.exit(1)

    print("Patient Estimation Agent")
    print("="*60)
    print(f"Input: {input_csv}")
    print("Loading market reference data...")

    total, added, updates = process_disputes(input_csv)

    print(f"\nProcessed {total} disputes missing patient counts")
    print(f"Added estimates for {added} disputes")

    print_estimation_report(updates)

    # Save detailed report
    if updates:
        report_path = Path(input_csv).parent / "patient_estimation_report.json"
        with open(report_path, 'w') as f:
            json.dump(updates, f, indent=2)
        print(f"Detailed report saved to: {report_path}")
