import { useMemo } from "react";
import {
  effectiveDuration,
  fmtCompact,
  fmtMonths,
  type Dispute,
} from "../lib/data";

function median(xs: number[]): number | null {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

interface Props {
  disputes: Dispute[];
  total: number;
}

export default function StatBand({ disputes, total }: Props) {
  const stats = useMemo(() => {
    const ongoing = disputes.filter((d) => d.status === "OON-Ongoing");
    const permanent = disputes.filter((d) => d.status === "OON-Permanent");
    const resolved = disputes.filter((d) => d.status === "Resolved");
    const patients = disputes.reduce((s, d) => s + (d.patients ?? 0), 0);
    const medResolution = median(
      resolved.map((d) => d.durationDays).filter((x): x is number => x != null && x > 0)
    );
    let longest: { d: Dispute; days: number } | null = null;
    for (const d of ongoing) {
      const days = effectiveDuration(d);
      if (days != null && (!longest || days > longest.days)) longest = { d, days };
    }
    return { ongoing, permanent, resolved, patients, medResolution, longest };
  }, [disputes]);

  const filteredNote = disputes.length !== total;

  const tiles: { label: string; value: string; sub?: string; color?: string }[] = [
    {
      label: "Disputes tracked",
      value: String(disputes.length),
      sub: filteredNote ? `of ${total} in the dataset` : "2021 – present",
    },
    {
      label: "Still out of network",
      value: String(stats.ongoing.length),
      sub: "recorded as ongoing at last review",
      color: "#b87400",
    },
    {
      label: "Ended in permanent splits",
      value: String(stats.permanent.length),
      sub: "no agreement — the network break stuck",
      color: "#c22f2f",
    },
    {
      label: "Patients affected",
      value: stats.patients > 0 ? fmtCompact(stats.patients) : "—",
      sub: "reported + estimated, all tracked disputes",
    },
    {
      label: "Median time to resolution",
      value: stats.medResolution != null ? fmtMonths(stats.medResolution) : "—",
      sub: `across ${stats.resolved.length} resolved disputes`,
      color: "#2a78d6",
    },
    {
      label: "Longest active standoff",
      value: stats.longest ? fmtMonths(stats.longest.days) : "—",
      sub: stats.longest
        ? `${stats.longest.d.systemShort ?? stats.longest.d.system} vs ${
            stats.longest.d.insurerShort ?? stats.longest.d.insurer
          }`
        : "no active disputes in view",
      color: "#b87400",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-px bg-hairline border border-hairline">
      {tiles.map((t) => (
        <div key={t.label} className="bg-card px-4 py-5">
          <p className="text-[11px] uppercase tracking-wider text-ink-3 leading-snug">
            {t.label}
          </p>
          <p
            className="mt-2 font-serif text-3xl sm:text-4xl leading-none tabular"
            style={t.color ? { color: t.color } : undefined}
          >
            {t.value}
          </p>
          {t.sub && <p className="mt-2 text-xs text-ink-3 leading-snug">{t.sub}</p>}
        </div>
      ))}
    </div>
  );
}
