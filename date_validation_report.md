# First Media Date Validation Report

**Generated:** 2026-01-21

## Executive Summary

This report validates `first_media_date` values against actual dates found in source URLs. The analysis reveals significant data quality issues that need correction.

### Key Findings

- **Total disputes analyzed:** 203
- **Disputes with dates in URLs:** 51 (25%)
- **Mismatches found:** 51 (100% of disputes with URL dates)
- **Critical errors (URL date earlier):** 10 disputes
- **Warnings (URL date later):** 41 disputes

**Important:** ALL disputes with extractable URL dates had mismatches. No matches were found.

---

## Critical Errors: URL Date EARLIER Than Recorded Date

These 10 disputes have `first_media_date` values that are LATER than the actual publication dates found in their source URLs. These require immediate correction.

### 1. Memorial Hermann Health System (Dispute ID: 12)
- **Recorded date:** 2022-08-01
- **Actual URL date:** 2022-03-11 (143 days earlier)
- **Source:** https://www.houstonpublicmedia.org/articles/news/health-science/2022/03/11/420914/memorial-hermann-and-blue-cross-blue-shield-reach-contract-agreement-allowing-nearly-200000-patients-to-continue-care/
- **Recommendation:** Change first_media_date to 2022-03-11

### 2. Phoenix Children's Hospital (Dispute ID: 110)
- **Recorded date:** 2025-02-01
- **Actual URL date:** 2024-11-04 (89 days earlier)
- **Source:** https://www.azfamily.com/video/2024/11/04/families-seek-solutions-after-phoenix-childrens-hospital-drops-insurer/
- **Recommendation:** Change first_media_date to 2024-11-04

### 3. Memorial Hermann Health System (Dispute ID: 56)
- **Recorded date:** 2024-01-01
- **Actual URL date:** 2023-11-01 (61 days earlier)
- **Source:** https://www.houstonpublicmedia.org/articles/news/health-science/medicine-wellness/2023/11/01/468409/memorial-hermann-at-impasse-in-negotiations-with-humana-as-their-network-contract-is-set-to-expire-jan-1/
- **Recommendation:** Change first_media_date to 2023-11-01

### 4. Ohio State Wexner Medical Center (Dispute ID: 184)
- **Recorded date:** 2025-02-01
- **Actual URL date:** 2024-12-06 (57 days earlier)
- **Source:** https://www.wosu.org/2024-12-06/anthem-and-ohio-state-strained-contract-talks-put-135-000-insured-patients-in-jeopardy
- **Recommendation:** Change first_media_date to 2024-12-06

### 5. Scripps Health (Dispute ID: 109)
- **Recorded date:** 2025-02-01
- **Actual URL date:** 2025-01-03 (29 days earlier)
- **Source:** https://www.kpbs.org/news/health/2025/01/03/scripps-health-out-of-network-anthem-blue-cross-health-insurance
- **Recommendation:** Change first_media_date to 2025-01-03

### 6. UNC Health (Dispute ID: 33)
- **Recorded date:** 2023-11-01
- **Actual URL date:** 2023-10-13 (19 days earlier)
- **Source:** https://www.axios.com/local/raleigh/2023/10/13/unc-healths-contract-dispute-with-united-healthcare
- **Recommendation:** Change first_media_date to 2023-10-13

### 7. Scripps Clinic Medical Group (Dispute ID: 24)
- **Recorded date:** 2023-11-01
- **Actual URL date:** 2023-10-16 (16 days earlier)
- **Source:** https://www.kpbs.org/news/health/2023/10/16/some-san-diego-medicare-advantage-customers-face-a-tough-choice
- **Recommendation:** Change first_media_date to 2023-10-16

### 8. UMass Memorial Health (Dispute ID: 180) ⭐ USER REPORTED
- **Recorded date:** 2025-11-01
- **Actual URL date:** 2025-10-22 (10 days earlier)
- **Source:** https://www.bostonglobe.com/2025/10/22/business/contract-network-insurance-doctor/
- **Recommendation:** Change first_media_date to 2025-10-22
- **Note:** This is the dispute you identified in your initial report

