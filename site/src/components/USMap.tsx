import { useCallback, useMemo, useRef, useState } from "react";
import { geoAlbersUsa, geoPath } from "d3-geo";
import { feature, mesh } from "topojson-client";
import statesTopo from "us-atlas/states-albers-10m.json";
import {
  fmtCompact,
  fmtDate,
  patientsIsEstimate,
  STATUS_SHORT,
  statusColor,
  STATUS_ORDER,
  type Dispute,
} from "../lib/data";
import { STATE_NAME_TO_POSTAL } from "../lib/usStates";

const W = 975;
const H = 610;

/* us-atlas states-albers-10m is pre-projected to a 975x610 frame produced by
   geoAlbersUsa().scale(1300).translate([487.5, 305]) — the same projection
   places the lat/lon dispute points in the same coordinate space. */
const projection = geoAlbersUsa().scale(1300).translate([W / 2, H / 2]);
const path = geoPath();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const topo = statesTopo as any;
const statesFeatures = (feature(topo, topo.objects.states) as any).features as Array<{
  properties: { name: string };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  geometry: any;
}>;
const stateBorders = mesh(topo, topo.objects.states, (a: unknown, b: unknown) => a !== b);

interface Placed {
  d: Dispute;
  x: number;
  y: number;
  r: number;
}

interface Hover {
  d: Dispute;
  cx: number;
  cy: number;
}

