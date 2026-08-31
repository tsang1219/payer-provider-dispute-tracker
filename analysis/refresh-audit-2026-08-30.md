# Payer–provider dispute tracker refresh audit

**Audit date:** 2026-08-30  
**Canonical baseline:** 195 rows, last substantive record updates 2026-01-20 through 2026-01-22  
**Discovery window:** 300 days through 2026-08-30

## Current baseline

- 195 rows across 2021–2025.
- 87 resolved, 74 recorded as ongoing, and 34 recorded as permanent separations.
- 137 commercial disputes, 45 Medicare Advantage disputes, 7 all-MA withdrawals, 2 multi-type, and 4 unknown.
- UnitedHealth Group is identified as parent on 49 records. Parent ownership is still unknown on 101 records, so payer-family comparisons are incomplete.
- Only 71 records are marked manually verified; 124 are not.
- Median recorded time to resolution among the 65 resolved rows with positive duration is 92 days. This is descriptive of visible, sufficiently dated records—not a population estimate.

## Data-quality findings

The canonical file has unique IDs but not necessarily unique disputes. Eight normalized provider–insurer/year pairs recur:

- Brown University Health / UnitedHealthcare: IDs 120 and 201
- Iowa Specialty Hospitals / multiple MA plans: IDs 126 and 178
- South Shore Health / UnitedHealthcare: IDs 129 and 194
- UConn Health / Aetna: IDs 132 and 196
- Salem Health / Regence: IDs 144 and 207
- Centra Health / Humana: IDs 145 and 173
- Montrose Regional Health / Humana: IDs 146 and 177
- Hackensack Meridian / Aetna: IDs 168 and 182

Six pairs reuse the same source or materially identical facts. South Shore, UConn, and Hackensack also show different dates/status snapshots and need record-level reconciliation rather than blind deletion.

The status sweep found 21 ongoing rows with recent coverage. Six were flagged as possible resolutions, but one is a false positive caused by an unrelated headline. The plausible resolution set includes Baptist/UnitedHealthcare, Kootenai/Regence, Mount Sinai/Anthem, and UConn/Aetna; the duplicate UConn rows cause the same resolution to surface twice. NewYork-Presbyterian/UnitedHealthcare requires manual review because one returned agreement concerns EmblemHealth instead.

## Discovery result

The automated scan staged 104 headlines, but these are not 104 new disputes. They contain follow-up articles, multiple stories about the same case, already-tracked disputes, commentary, labor disputes, reimbursement litigation, and government procurement.

The first clustering pass identifies 17 plausible distinct provider–payer contract disputes for source review, four clear exclusions, and one inclusion hold. See `refresh-audit-2026-08-30.csv`.

The most analytically promising complete 2026 arcs are:

- ECU Health / UnitedHealthcare: negotiation → out-of-network → reported resolution, with a reported 100,000 patients affected.
- Legacy Health / Regence: termination followed by a reported new agreement roughly one month later.
- East Tennessee Children's / Cigna: proposed termination followed by reversal.

The highest-salience open or prospective cases are:

- Lee Health / UnitedHealthcare, including a reported $100 million claims dispute and a 2027 termination announcement.
- Sentara / Anthem in Virginia.
- Lehigh Valley Health Network / UnitedHealthcare.
- Texas Tech Physicians / UnitedHealthcare.
- Cigna disputes involving UC Davis Health and MUSC.

These remain `review`, not canonical, until the provider, payer, affected products, effective dates, outcome, and primary source are verified.

## Dashboard recommendation

Do not lead the refreshed dashboard with the total patient count; most patient figures are modeled. The strongest first refreshed view is a **dispute lifecycle dashboard**:

1. New disputes first reported by month.
2. Status transitions: negotiating → out of network → resolved/permanent.
3. Median days to resolution, with missing-date coverage shown beside it.
4. Payer-family share only after the 101 unknown parent fields are reconciled.
5. A visible “evidence state” filter: manually verified / source-backed but unverified / estimated impact.

### Argument lock

- **Claim:** Public provider–payer standoffs are not one event; they are observable lifecycles, and a meaningful subset now proceeds through an actual out-of-network period before resolution.
- **Meaning:** The tracker can show duration and patient exposure, not merely count headlines.
- **Limit:** The dataset is visibility-biased, incomplete for 2026, and currently contains duplicate and unresolved records.

No chart should be published from the 2026 candidate table until the `review` rows pass the source gate.
