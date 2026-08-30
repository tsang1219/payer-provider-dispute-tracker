import { useMemo, useState } from "react";
import {
  effectiveDuration,
  fmtCompact,
  fmtDate,
  fmtMonths,
  patientsIsEstimate,
  STATUS_SHORT,
  statusColor,
  type Dispute,
} from "../lib/data";

type Col = "system" | "insurer" | "state" | "first" | "duration" | "patients" | "status";

const HEADERS: { key: Col; label: string; numeric?: boolean }[] = [
  { key: "system", label: "Health system" },
  { key: "insurer", label: "Insurer" },
  { key: "state", label: "State" },
  { key: "first", label: "First reported" },
  { key: "duration", label: "Duration", numeric: true },
  { key: "patients", label: "Patients", numeric: true },
  { key: "status", label: "Status" },
];

export default function DisputeTable({
  disputes,
  onSelect,
}: {
  disputes: Dispute[];
  onSelect: (d: Dispute) => void;
}) {
  const [sortCol, setSortCol] = useState<Col>("first");
  const [asc, setAsc] = useState<boolean>(false);

  const sorted = useMemo(() => {
    const val = (d: Dispute): string | number => {
      switch (sortCol) {
        case "system":
          return d.system.toLowerCase();
        case "insurer":
          return (d.insurerShort ?? d.insurer).toLowerCase();
        case "state":
          return d.state ?? "";
        case "first":
          return d.firstDate ?? "";
        case "duration":
          return effectiveDuration(d) ?? -1;
        case "patients":
          return d.patients ?? -1;
        case "status":
          return d.status;
      }
    };
    return [...disputes].sort((a, b) => {
      const va = val(a);
      const vb = val(b);
      const cmp = typeof va === "number" ? va - (vb as number) : String(va).localeCompare(String(vb));
      return asc ? cmp : -cmp;
    });
  }, [disputes, sortCol, asc]);

  const clickHeader = (c: Col) => {
    if (c === sortCol) setAsc((a) => !a);
    else {
      setSortCol(c);
      setAsc(c === "system" || c === "insurer" || c === "state");
    }
  };

  return (
    <div className="border border-hairline bg-card">
      <div className="well overflow-auto max-h-[520px]">
        <table className="w-full text-sm min-w-[720px]">
          <thead className="sticky top-0 z-10 bg-card">
            <tr className="border-b border-hairline text-left">
              {HEADERS.map((h) => (
                <th
                  key={h.key}
                  className={`px-3 py-2.5 font-medium text-xs uppercase tracking-wider text-ink-3 cursor-pointer select-none hover:text-ink whitespace-nowrap ${
                    h.numeric ? "text-right" : ""
                  }`}
                  onClick={() => clickHeader(h.key)}
                  aria-sort={sortCol === h.key ? (asc ? "ascending" : "descending") : undefined}
                >
                  {h.label}
                  {sortCol === h.key ? (asc ? " ↑" : " ↓") : ""}
                </th>
              ))}
              <th className="px-3 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((d) => {
              const dur = effectiveDuration(d);
              const ongoing = d.status === "OON-Ongoing";
              return (
                <tr
                  key={d.id}
                  className="border-b border-hairline/60 hover:bg-paper cursor-pointer"
                  onClick={() => onSelect(d)}
                >
                  <td className="px-3 py-2 max-w-[220px] truncate">{d.system}</td>
                  <td className="px-3 py-2 max-w-[180px] truncate text-ink-2">
                    {d.insurerShort ?? d.insurer}
                  </td>
                  <td className="px-3 py-2 text-ink-2">{d.state ?? "—"}</td>
                  <td className="px-3 py-2 whitespace-nowrap text-ink-2 tabular">
                    {fmtDate(d.firstDate)}
                  </td>
                  <td className="px-3 py-2 text-right whitespace-nowrap tabular text-ink-2">
                    {dur != null ? `${fmtMonths(dur)}${ongoing ? " +" : ""}` : "—"}
                  </td>
                  <td className="px-3 py-2 text-right whitespace-nowrap tabular text-ink-2">
                    {d.patients != null
                      ? `${fmtCompact(d.patients)}${patientsIsEstimate(d) ? "*" : ""}`
                      : "—"}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <span className="inline-flex items-center gap-1.5 text-xs">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ background: statusColor(d.status) }}
                      />
                      {STATUS_SHORT[d.status] ?? d.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    {d.sourceUrl && (
                      <a
                        href={d.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-xs text-ink-3 hover:text-ink underline underline-offset-2 whitespace-nowrap"
                      >
                        source ↗
                      </a>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {sorted.length === 0 && (
          <p className="px-4 py-8 text-sm text-ink-3">No disputes match the current filters.</p>
        )}
      </div>
      <p className="px-4 py-2 border-t border-hairline text-[11px] text-ink-3">
        * patient count is an estimate from market data, not a reported figure — see each
        record for provenance.
      </p>
    </div>
  );
}