export default function USMap({
  disputes,
  activeStates,
  onSelect,
  onToggleState,
}: {
  disputes: Dispute[];
  activeStates: string[];
  onSelect: (d: Dispute) => void;
  onToggleState: (postal: string) => void;
}) {
  const [view, setView] = useState({ k: 1, tx: 0, ty: 0 });
  const [hover, setHover] = useState<Hover | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; tx: number; ty: number; moved: boolean } | null>(null);

  const placed = useMemo<Placed[]>(() => {
    const max = Math.max(1, ...disputes.map((d) => d.patients ?? 0));
    const out: Placed[] = [];
    for (const d of disputes) {
      if (d.lat == null || d.lon == null) continue;
      const p = projection([d.lon, d.lat]);
      if (!p) continue;
      const r = d.patients ? 4 + 18 * Math.sqrt(d.patients / max) : 3.5;
      out.push({ d, x: p[0], y: p[1], r });
    }
    // draw big dots first so small ones stay clickable
    return out.sort((a, b) => b.r - a.r);
  }, [disputes]);

  const clampView = (k: number, tx: number, ty: number) => {
    const kk = Math.min(8, Math.max(1, k));
    const minTx = W - W * kk;
    const minTy = H - H * kk;
    return {
      k: kk,
      tx: Math.min(0, Math.max(minTx, tx)),
      ty: Math.min(0, Math.max(minTy, ty)),
    };
  };

  /** convert a mouse event to svg user coords */
  const svgPoint = useCallback((e: { clientX: number; clientY: number }) => {
    const el = wrapRef.current!;
    const rect = el.getBoundingClientRect();
    return {
      x: ((e.clientX - rect.left) / rect.width) * W,
      y: ((e.clientY - rect.top) / rect.height) * H,
      px: e.clientX - rect.left,
      py: e.clientY - rect.top,
    };
  }, []);

  const zoomBy = (factor: number, cx = W / 2, cy = H / 2) =>
    setView((v) => {
      const k = Math.min(8, Math.max(1, v.k * factor));
      const scale = k / v.k;
      return clampView(k, cx - scale * (cx - v.tx), cy - scale * (cy - v.ty));
    });

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const { x, y } = svgPoint(e);
    zoomBy(e.deltaY < 0 ? 1.25 : 0.8, x, y);
  };

  const onPointerDown = (e: React.PointerEvent) => {
    (e.target as Element).setPointerCapture?.(e.pointerId);
    drag.current = { x: e.clientX, y: e.clientY, tx: view.tx, ty: view.ty, moved: false };
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current) return;
    const el = wrapRef.current!;
    const rect = el.getBoundingClientRect();
    const dx = ((e.clientX - drag.current.x) / rect.width) * W;
    const dy = ((e.clientY - drag.current.y) / rect.height) * H;
    if (Math.abs(dx) + Math.abs(dy) > 3) drag.current.moved = true;
    if (drag.current.moved)
      setView((v) => clampView(v.k, drag.current!.tx + dx, drag.current!.ty + dy));
  };
  const onPointerUp = () => {
    // keep `moved` readable by click handlers that fire after pointerup
    setTimeout(() => (drag.current = null), 0);
  };
  const wasDrag = () => !!drag.current?.moved;

  const legendCounts = useMemo(() => {
    const m = new Map<string, number>();
    for (const d of disputes) m.set(d.status, (m.get(d.status) ?? 0) + 1);
    return m;
  }, [disputes]);

  return (
    <div className="border border-hairline bg-card">
      {/* legend + zoom controls */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3 border-b border-hairline">
        {STATUS_ORDER.map((s) => (
          <span key={s} className="flex items-center gap-1.5 text-xs text-ink-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: statusColor(s) }} />
            {STATUS_SHORT[s]}
            <span className="text-ink-3 tabular">{legendCounts.get(s) ?? 0}</span>
          </span>
        ))}
        <span className="text-xs text-ink-3 hidden sm:inline">dot size = patients affected</span>
        <span className="ml-auto flex items-center gap-1">
          <button
            className="w-7 h-7 border border-baseline rounded text-ink-2 hover:border-ink text-sm leading-none"
            onClick={() => zoomBy(1.4)}
            aria-label="Zoom in"
          >
            +
          </button>
          <button
            className="w-7 h-7 border border-baseline rounded text-ink-2 hover:border-ink text-sm leading-none"
            onClick={() => zoomBy(0.7)}
            aria-label="Zoom out"
          >
            −
          </button>
          <button
            className="h-7 px-2 border border-baseline rounded text-ink-2 hover:border-ink text-xs"
            onClick={() => setView({ k: 1, tx: 0, ty: 0 })}
          >
            Reset
          </button>
        </span>
      </div>

      <div
        ref={wrapRef}
        className="relative select-none touch-pan-y"
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={() => {
          onPointerUp();
          setHover(null);
        }}
      >
        <svg viewBox={`0 0 ${W} ${H}`} className="block w-full h-auto cursor-grab active:cursor-grabbing" role="img" aria-label="Map of U.S. payer–provider disputes">
          <g transform={`translate(${view.tx},${view.ty}) scale(${view.k})`}>
            {statesFeatures.map((f, i) => {
              const postal = STATE_NAME_TO_POSTAL[f.properties.name];
              const active = postal && activeStates.includes(postal);
              return (
                <path
                  key={i}
                  d={path(f as never) ?? undefined}
                  fill={active ? "#eee7d4" : "#f1efe8"}
                  className="cursor-pointer"
                  onClick={() => {
                    if (wasDrag() || !postal) return;
                    onToggleState(postal);
                  }}
                >
                  <title>{f.properties.name}</title>
                </path>
              );
            })}
            <path
              d={path(stateBorders as never) ?? undefined}
              fill="none"
              stroke="#d8d4c8"
              strokeWidth={1 / view.k}
            />
            {placed.map(({ d, x, y, r }) => (
              <circle
                key={d.id}
                cx={x}
                cy={y}
                r={r / Math.sqrt(view.k)}
                fill={statusColor(d.status)}
                fillOpacity={0.72}
                stroke="#fffefb"
                strokeWidth={1.5 / view.k}
                className="cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  if (wasDrag()) return;
                  onSelect(d);
                }}
                onMouseEnter={(e) => {
                  const { px, py } = svgPoint(e);
                  setHover({ d, cx: px, cy: py });
                }}
                onMouseMove={(e) => {
                  const { px, py } = svgPoint(e);
                  setHover({ d, cx: px, cy: py });
                }}
                onMouseLeave={() => setHover(null)}
              />
            ))}
          </g>
        </svg>

        {hover && (
          <div
            className="pointer-events-none absolute z-10 max-w-[260px] bg-ink text-paper text-xs rounded px-3 py-2 shadow-lg"
            style={{
              left: Math.min(hover.cx + 12, (wrapRef.current?.clientWidth ?? 600) - 270),
              top: hover.cy + 12,
            }}
          >
            <p className="font-semibold leading-snug">
              {hover.d.system} vs {hover.d.insurerShort ?? hover.d.insurer}
            </p>
            <p className="mt-1 opacity-80">
              {STATUS_SHORT[hover.d.status] ?? hover.d.status} · first reported{" "}
              {fmtDate(hover.d.firstDate)}
            </p>
            {hover.d.patients != null && (
              <p className="opacity-80">
                {fmtCompact(hover.d.patients)} patients
                {patientsIsEstimate(hover.d) ? " (est.)" : ""}
              </p>
            )}
            <p className="mt-1 opacity-60">Click for the full record</p>
          </div>
        )}

        {placed.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-ink-3">
            No disputes match the current filters.
          </div>
        )}
      </div>
    </div>
  );
}
