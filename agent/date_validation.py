"""
Date validation utilities for dispute data quality checks

Provides comprehensive validation for:
- Date format standardization
- Chronological ordering
- Source attribution
- Quarter alignment
- Earliest date detection
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

DATE_FORMATS = (
    "%Y-%m-%d", "%Y-%m", "%Y", "%m/%d/%Y", "%m/%d/%y",
    "%B %d, %Y", "%b %d, %Y", "%B %Y", "%b %Y",
)


# Quarter mapping
QUARTER_MAP = {
    1: 'Q1', 2: 'Q1', 3: 'Q1',
    4: 'Q2', 5: 'Q2', 6: 'Q2',
    7: 'Q3', 8: 'Q3', 9: 'Q3',
    10: 'Q4', 11: 'Q4', 12: 'Q4'
}


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats to datetime object"""
    if not date_str or not isinstance(date_str, str):
        return None

    date_str = date_str.strip()
    if not date_str:
        return None

    normalized = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", date_str, flags=re.IGNORECASE)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    return None


def standardize_date(date_str: str, default_day: int = 1) -> Optional[str]:
    """
    Standardize date to YYYY-MM-DD format

    Args:
        date_str: Input date in various formats
        default_day: Day to use if only month/year provided (default: 1)

    Returns:
        Date in YYYY-MM-DD format or None if unparseable
    """
    # Try manual parsing first for common formats to control default_day
    # "Aug 2021" or "August 2021"
    match = re.match(r'(\w+)\s+(\d{4})', date_str, re.IGNORECASE)
    if match:
        month_str, year_str = match.groups()
        try:
            dt = datetime.strptime(f"{month_str} {default_day}, {year_str}", "%B %d, %Y")
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            try:
                dt = datetime.strptime(f"{month_str} {default_day}, {year_str}", "%b %d, %Y")
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass

    # "2023-02" (year-month only)
    match = re.match(r'(\d{4})-(\d{2})$', date_str)
    if match:
        year, month = match.groups()
        return f"{year}-{month}-{default_day:02d}"

    # Try general parsing (for dates with specific days)
    dt = parse_date(date_str)
    if dt:
        return dt.strftime('%Y-%m-%d')

    return None


def get_date_precision(date_str: str) -> str:
    """
    Determine precision of date string

    Returns: 'day', 'month', 'quarter', or 'year'
    """
    if not date_str:
        return 'unknown'

    # ISO format with day: YYYY-MM-DD
    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
        return 'day'

    # Year-month only: YYYY-MM or "Aug 2021"
    if re.match(r'\d{4}-\d{2}$', date_str) or re.match(r'\w+\s+\d{4}', date_str):
        return 'month'

    # Year only
    if re.match(r'^\d{4}$', date_str):
        return 'year'

    # Try parsing to determine
    dt = parse_date(date_str)
    if dt:
        if dt.day == 1 and 'first' not in date_str.lower():
            return 'month'
        return 'day'

    return 'unknown'


def validate_first_media_date(dispute: Dict) -> Dict[str, Any]:
    """
    Validate that first_media_date is the earliest date and has source

    Returns:
        {
            'valid': bool,
            'issues': List[str],
            'warnings': List[str]
        }
    """
    issues = []
    warnings = []

    first_media_date = dispute.get('first_media_date')

    # Check if first_media_date has a source
    if first_media_date:
        first_media_source = dispute.get('first_media_date_source', '').strip()
        primary_source = dispute.get('primary_source_url', '').strip()

        if not first_media_source:
            if not primary_source:
                issues.append("first_media_date has no source URL")
            else:
                warnings.append("first_media_date using primary_source_url (should have dedicated source)")

    # Check quarter alignment
    if first_media_date and dispute.get('quarter_first_reported'):
        dt = parse_date(first_media_date)
        if dt:
            expected_quarter = QUARTER_MAP[dt.month]
            actual_quarter = dispute.get('quarter_first_reported')
            if expected_quarter != actual_quarter:
                issues.append(
                    f"first_media_date {first_media_date} (month {dt.month}) "
                    f"not in quarter {actual_quarter} (expected {expected_quarter})"
                )

    # Check if first_media_date is the earliest among all timeline dates
    if first_media_date:
        first_dt = parse_date(first_media_date)
        if first_dt:
            # Check against other dates
            for date_field in ['deadline_date', 'oon_effective_date', 'resolution_date']:
                other_date = dispute.get(date_field)
                if other_date:
                    other_dt = parse_date(other_date)
                    if other_dt and other_dt < first_dt:
                        issues.append(
                            f"{date_field} ({other_date}) is earlier than "
                            f"first_media_date ({first_media_date})"
                        )

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings
    }


def validate_date_sequence(dispute: Dict) -> Dict[str, Any]:
    """
    Validate chronological order of events

    Expected sequence:
    first_media_date <= deadline_date <= oon_effective_date <= resolution_date

    Returns:
        {
            'valid': bool,
            'violations': List[str]
        }
    """
    violations = []
    dates = []

    # Build ordered list of dates
    date_fields = [
        ('first_media_date', dispute.get('first_media_date')),
        ('deadline_date', dispute.get('deadline_date')),
        ('oon_effective_date', dispute.get('oon_effective_date')),
    ]

    # Only include resolution_date if dispute is resolved
    if dispute.get('outcome_status') == 'Resolved':
        date_fields.append(('resolution_date', dispute.get('resolution_date')))

    # Parse dates
    for field_name, date_str in date_fields:
        if date_str:
            dt = parse_date(date_str)
            if dt:
                dates.append((field_name, dt, date_str))

    # Check for violations (dates going backwards)
    for i in range(len(dates) - 1):
        curr_field, curr_dt, curr_str = dates[i]
        next_field, next_dt, next_str = dates[i + 1]

        if curr_dt > next_dt:
            violations.append(
                f"{curr_field} ({curr_str}) is after "
                f"{next_field} ({next_str})"
            )

    return {
        'valid': len(violations) == 0,
        'violations': violations
    }


