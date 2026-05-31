import { manhattanPath, pinPosition } from "../../lib/bms/layout";
import type { SchematicEdge, SchematicNode } from "../../lib/bms/types";

type SchematicWireProps = {
  edge: SchematicEdge;
  nodes: SchematicNode[];
};

export function SchematicWire({ edge, nodes }: SchematicWireProps) {
  const fromNode = nodes.find((n) => n.id === edge.from_node);
  const toNode = nodes.find((n) => n.id === edge.to_node);
  if (!fromNode || !toNode) return null;

  const fromPin = fromNode.pins?.find((p) => p.id === edge.from_pin);
  const toPin = toNode.pins?.find((p) => p.id === edge.to_pin);
  if (!fromPin || !toPin) return null;

  const from = pinPosition(fromNode, fromPin);
  const to = pinPosition(toNode, toPin);
  const d = manhattanPath(from, to, fromPin.side, toPin.side);
  const midX = (from.x + to.x) / 2;
  const midY = (from.y + to.y) / 2;

  return (
    <g className="schematic-wire-group">
      <path className="schematic-wire schematic-wire-glow" d={d} fill="none" filter="url(#bms-wire-glow)" />
      <path className="schematic-wire" d={d} fill="none" />
      <text className="schematic-wire-label" x={midX} y={midY - 4} textAnchor="middle">
        {edge.signal}
      </text>
    </g>
  );
}
