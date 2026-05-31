import {
  blockLabelStartY,
  formatSchematicBlockLabels,
  truncateLabel,
} from "../../lib/bms/blockLabel";
import type { PackInfo, SchematicNode } from "../../lib/bms/types";
import { parsePackTopology, pinPosition, resolveComponentPart } from "../../lib/bms/layout";
import { CellStackGraphic } from "./CellStackGraphic";

type SchematicBlockProps = {
  node: SchematicNode;
  selected: boolean;
  onSelect: (nodeId: string) => void;
  onDrill?: (node: SchematicNode) => void;
  readOnly?: boolean;
  pack?: PackInfo;
  components?: Record<string, Record<string, unknown>>;
};

function monitoredCellCount(node: SchematicNode): number | null {
  const fromTelemetry = node.telemetry?.cells_monitored;
  if (typeof fromTelemetry === "number" && fromTelemetry > 0) return fromTelemetry;
  const pin = node.pins?.find((p) => /^CELL_/i.test(p.label));
  if (!pin) return null;
  const range = pin.label.match(/CELL_1(?:-(\d+))?/i);
  if (!range) return null;
  return range[1] ? Number.parseInt(range[1], 10) : 1;
}

const PIN_LABEL_MAX = 12;

export function SchematicBlock({
  node,
  selected,
  onSelect,
  onDrill,
  readOnly,
  pack,
  components,
}: SchematicBlockProps) {
  const pins = node.pins ?? [];
  const canDrill = Boolean(node.drill_view) && !readOnly;
  const partNumber = resolveComponentPart(node.component_ref, components);
  const packTopology = pack ? parsePackTopology(pack.topology) : null;
  const showPackCells = node.type === "cells" && packTopology !== null;
  const monitored = node.type === "cell_monitor_ic" ? monitoredCellCount(node) : null;
  const showAfeCells = node.type === "cell_monitor_ic" && monitored !== null && monitored > 0;

  const componentMeta =
    node.component_ref && components?.[node.component_ref]
      ? components[node.component_ref]
      : undefined;

  const display = formatSchematicBlockLabels(node.type, node.label, node.width, {
    partNumber,
    componentMeta,
    maxLines: node.height >= 95 ? 3 : 2,
  });

  const labelStartY = blockLabelStartY(node.height, display.lines.length, {
    topAligned: showPackCells,
  });
  const clipId = `schematic-clip-${node.id}`;
  const shownText = display.lines.map((l) => l.text).join(" · ");
  const ariaLabel = shownText !== display.full ? display.full : node.label;

  return (
    <g
      className={`schematic-block${selected ? " selected" : ""}${canDrill ? " drillable" : ""}${readOnly ? " readonly" : ""}`}
      data-type={node.type}
      data-chemistry={pack?.chemistry?.toLowerCase()}
      aria-label={ariaLabel}
      transform={`translate(${node.x}, ${node.y})`}
      onClick={(e) => {
        e.stopPropagation();
        if (readOnly) return;
        if (canDrill && onDrill) {
          onDrill(node);
        } else {
          onSelect(node.id);
        }
      }}
      role={readOnly ? undefined : "button"}
      tabIndex={readOnly ? undefined : 0}
      onKeyDown={(e) => {
        if (readOnly) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (canDrill && onDrill) onDrill(node);
          else onSelect(node.id);
        }
      }}
    >
      <defs>
        <clipPath id={clipId}>
          <rect width={node.width} height={node.height} rx={2} />
        </clipPath>
      </defs>

      <rect className="schematic-block-body" width={node.width} height={node.height} rx={2} />

      {showPackCells && (
        <CellStackGraphic
          topology={packTopology}
          chemistry={pack?.chemistry}
          width={node.width}
          height={node.height}
        />
      )}

      {showAfeCells && (
        <text className="schematic-afe-cell-count" x={node.width - 6} y={node.height - 6} textAnchor="end">
          {monitored}S
        </text>
      )}

      <g clipPath={`url(#${clipId})`} className="schematic-block-text">
        <text
          className="schematic-block-label"
          x={node.width / 2}
          y={labelStartY}
          textAnchor="middle"
        >
          {display.lines.map((line, index) => (
            <tspan
              key={`${index}-${line.text}`}
              x={node.width / 2}
              dy={index === 0 ? 0 : 11}
              className={
                line.variant === "part"
                  ? "schematic-block-part"
                  : line.variant === "detail"
                    ? "schematic-block-sublabel"
                    : undefined
              }
            >
              {line.text}
            </tspan>
          ))}
        </text>
      </g>

      {pins.map((pin) => {
        const abs = pinPosition(node, pin);
        const rel = { x: abs.x - node.x, y: abs.y - node.y };
        const pinText = truncateLabel(pin.label, PIN_LABEL_MAX);
        const labelOffset =
          pin.side === "left"
            ? { x: -4, y: rel.y + 3, anchor: "end" as const }
            : pin.side === "right"
              ? { x: node.width + 4, y: rel.y + 3, anchor: "start" as const }
              : pin.side === "top"
                ? { x: rel.x, y: -4, anchor: "middle" as const }
                : { x: rel.x, y: node.height + 12, anchor: "middle" as const };

        return (
          <g key={pin.id} className="schematic-pin-group">
            <circle className="schematic-pin" cx={rel.x} cy={rel.y} r={2.5} />
            <text
              className="schematic-pin-label"
              x={labelOffset.x}
              y={labelOffset.y}
              textAnchor={labelOffset.anchor}
            >
              {pinText}
            </text>
          </g>
        );
      })}

      {canDrill && (
        <text className="schematic-drill-hint" x={node.width - 6} y={12} textAnchor="end">
          ▶
        </text>
      )}
    </g>
  );
}
