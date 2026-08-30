import { useEffect, useMemo, useRef, useState } from "react";
import {
  insurerFamily,
  STATUS_ORDER,
  STATUS_SHORT,
  statusColor,
  type Dispute,
} from "../lib/data";
import { POSTAL_TO_NAME } from "../lib/usStates";

export interface Filters {
  insurers: string[];
  states: string[];
  statuses: string[];
  years: number[];
  q: string;
}

export const emptyFilters: Filters = {
  insurers: [],
  states: [],
  statuses: [],
  years: [],
  q: "",
};

/* ---------- generic multiselect dropdown ---------- */

interface Option {
  value: string;
  label: string;
  count: number;
  swatch?: string;
}

function MultiSelect({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: Option[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const toggle = (v: string) =>
    onChange(selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v]);

  const active = selected.length > 0;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={`text-sm px-3 py-1.5 border rounded-full transition-colors ${
          active
            ? "border-ink bg-ink text-paper"
            : "border-baseline text-ink-2 hover:border-ink-3 bg-card"
        }`}
      >
        {label}
        {active ? ` · ${selected.length}` : ""}
        <span className="ml-1 text-[10px] align-middle">▾</span>
      </button>
      {open && (
        <div className="absolute left-0 mt-2 w-64 max-h-72 overflow-auto well bg-card border border-hairline rounded-md shadow-lg z-30 py-1">
          {active && (
            <button
              type="button"
              className="w-full text-left px-3 py-1.5 text-xs text-ink-3 hover:text-ink"
              onClick={() => onChange([])}
            >
              Clear {label.toLowerCase()}
            </button>
          )}
          {options.map((o) => (
            <label
              key={o.value}
              className="flex items-center gap-2 px-3 py-1.5 text-sm cursor-pointer hover:bg-paper"
            >
              <input
                type="checkbox"
                checked={selected.includes(o.value)}
                onChange={() => toggle(o.value)}
                className="accent-[#1a1916]"
              />
              {o.swatch && (
                <span
                  className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ background: o.swatch }}
                />
              )}
              <span className="flex-1 truncate">{o.label}</span>
              <span className="text-xs text-ink-3 tabular">{o.count}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- the bar ---------- */

export default function FilterBar({
  all,
  filters,
  onChange,
  shown,
}: {
  all: Dispute[];
  filters: Filters;
  onChange: (f: Filters) => void;
  shown: number;
}) {
  const opts = useMemo(() => {
    const count = (xs: string[]) => {
      const m = new Map<string, number>();
      for (const x of xs) m.set(x, (m.get(x) ?? 0) + 1);
      return m;
    };
    const insurers = count(all.map(insurerFamily));
    const states = count(all.map((d) => d.state ?? "??"));
    const statuses = count(all.map((d) => d.status));
    const years = count(all.map((d) => String(d.year ?? "")));

    return {
      insurers: [...insurers.entries()]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .map(([v, c]) => ({ value: v, label: v, count: c })),
      states: [...states.entries()]
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([v, c]) => ({ value: v, label: POSTAL_TO_NAME[v] ?? v, count: c })),
      statuses: STATUS_ORDER.filter((s) => statuses.has(s)).map((s) => ({
        value: s,
        label: STATUS_SHORT[s],
        count: statuses.get(s) ?? 0,
        swatch: statusColor(s),
      })),
      years: [...years.entries()]
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([v, c]) => ({ value: v, label: v, count: c })),
    };
  }, [all]);

  const anyActive =
    filters.insurers.length ||
    filters.states.length ||
    filters.statuses.length ||
    filters.years.length ||
    filters.q;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <input
        type="search"
        placeholder="Search system, insurer, city…"
        value={filters.q}
        onChange={(e) => onChange({ ...filters, q: e.target.value })}
        className="text-sm px-3 py-1.5 border border-baseline rounded-full bg-card w-52 sm:w-60 focus:outline-none focus:border-ink placeholder:text-ink-3"
        aria-label="Search disputes"
      />
      <MultiSelect
        label="Insurer"
        options={opts.insurers}
        selected={filters.insurers}
        onChange={(v) => onChange({ ...filters, insurers: v })}
      />
      <MultiSelect
        label="State"
        options={opts.states}
        selected={filters.states}
        onChange={(v) => onChange({ ...filters, states: v })}
      />
      <MultiSelect
        label="Status"
        options={opts.statuses}
        selected={filters.statuses}
        onChange={(v) => onChange({ ...filters, statuses: v })}
      />
      <MultiSelect
        label="Year"
        options={opts.years}
        selected={filters.years.map(String)}
        onChange={(v) => onChange({ ...filters, years: v.map(Number) })}
      />
      {anyActive ? (
        <button
          type="button"
          onClick={() => onChange(emptyFilters)}
          className="text-xs text-ink-3 hover:text-ink underline underline-offset-2"
        >
          Reset
        </button>
      ) : null}
      <span className="ml-auto text-xs text-ink-3 tabular">
        {shown} dispute{shown === 1 ? "" : "s"} shown
      </span>
    </div>
  );
}
