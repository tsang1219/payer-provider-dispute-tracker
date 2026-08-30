import { useMemo, useState } from "react";
import { DISPUTES, META, insurerFamily, type Dispute } from "./lib/data";
import StatBand from "./components/StatBand";
import FilterBar, { emptyFilters, type Filters } from "./components/FilterBar";
import USMap from "./components/USMap";
import Timeline from "./components/Timeline";
import DisputeTable from "./components/DisputeTable";
import DetailPanel from "./components/DetailPanel";

function applyFilters(all: Dispute[], f: Filters): Dispute[] {
  const q = f.q.trim().toLowerCase();
  return all.filter((d) => {
    if (f.insurers.length && !f.insurers.includes(insurerFamily(d))) return false;
    if (f.states.length && !f.states.includes(d.state ?? "")) return false;
    if (f.statuses.length && !f.statuses.includes(d.status)) return false;
    if (f.years.length && !f.years.includes(d.year ?? -1)) return false;
    if (q) {
      const hay = `${d.system} ${d.insurer} ${d.insurerParent ?? ""} ${d.hqCity ?? ""} ${d.state ?? ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

export default function App() {
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const filtered = useMemo(() => applyFilters(DISPUTES, filters), [filters]);
  const selected = useMemo(
    () => DISPUTES.find((d) => d.id === selectedId) ?? null,
    [selectedId]
  );

  const toggleState = (postal: string) =>
    setFilters((f) => ({
      ...f,
      states: f.states.includes(postal)
        ? f.states.filter((s) => s !== postal)
        : [...f.states, postal],
    }));

  return (
    <div className="min-h-screen">
      {/* Masthead */}
      <header className="border-b border-hairline">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-8 sm:py-12">
          <p className="text-xs uppercase tracking-[0.2em] text-ink-3 mb-3">
            <a href="https://healthisotherpeople.com" className="hover:text-ink-2">
              Health Is Other People
            </a>{" "}
            · A living dataset
          </p>
          <h1 className="font-serif text-4xl sm:text-5xl leading-tight tracking-tight">
            The Dispute Tracker
          </h1>
          <p className="mt-4 max-w-2xl text-ink-2 text-base sm:text-lg leading-relaxed">
            Public contract standoffs between American hospitals and insurers,
            2021–present: who's fighting whom, how long the standoffs run, and how
            they end. {META.records} disputes in the restoration baseline; public
            updates are reviewed before release.
          </p>
          <p className="mt-2 text-xs text-ink-3">
            Data as of {META.asOf}
            {META.lastRecordUpdate ? ` · last record change ${META.lastRecordUpdate}` : ""}
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 sm:px-6">
        {/* State of the fight */}
        <section className="py-8 sm:py-10">
          <StatBand disputes={filtered} total={DISPUTES.length} />
        </section>

        {/* Filters */}
        <section className="sticky top-0 z-20 -mx-4 sm:-mx-6 px-4 sm:px-6 py-3 bg-paper/95 backdrop-blur border-y border-hairline">
          <FilterBar all={DISPUTES} filters={filters} onChange={setFilters} shown={filtered.length} />
        </section>

        {/* Map */}
        <section className="py-10" id="map">
          <h2 className="font-serif text-2xl sm:text-3xl mb-1">Where the fights are</h2>
          <p className="text-sm text-ink-2 mb-5 max-w-2xl">
            Each dot is one dispute, placed at the health system's headquarters and
            sized by patients affected. Click a dot for the full record; click a
            state to filter to it.
          </p>
          <USMap
            disputes={filtered}
            activeStates={filters.states}
            onSelect={(d) => setSelectedId(d.id)}
            onToggleState={toggleState}
          />
        </section>

        {/* Timeline */}
        <section className="py-10" id="timeline">
          <h2 className="font-serif text-2xl sm:text-3xl mb-1">How long the standoffs run</h2>
          <p className="text-sm text-ink-2 mb-5 max-w-2xl">
            Every dispute as a bar from first news coverage to resolution — or to
            today, if the parties are still out of network. Click a bar for detail.
          </p>
          <Timeline disputes={filtered} onSelect={(d) => setSelectedId(d.id)} />
        </section>

        {/* Table */}
        <section className="py-10" id="records">
          <h2 className="font-serif text-2xl sm:text-3xl mb-1">The record</h2>
          <p className="text-sm text-ink-2 mb-5 max-w-2xl">
            The full ledger behind the graphics. Every row links to its primary
            source.
          </p>
          <DisputeTable disputes={filtered} onSelect={(d) => setSelectedId(d.id)} />
        </section>

        {/* Methodology */}
        <section className="py-10 border-t border-hairline" id="methodology">
          <h2 className="font-serif text-2xl mb-4">About this dataset</h2>
          <div className="grid sm:grid-cols-2 gap-8 text-sm text-ink-2 leading-relaxed max-w-4xl">
            <div>
              <h3 className="font-semibold text-ink mb-2">What counts as a dispute</h3>
              <p>
                A publicly reported contract standoff between a U.S. hospital or
                health system and an insurer — commercial, Medicare Advantage, or
                Medicaid managed care — serious enough to reach news coverage.
                Routine renewals that never made the news are not here; this is the
                visible part of the fight.
              </p>
              <h3 className="font-semibold text-ink mt-5 mb-2">Sources</h3>
              <p>
                Every dispute traces to at least one named public source — trade
                press (Becker's, Fierce Healthcare, Modern Healthcare), local news,
                or the parties' own statements. Source links are on every record.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-ink mb-2">Patients-affected figures</h3>
              <p>
                Where a count was publicly reported, that figure is used. Where it
                wasn't, it is estimated from market data (system volume × payer
                share) and labeled as an estimate on the record. Totals therefore
                mix reported and estimated counts — read them as scale, not census.
              </p>
              <h3 className="font-semibold text-ink mt-5 mb-2">Updates & corrections</h3>
              <p>
                Automated searches stage possible additions and status changes for
                human review. The current release is a restored historical baseline,
                not a claim that every record is current or complete. Spot an error,
                a better source, or a missing fight? Open an issue or pull request on{" "}
                <a href="https://github.com/tsang1219/payer-provider-dispute-tracker" className="underline decoration-hairline underline-offset-2 hover:text-ink">
                  GitHub
                </a>
                .
              </p>
              <p className="mt-3">
                <a
                  href="https://github.com/tsang1219/payer-provider-dispute-tracker"
                  className="underline decoration-hairline underline-offset-2 hover:text-ink"
                >
                  View the data, methodology, and version history
                </a>
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-hairline mt-6">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-8 text-xs text-ink-3 flex flex-wrap gap-x-6 gap-y-2 items-center">
          <span>
            © {new Date().getFullYear()}{" "}
            <a href="https://healthisotherpeople.com" className="hover:text-ink-2">
              Health Is Other People
            </a>
          </span>
          <span>Written by Andrew Tsang — 15 years inside the revenue cycle.</span>
          <span className="tabular">{META.records} disputes · 2021–present</span>
        </div>
      </footer>

      {selected && <DetailPanel dispute={selected} onClose={() => setSelectedId(null)} />}
    </div>
  );
}