### 9. Capital Women's Care (Dispute ID: 143)
- **Recorded date:** 2025-08-01
- **Actual URL date:** 2025-07-26 (6 days earlier)
- **Source:** https://mocoshow.com/2025/07/26/capital-womens-care-contract-with-unitedhealthcare-set-to-expire-on-august-1/
- **Recommendation:** Change first_media_date to 2025-07-26

### 10. Lexington Medical Center (Dispute ID: 154)
- **Recorded date:** 2025-02-01
- **Actual URL date:** 2025-01-30 (2 days earlier)
- **Source:** https://www.wistv.com/2025/01/30/lexington-medical-center-providers-are-back-network-with-aetna/
- **Recommendation:** Change first_media_date to 2025-01-30

---

## Warnings: URL Date LATER Than Recorded Date

41 disputes have `first_media_date` values that are EARLIER than the dates in their source URLs. These may be legitimate if the first media coverage came from a different source not captured in the URL.

### Top 10 Largest Discrepancies

1. **Memorial Sloan Kettering Cancer Center (ID: 63)** - Recorded: 2024-05-01, URL: 2025-07-01 (426 days later)
2. **Broward Health (ID: 66)** - Recorded: 2024-05-01, URL: 2025-05-17 (381 days later)
3. **WakeMed Health (ID: 13)** - Recorded: 2022-11-01, URL: 2023-10-13 (346 days later)
4. **South Shore Health (ID: 194)** - Recorded: 2025-01-01, URL: 2025-11-25 (328 days later)
5. **Mass General Brigham (ID: 139)** - Recorded: 2025-02-01, URL: 2025-10-01 (242 days later)
6. **Northside Hospital (ID: 9)** - Recorded: 2022-02-01, URL: 2022-07-12 (161 days later)
7. **UConn Health (ID: 132)** - Recorded: 2025-08-01, URL: 2025-12-09 (130 days later)
8. **South Shore Health (ID: 130)** - Recorded: 2025-08-01, URL: 2025-12-01 (122 days later)
9. **South Shore Health (ID: 129)** - Recorded: 2025-08-01, URL: 2025-11-25 (116 days later)
10. **Kootenai Health (ID: 131)** - Recorded: 2025-08-01, URL: 2025-11-18 (109 days later)

**Note:** These warnings suggest that the URLs may point to follow-up articles or resolution announcements rather than the initial dispute coverage. Review recommended but not critical.

---

## Data Quality Observations

1. **Pattern of errors:** Many disputes use the 1st day of the month as `first_media_date` (e.g., 2025-02-01, 2024-08-01), suggesting approximations rather than exact dates.

2. **URL patterns detected:**
   - `/YYYY/MM/DD/` format (most common)
   - `/YYYY-MM-DD/` format
   - Works with: Boston Globe, Houston Public Media, KPBS, WOSU, Axios, CNN, and many others

3. **Coverage:** Only 25% (51/203) of disputes have dates extractable from URLs, meaning 75% use sources without date patterns in the URL.

---

## Recommendations

### Immediate Actions Required

1. **Correct the 10 critical errors** where URL dates are earlier than recorded dates
2. **Verify dispute 180 (UMass Memorial)** as reported by the user
3. **Review disputes with "01" dates** (1st of month) - likely placeholders

### Further Investigation

1. **Examine disputes without URL dates** - Consider adding `first_media_date_source` URLs that contain dates
2. **Cross-reference warnings** - For the 41 "later" cases, check if there are earlier sources
3. **Standardize date collection** - Establish process to capture exact publication dates

### Data Entry Guidelines

- Always extract exact dates from source URLs when available
- Use publication date, not article update date
- If only month/year known, use the 1st of the month but add a flag
- Document source of date in `first_media_date_source` field

---

## Methodology

**Date Extraction Patterns:**
- `/YYYY/MM/DD/` (e.g., `/2025/10/22/`)
- `/YYYY-MM-DD/` (e.g., `/2025-10-22/`)
- `YYYY/MM/DD` without slashes

**Fields Checked:**
- `primary_source_url`
- `first_media_date_source`

**Validation Logic:**
- ERROR: URL date < recorded date (data quality issue)
- WARNING: URL date > recorded date (may be legitimate)
- MATCH: URL date = recorded date (correct)

---

## Next Steps

Run the correction script to update the 10 critical errors, or manually update the CSV with the recommended dates listed above.