def validate_resolution_date_source(dispute: Dict) -> Dict[str, Any]:
    """
    Validate resolution date has proper source attribution

    Returns:
        {
            'valid': bool,
            'issues': List[str],
            'warnings': List[str]
        }
    """
    issues = []
    warnings = []

    outcome_status = dispute.get('outcome_status', '')
    resolution_date = dispute.get('resolution_date', '').strip()

    if outcome_status == 'Resolved':
        # Resolved disputes MUST have resolution_date
        if not resolution_date:
            issues.append("Status is Resolved but no resolution_date")
        else:
            # Check source attribution
            resolution_source = dispute.get('resolution_date_source', '').strip()
            primary_source = dispute.get('primary_source_url', '').strip()

            if not resolution_source:
                if not primary_source:
                    issues.append("resolution_date has no source URL")
                else:
                    warnings.append("resolution_date using primary_source_url (should have dedicated source)")

    # Check for inconsistency: resolution date but not resolved
    elif resolution_date and outcome_status in ['OON-Ongoing', 'OON-Negotiating', 'OON-Temporary']:
        warnings.append(
            f"Has resolution_date ({resolution_date}) but status is {outcome_status}"
        )

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings
    }


def determine_latest_status_date(dispute: Dict) -> Optional[str]:
    """
    Determine most recent date related to dispute status

    For resolved disputes: resolution_date
    For ongoing disputes: MAX(oon_effective_date, deadline_date, last_updated)

    Returns:
        Date in YYYY-MM-DD format or None
    """
    outcome_status = dispute.get('outcome_status', '')

    # For resolved disputes, use resolution date
    if outcome_status == 'Resolved':
        resolution_date = dispute.get('resolution_date')
        if resolution_date:
            return standardize_date(resolution_date)

    # For ongoing disputes, find latest date
    dates = []

    for field in ['oon_effective_date', 'deadline_date', 'first_media_date']:
        date_str = dispute.get(field)
        if date_str:
            dt = parse_date(date_str)
            if dt:
                dates.append(dt)

    # Include last_updated if available
    last_updated = dispute.get('last_updated')
    if last_updated:
        dt = parse_date(last_updated)
        if dt:
            dates.append(dt)

    if dates:
        return max(dates).strftime('%Y-%m-%d')

    return None


def validate_oon_effective_date(dispute: Dict) -> Dict[str, Any]:
    """
    Validate OON effective date for disputes with OON status

    Returns:
        {
            'valid': bool,
            'issues': List[str],
            'warnings': List[str]
        }
    """
    issues = []
    warnings = []

    outcome_status = dispute.get('outcome_status', '')

    # OON status disputes SHOULD have oon_effective_date
    if outcome_status in ['OON-Ongoing', 'OON-Permanent']:
        oon_date = dispute.get('oon_effective_date', '').strip()

        if not oon_date:
            warnings.append(f"OON status ({outcome_status}) but missing oon_effective_date")
        else:
            # Check source attribution
            oon_source = dispute.get('oon_effective_date_source', '').strip()
            primary_source = dispute.get('primary_source_url', '').strip()

            if not oon_source:
                if not primary_source:
                    issues.append("oon_effective_date has no source URL")
                else:
                    warnings.append("oon_effective_date using primary_source_url (should have dedicated source)")

    # Validate chronological: first_media_date <= oon_effective_date
    if dispute.get('first_media_date') and dispute.get('oon_effective_date'):
        first_dt = parse_date(dispute['first_media_date'])
        oon_dt = parse_date(dispute['oon_effective_date'])

        if first_dt and oon_dt and oon_dt < first_dt:
            issues.append(
                f"oon_effective_date ({dispute['oon_effective_date']}) "
                f"before first_media_date ({dispute['first_media_date']})"
            )

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings
    }


def validate_all_dates(dispute: Dict) -> Dict[str, Any]:
    """
    Run all date validations on a dispute record

    Returns:
        {
            'dispute_id': int,
            'valid': bool,
            'first_media_validation': dict,
            'sequence_validation': dict,
            'resolution_validation': dict,
            'oon_validation': dict,
            'latest_status_date': str,
            'error_count': int,
            'warning_count': int
        }
    """
    first_media = validate_first_media_date(dispute)
    sequence = validate_date_sequence(dispute)
    resolution = validate_resolution_date_source(dispute)
    oon = validate_oon_effective_date(dispute)
    latest_date = determine_latest_status_date(dispute)

    # Count issues
    error_count = (
        len(first_media.get('issues', [])) +
        len(sequence.get('violations', [])) +
        len(resolution.get('issues', [])) +
        len(oon.get('issues', []))
    )

    warning_count = (
        len(first_media.get('warnings', [])) +
        len(resolution.get('warnings', [])) +
        len(oon.get('warnings', []))
    )

    return {
        'dispute_id': dispute.get('dispute_id'),
        'valid': error_count == 0,
        'first_media_validation': first_media,
        'sequence_validation': sequence,
        'resolution_validation': resolution,
        'oon_validation': oon,
        'latest_status_date': latest_date,
        'error_count': error_count,
        'warning_count': warning_count
    }
