import raw from "../data/disputes.json";

export interface Dispute {
  id: number;
  name: string;
  system: string;
  systemShort: string | null;
  systemType: string | null;
  hqCity: string | null;
  hqState: string | null;
  lat: number | null;
  lon: number | null;
  beds: number | null;
  insurer: string;
  insurerShort: string | null;
  insurerParent: string | null;
  insurerType: string | null;
  disputeType: string | null;
  state: string | null;
  year: number | null;
  quarter: string | null;
  firstDate: string | null;
  deadlineDate: string | null;
  oonDate: string | null;
  resolutionDate: string | null;
  durationDays: number | null;
  status: string;
  patients: number | null;
  patientsSource: string | null;
  lawsuit: boolean | null;
  sourceName: string | null;
  sourceUrl: string | null;
  resolutionSourceUrl: string | null;
  notes: string | null;
  verified: boolean | null;
  completeness: number | null;
}

export interface Meta {
  generated: string;
  asOf: string;
  records: number;
  sourceFile: string;
  lastRecordUpdate: string | null;
}

const payload = raw as unknown as { meta: Meta; disputes: Dispute[] };

export const META: Meta = payload.meta;
export const DISPUTES: Dispute[] = payload.disputes;

/* ---------- status ---------- */

export const STATUS_ORDER = ["OON-Ongoing", "OON-Permanent", "Resolved"] as const;

export const STATUS_LABEL: Record<string, string> = {
  Resolved: "Resolved",
  "OON-Ongoing": "Out of network — ongoing",
  "OON-Permanent": "Out of network — permanent",
  "OON-Temporary": "Out of network — temporary",
  "OON-Negotiating": "Negotiating",
  "OON-Partial": "Partially resolved",
  Unknown: "Unknown",
};

export const STATUS_SHORT: Record<string, string> = {
  Resolved: "Resolved",
  "OON-Ongoing": "Ongoing",
  "OON-Permanent": "Permanent split",
  "OON-Temporary": "Temporary OON",
  "OON-Negotiating": "Negotiating",
  "OON-Partial": "Partial",
  Unknown: "Unknown",
};

/* Validated 3-slot palette (all >=3:1 on #faf9f6, worst CVD dE 21.2). */
export const STATUS_COLOR: Record<string, string> = {
  Resolved: "#2a78d6",
  "OON-Ongoing": "#b87400",
  "OON-Permanent": "#c22f2f",
  "OON-Temporary": "#b87400",
  "OON-Negotiating": "#b87400",
  "OON-Partial": "#2a78d6",
  Unknown: "#898781",
};

export function statusColor(s: string): string {
  return STATUS_COLOR[s] ?? "#898781";
}

/* ---------- insurer family (parent if known, else normalized name) ---------- */

export function insurerFamily(d: Dispute): string {
  return d.insurerParent || d.insurerShort || d.insurer;
}

/* ---------- dates & durations ---------- */

export const AS_OF = META.asOf; // ISO date the data was generated

export function parseISO(s: string): number {
  return new Date(s + "T00:00:00").getTime();
}

const MS_DAY = 86400000;

export function daysBetween(a: string, b: string): number {
  return Math.round((parseISO(b) - parseISO(a)) / MS_DAY);
}

/** End of the bar for timeline purposes; null = unknown end. */
export function endDate(d: Dispute): { end: string | null; ongoing: boolean } {
  if (d.status === "OON-Ongoing") return { end: AS_OF, ongoing: true };
  if (d.resolutionDate) return { end: d.resolutionDate, ongoing: false };
  if (d.status === "OON-Permanent")
    return { end: d.oonDate || d.deadlineDate || null, ongoing: false };
  return { end: null, ongoing: false };
}

/** Duration in days: recorded if present; for ongoing, days since first report. */
export function effectiveDuration(d: Dispute): number | null {
  if (d.status === "OON-Ongoing" && d.firstDate) return daysBetween(d.firstDate, AS_OF);
  if (d.durationDays != null) return d.durationDays;
  const { end } = endDate(d);
  if (d.firstDate && end) return daysBetween(d.firstDate, end);
  return null;
}

/* ---------- formatting ---------- */

export function fmtInt(n: number): string {
  return n.toLocaleString("en-US");
}

export function fmtCompact(n: number): string {
  if (n >= 1e6) return (n / 1e6).toFixed(n >= 10e6 ? 0 : 1) + "M";
  if (n >= 1e3) return Math.round(n / 1e3) + "K";
  return String(Math.round(n));
}

export function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function fmtMonths(days: number): string {
  const m = days / 30.44;
  if (m < 1) return `${days} days`;
  if (m < 24) return `${m.toFixed(m < 10 ? 1 : 0)} months`;
  return `${(m / 12).toFixed(1)} years`;
}

export const PATIENTS_SOURCE_LABEL: Record<string, string> = {
  extracted_from_notes_patients: "reported figure",
  estimated_commercial_estimation: "estimated from market data",
  estimated_ma_enrollment_estimation: "estimated from MA enrollment",
  known_calibration: "verified figure",
  revenue_based_estimation: "estimated from revenue data",
};

export function patientsIsEstimate(d: Dispute): boolean {
  return !!d.patientsSource && d.patientsSource.startsWith("estimated");
}
