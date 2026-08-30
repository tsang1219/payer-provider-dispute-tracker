# Patient Impact Estimation Framework

When direct patient counts aren't available, use these estimation approaches.

## Method 1: MA Enrollment Estimation (For Medicare Advantage Disputes)

### Data Sources
- CMS MA Enrollment by County: https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-advantagepart-d-contract-and-enrollment-data/ma-enrollment-county
- Hospital service area (from their website or AHA data)

### Formula
```
Estimated MA Patients = 
  (Payer's MA Enrollment in Hospital Counties) × 
  (Hospital's Estimated Market Share)

Where:
- Hospital Market Share ≈ 15-40% for dominant systems, 5-15% for others
- Use county-level MA enrollment from CMS data
```

### Example: Mayo Clinic vs Humana (MN)
```
Humana MA enrollment in MN (2024): ~45,000 members
Mayo Clinic market share in Rochester area: ~80%
Mayo Clinic market share statewide: ~15%

Estimated affected: 45,000 × 0.15 to 0.30 = 6,750 - 13,500 patients
(Actual reported: not disclosed, but this gives a reasonable range)
```

## Method 2: Commercial Insurance Estimation

### Data Sources
- State insurance market share reports (state DOI websites)
- Hospital payer mix (Form 990 Schedule H, or state cost reports)
- Hospital total patient volume (AHA or state health dept)

### Formula
```
Estimated Commercial Patients =
  (Hospital Annual Discharges + Outpatient Visits) ×
  (Payer's State Commercial Market Share) ×
  (Adjustment Factor for Hospital's Payer Mix)

Adjustment factors:
- Academic medical centers: 0.7 (more Medicare, less commercial)
- Community hospitals: 1.0
- For-profit systems: 1.2 (often more commercial)
```

### Example: Jefferson Health vs Cigna (PA)
```
Jefferson annual discharges: ~100,000
Jefferson outpatient visits: ~2,000,000
Cigna commercial market share in PA: ~12%

Hospital-based estimate: 100,000 × 0.12 = 12,000 inpatients
Outpatient estimate: 2,000,000 × 0.12 = 240,000 visits (but many are same patients)

Unique patient estimate: 50,000 - 100,000 range
```

## Method 3: Revenue-Based Estimation

### Formula
```
Estimated Patients =
  (Hospital Total Revenue) ×
  (Payer's Share of Revenue, if known) ÷
  (Average Revenue per Patient)

Average revenue benchmarks:
- MA patient/year: $12,000 - $18,000
- Commercial patient/year: $8,000 - $15,000
- Per inpatient stay: $15,000 - $40,000
```

### Example: UNC Health vs UnitedHealthcare (NC)
```
UNC Health revenue: ~$6B
UnitedHealthcare share (estimated): 8-12%
Revenue at risk: $480M - $720M

If mostly outpatient/physician services at $500/visit average:
$600M ÷ $500 = 1.2M visits

If estimating unique patients (5 visits/patient/year):
240,000 patients

Reported figure: 200,000 patients ← Our estimate was close!
```

## Method 4: Proxy Metrics

When you can't estimate patients, capture these proxies:

| Proxy | What it tells you | Where to find it |
|-------|-------------------|------------------|
| Hospital beds | Scale of system | AHA, Wikipedia |
| Annual discharges | Patient volume | State health dept, 990 |
| ER visits | Community reliance | State health dept |
| Payer market share | Relative exposure | State DOI reports |
| Geographic monopoly | Patient alternatives | Market analysis |

## Confidence Scoring

When using estimates, assign confidence levels:

| Confidence | Basis | Example |
|------------|-------|---------|
| **High** | Direct disclosure, regulatory filing | "Hospital announced 60,000 affected" |
| **Medium** | Calculated from CMS/state data | "Estimated from MA enrollment × market share" |
| **Low** | Rough proxy or benchmark | "Large system, likely 20,000-50,000" |
| **Unknown** | No basis for estimate | Leave blank, note in enrichment_notes |

## Data Fields to Add

```json
{
  "patients_affected": 60000,
  "patients_affected_confidence": "high",
  "patients_affected_source": "Hospital press release",
  "patients_affected_method": "direct_disclosure",
  
  // OR for estimates:
  "patients_affected": 45000,
  "patients_affected_confidence": "medium", 
  "patients_affected_source": "CMS MA enrollment + market share estimate",
  "patients_affected_method": "ma_enrollment_estimation",
  "patients_affected_range_low": 30000,
  "patients_affected_range_high": 60000
}
```

## Quick Reference: State Data Sources

| State | MA Enrollment | Commercial Market Share | Hospital Data |
|-------|---------------|------------------------|---------------|
| CA | CMS + DMHC | CDI annual report | OSHPD |
| TX | CMS | TDI market share | THCIC |
| FL | CMS + AHCA | OIR reports | AHCA |
| NY | CMS + DFS | DFS annual report | SPARCS |
| PA | CMS | PID reports | PHC4 |
| MA | CMS + CHIA | DOI reports | CHIA |
| NC | CMS | NCDOI | NC DHHS |
| GA | CMS | OCI reports | DCH |
| OH | CMS | ODI | OHA |
| MN | CMS | Commerce Dept | MDH |

## Agent Search Queries for Estimation Data

```
# For MA enrollment
"CMS Medicare Advantage enrollment" "{county}" "{payer}" 2024

# For hospital market share  
"{health_system}" market share "{metro_area}" OR "{state}"
"{health_system}" annual report discharges patients served

# For payer market share
"{state}" health insurance market share 2024
"{payer}" "{state}" commercial enrollment members

# For regulatory filings
"{health_system}" "{insurer}" "{state}" department of insurance
"{health_system}" network adequacy filing
```

## Batch Estimation Workflow

For disputes missing patient counts:

1. **Classify dispute type** (MA vs Commercial vs Both)
2. **Look up reference data:**
   - Hospital annual revenue/volume
   - Payer market share in state
   - CMS MA enrollment if applicable
3. **Apply appropriate formula**
4. **Assign confidence level**
5. **Document method in enrichment_notes**

This lets you have *something* for visualization even when direct numbers aren't available, while being transparent about certainty levels.
