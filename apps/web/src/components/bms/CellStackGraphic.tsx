import type { PackTopology } from "../../lib/bms/layout";

type CellStackGraphicProps = {
  topology: PackTopology;
  chemistry?: string;
  width: number;
  height: number;
};

const CHEMISTRY_TINT: Record<string, string> = {
  NMC: "#f59e0b",
  LFP: "#22c55e",
};

export function CellStackGraphic({ topology, chemistry, width, height }: CellStackGraphicProps) {
  const { series, parallel } = topology;
  const tint = CHEMISTRY_TINT[chemistry?.toUpperCase() ?? ""] ?? "#64748b";
  const labelReserve = 26;
  const padX = 10;
  const padY = 8;
  const gap = 2;
  const stringGap = parallel > 1 ? 6 : 0;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2 - labelReserve;
  const stringH = parallel > 1 ? (innerH - stringGap * (parallel - 1)) / parallel : innerH;
  const cellW = Math.max(4, Math.min(16, (innerW - gap * (series - 1)) / series));
  const cellH = Math.max(8, Math.min(18, stringH - 4));
  const rowW = series * cellW + gap * (series - 1);
  const startX = (width - rowW) / 2;

  return (
    <g className="schematic-cell-stack" aria-hidden="true">
      {Array.from({ length: parallel }, (_, p) => {
        const rowY = padY + p * (stringH + stringGap) + (stringH - cellH) / 2;
        return (
          <g key={`string-${p}`}>
            {parallel > 1 && (
              <text className="schematic-cell-string-label" x={padX} y={rowY + cellH / 2 + 4}>
                P{p + 1}
              </text>
            )}
            {Array.from({ length: series }, (_, s) => (
              <rect
                key={`cell-${p}-${s}`}
                className="schematic-cell-unit"
                x={startX + s * (cellW + gap)}
                y={rowY}
                width={cellW}
                height={cellH}
                rx={1}
                fill={tint}
                fillOpacity={0.35}
                stroke={tint}
                strokeWidth={1}
              />
            ))}
          </g>
        );
      })}
      <text className="schematic-cell-topology-label" x={width / 2} y={height - 8} textAnchor="middle">
        {topology.series}S{topology.parallel > 1 ? `${topology.parallel}P` : ""}
      </text>
    </g>
  );
}
