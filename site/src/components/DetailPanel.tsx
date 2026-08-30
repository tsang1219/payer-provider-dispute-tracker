import { useEffect } from "react";
import {
  effectiveDuration,
  fmtCompact,
  fmtDate,
  fmtMonths,
  PATIENTS_SOURCE_LABEL,
  STATUS_LABEL,
  statusColor,
  type Dispute,
} from "../lib/data";
import { POSTAL_TO_NAME } from "../lib/usStates";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="py-2.5 border-b border-hairline/70 flex gap-4">
      <dt className="w-32 shrink-0 text-xs uppercase tracking-wider text-ink-3 pt-0.5">{label}</dt>
      <dd className="flex-1 text-sm text-ink-2 leading-relaxed">{children}</dd>
    </div>
  );
}

export default function DetailPanel({
  dispute: d,
  onClose,
}: {
  dispute: Dispute;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const dur = effectiveDuration(d);
  const ongoing = d.status === "OON-Ongoing";

  return (
    <div className="fixed inset-0 z-40" role="dialog" aria-modal="true" aria-label={d.name}>
      <div className="absolute inset-0 bg-ink/30" onClick={onClose} />
      <aside className="absolute right-0 top-0 bottom-0 w-full sm:w-[440px] bg-card border-l border-hairline shadow-2xl overflow-y-auto well">
        <div className="sticky top-0 bg-card border-b border-hairline px-5 py-4 flex items-start gap-3">
          <div className="flex-1">
            <p className="flex items-center gap-2 text-xs mb-1.5" style={{ color: statusColor(d.status) }}>
              <span className="w-2 h-2 rounded-full" style={{ background: statusColor(d.status) }} />
              {STATUS_LABEL[d.status] ?? d.status}
            </p>
            <h3 className="font-serif text-xl leading-snug">
              {d.system} <span className="text-ink-3">vs</span> {d.insurerShort ?? d.insurer}
            </h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="w-8 h-8 shrink-0 border border-baseline rounded-full text-ink-2 hover:border-ink"
          >
            ×
          </button>
        </div>

        <dl className="px-5 pb-8">
          <Row label="Health system">
            {d.system}
            {d.hqCity && (
              <span className="text-ink-3">
                {" "}
                — {d.hqCity}, {d.hqState}
              </span>
            )}
            {d.systemType && <span className="text-ink-3"> · {d.systemType.replace(/_/g, " ")}</span>}
            {d.beds != null && d.beds > 0 && <span className="text-ink-3"> · {fmtCompact(d.beds)} beds</span>}
          </Row>
          <Row label="Insurer">
            {d.insurer}
            {d.insurerType && <span className="text-ink-3"> · {d.insurerType}</span>}
          </Row>
          <Row label="Dispute state">{d.state ? POSTAL_TO_NAME[d.state] ?? d.state : "—"}</Row>
          <Row label="Line of business">{d.disputeType ?? "—"}</Row>
          <Row label="First reported">{fmtDate(d.firstDate)}</Row>
          {d.deadlineDate && <Row label="Contract deadline">{fmtDate(d.deadlineDate)}</Row>}
          {d.oonDate && <Row label="Went out of network">{fmtDate(d.oonDate)}</Row>}
          {d.resolutionDate && <Row label="Resolved">{fmtDate(d.resolutionDate)}</Row>}
          <Row label="Duration">
            {dur != null ? (
              <>
                {fmtMonths(dur)}
                {ongoing && <span className="text-ink-3"> and counting (since first report)</span>}
              </>
            ) : (
              "—"
            )}
          </Row>
          <Row label="Patients affected">
            {d.patients != null ? (
              <>
                {fmtCompact(d.patients)}{" "}
                <span className="text-ink-3">
                  (
                  {d.patientsSource
                    ? PATIENTS_SOURCE_LABEL[d.patientsSource] ?? d.patientsSource
                    : "provenance unrecorded"}
                  )
                </span>
              </>
            ) : (
              "not established"
            )}
          </Row>
          {d.lawsuit && <Row label="Litigation">Lawsuit filed</Row>}
          {d.notes && <Row label="Notes">{d.notes}</Row>}
          <Row label="Sources">
            <div className="space-y-1">
              {d.sourceUrl ? (
                <a
                  href={d.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block underline decoration-hairline underline-offset-2 hover:text-ink break-words"
                >
                  {d.sourceName ?? "Primary source"} ↗
                </a>
              ) : (
                "—"
              )}
              {d.resolutionSourceUrl && d.resolutionSourceUrl !== d.sourceUrl && (
                <a
                  href={d.resolutionSourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block underline decoration-hairline underline-offset-2 hover:text-ink break-words"
                >
                  Resolution coverage ↗
                </a>
              )}
            </div>
          </Row>
          <Row label="Record quality">
            {d.completeness != null ? `${Math.round(d.completeness * 100)}% complete` : "—"}
            {d.verified ? " · manually verified" : ""}
          </Row>
        </dl>
      </aside>
    </div>
  );
}
