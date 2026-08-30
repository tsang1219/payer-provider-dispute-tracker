import { useMemo, useState } from "react";
import {
  AS_OF,
  endDate,
  effectiveDuration,
  fmtDate,
  fmtMonths,
  parseISO,
  STATUS_SHORT,
  statusColor,
  type Dispute,
} from "../lib/data";

type SortKey = "start" | "duration";

interface Row {
  d: Dispute;
  startMs: number;
  endMs: number | null;
  ongoing: boolean;
}

export default function Timeline({
  disputes,
  onSelect,
}: {
  disputes: Dispute[];
  onSelect: (d: Dispute) => void;
}) {
  const [sort, setSort] = useState<SortKey>("start");

  const { rows, domainStart, domainEnd, yearTicks } = useMemo(() => {
    const rows: Row[] = disputes
      .filter((d) => d.firstDate)
      .map((d) => {
        const { end, ongoing } = endDate(d);
        return {
          d,
          startMs: parseISO(d.firstDate!),
          endMs: end ? parseISO(end) : null,
          ongoing,
        };
      });

    rows.sort((a, b) => {
      if (sort === "duration") {
        const da = effectiveDuration(a.d) ?? -1;
        const db = effectiveDuration(b.d) ?? -1;
        return db - da;
      }
      return a.startMs - b.startMs;
    });

    const asOfMs = parseISO(AS_OF);
    const minMs = rows.length ? Math.min(...rows.map((r) => r.startMs)) : parseISO("2021-01-01");
    const domainStart = new Date(minMs);
    domainStart.setMonth(domainStart.getMonth() - 1);
    const domainEnd = asOfMs + 45 * 86400000;

    const yearTicks: number[] = [];
    for (let y = domainStart.getFullYear() + 1; y <= new Date(domainEnd).getFullYear(); y++) {
      yearTicks.push(new Date(y, 0, 1).getTime());
    }
    return { rows, domainStart: domainStart.getTime(), domainEnd, yearTicks };
  }, [disputes, sort]);

  const pct = (ms: number) =>
    ((ms - domainStart) / (domainEnd - domainStart)) * 100;

  return (
    <div className="border border-hairline bg-card">
      {/* header: sort + axis */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-hairline text-xs text-ink-2">
        <span>Sort:</span>
        <button
          className={`px-2 py-1 rounded-full border ${
            sort === "start" ? "border-ink bg-ink text-paper" : "border-baseline hover:border-ink-3"
          }`}
          onClick={() => setSort("start")}
        >
          By start date
        </button>
        <button
          className={`px-2 py-1 rounded-full border ${
            sort === "duration" ? "border-ink bg-ink text-paper" : "border-baseline hover:border-ink-3"
          }`}
          onClick={() => setSort("duration")}
        >
          Longest first
        </button>
        <span className="ml-auto hidden sm:inline text-ink-3">
          bar = first report → resolution, or → today if ongoing
        </span>
      </div>

      <div className="well overflow-y-auto max-h-[560px]">
        <div className="min-w-[560px]">
          {/* year axis */}
          <div className="sticky top-0 z-10 bg-card border-b border-hairline">
            <div className="relative h-7 ml-[180px] sm:ml-[220px] mr-4">
              {yearTicks.map((t) => (
                <span
                  key={t}
                  className="absolute top-1.5 text-[11px] text-ink-3 -translate-x-1/2 tabular"
                  style={{ left: `${pct(t)}%` }}
                >
                  {new Date(t).getFullYear()}
                </span>
              ))}
            </div>
          </div>

          {rows.map(({ d, startMs, endMs, ongoing }) => {
            const left = pct(startMs);
            const right = endMs != null ? pct(endMs) : left;
            const width = Math.max(right - left, 0.35);
            const color = statusColor(d.status);
            const dur = effectiveDuration(d);
            return (
              <button
                key={d.id}
                onClick={() => onSelect(d)}
                className="group flex w-full items-center gap-0 text-left hover:bg-paper focus:bg-paper focus:outline-none"
                title={`${d.system} vs ${d.insurerShort ?? d.insurer} — ${
                  STATUS_SHORT[d.status] ?? d.status
                }, ${fmtDate(d.firstDate)}${
                  dur != null ? `, ${fmtMonths(dur)}${ongoing ? " and counting" : ""}` : ""
                }`}
              >
                <span className="w-[180px] sm:w-[220px] shrink-0 pl-4 pr-2 py-[3px] text-[11px] leading-tight text-ink-2 truncate group-hover:text-ink">
                  {d.systemShort ?? d.system}
                  <span className="text-ink-3"> vs {d.insurerShort ?? d.insurer}</span>
                </span>
                <span className="relative flex-1 h-[14px] mr-4">
                  {/* year gridlines */}
                  {yearTicks.map((t) => (
                    <span
                      key={t}
                      className="absolute top-0 bottom-0 w-px bg-hairline"
                      style={{ left: `${pct(t)}%` }}
                    />
                  ))}
                  <span
                    className="absolute top-[3px] h-[8px] rounded-full"
                    style={{
                      left: `${left}%`,
                      width: `${width}%`,
                      background: ongoing
                        ? `linear-gradient(90deg, ${color} 70%, ${color}55 100%)`
                        : color,
                      opacity: 0.9,
                    }}
                  />
                  {endMs == null && !ongoing && (
                    <span
                      className="absolute top-[1px] text-[9px] leading-none text-ink-3"
                      style={{ left: `calc(${left}% + 8px)` }}
                    >
                      end date unknown
                    </span>
                  )}
                  {ongoing && (
                    <span
                      className="absolute top-[2px] text-[9px] leading-none tabular"
                      style={{ left: `calc(${right}% + 4px)`, color }}
                    >
                      ▸
                    </span>
                  )}
                </span>
              </button>
            );
          })}

          {rows.length === 0 && (
            <p className="px-4 py-8 text-sm text-ink-3">No disputes match the current filters.</p>
          )}
        </div>
      </div>
    </div>
  );
}
