import type { BmsArchitecture, PackInfo, SchematicEdge, SchematicNode, SchematicView } from "./types";
import { NODE_ROLE_LABELS } from "./blockLabel";
import { parsePackTopology, resolveComponentPart, seriesCellPinLabel } from "./layout";

export type PackTopology = NonNullable<ReturnType<typeof parsePackTopology>>;

/** Cell-stack block size scales with series × parallel so 4S and 12S are visibly different. */
export function cellStackDimensions(series: number, parallel: number): { width: number; height: number } {
  return {
    width: Math.min(720, Math.max(140, 48 + series * 22)),
    height: Math.max(72, 56 + Math.max(0, parallel - 1) * 36),
  };
}

/** AFE monitor block grows with series count. */
export function afeBlockDimensions(series: number): { width: number; height: number } {
  return {
    width: Math.min(300, Math.max(170, 100 + series * 7)),
    height: Math.max(95, 80 + Math.floor(series / 4) * 10),
  };
}

function ensureBlockSize(node: SchematicNode, minWidth: number, minHeight: number): void {
  node.width = Math.max(node.width, minWidth);
  node.height = Math.max(node.height, minHeight);
}

function cloneNode(node: SchematicNode): SchematicNode {
  return {
    ...node,
    pins: node.pins?.map((p) => ({ ...p })),
    telemetry: node.telemetry ? { ...node.telemetry } : undefined,
  };
}

function cloneView(view: SchematicView): SchematicView {
  return {
    nodes: view.nodes.map(cloneNode),
    edges: view.edges.map((e) => ({ ...e })),
  };
}

function findNode(nodes: SchematicNode[], id: string): SchematicNode | undefined {
  return nodes.find((n) => n.id === id);
}

function findByType(nodes: SchematicNode[], type: string): SchematicNode | undefined {
  return nodes.find((n) => n.type === type);
}

function updatePinLabel(node: SchematicNode, prefix: RegExp, label: string): void {
  for (const pin of node.pins ?? []) {
    if (prefix.test(pin.label)) {
      pin.label = label;
    }
  }
}

function formatStackLabel(topology: PackTopology, pack: PackInfo): string {
  const topo = `${topology.series}S${topology.parallel > 1 ? `${topology.parallel}P` : ""}`;
  return `${topo} ${pack.chemistry} Stack`;
}

function shiftNodesRight(nodes: SchematicNode[], fromX: number, deltaX: number): void {
  if (deltaX <= 0) return;
  for (const node of nodes) {
    if (node.x >= fromX) {
      node.x += deltaX;
    }
  }
}

export function adaptPackView(view: SchematicView, pack: PackInfo, topology: PackTopology): SchematicView {
  const adapted = cloneView(view);
  const cells = findByType(adapted.nodes, "cells");
  if (!cells) return adapted;

  const prevWidth = cells.width;
  const dims = cellStackDimensions(topology.series, topology.parallel);
  cells.width = dims.width;
  cells.height = dims.height;
  cells.label = formatStackLabel(topology, pack);
  cells.y = Math.max(280, 460 - dims.height);

  const widthDelta = cells.width - prevWidth;
  if (widthDelta > 0) {
    shiftNodesRight(adapted.nodes, cells.x + prevWidth + 20, widthDelta);
  }

  const bmsBoard = findByType(adapted.nodes, "bms_board");
  if (bmsBoard) {
    const minGap = 44;
    bmsBoard.x = Math.max(bmsBoard.x, cells.x + cells.width + minGap);
  }

  const contactor = findByType(adapted.nodes, "contactor");
  if (contactor && bmsBoard) {
    contactor.x = Math.max(contactor.x, bmsBoard.x + bmsBoard.width + 36);
  }

  return adapted;
}

function injectSecondAfe(
  nodes: SchematicNode[],
  edges: SchematicEdge[],
  primary: SchematicNode,
  series: number,
  part: string | null,
): void {
  if (series <= 16 || nodes.some((n) => n.id === "cell_ic_2")) return;

  const secondSeries = series - 16;
  const startCell = 17;
  const endCell = startCell + secondSeries - 1;
  const cellLabel =
    secondSeries <= 1 ? `CELL_${startCell}` : `CELL_${startCell}-${endCell}`;

  const yOffset = primary.height + 36;
  nodes.push({
    id: "cell_ic_2",
    type: "cell_monitor_ic",
    label: part ? `${part} AFE (B)` : "Cell Monitor IC (B)",
    x: primary.x,
    y: primary.y + yOffset,
    width: afeBlockDimensions(secondSeries).width,
    height: afeBlockDimensions(secondSeries).height,
    component_ref: primary.component_ref ? `${primary.component_ref}_b` : undefined,
    telemetry: { cells_monitored: secondSeries },
    pins: [
      { id: "cell_sense", label: cellLabel, side: "left" },
      { id: "i2c_sda", label: "I2C_SDA", side: "top" },
      { id: "i2c_scl", label: "I2C_SCL", side: "top" },
      { id: "bal_out", label: "BAL_OUT", side: "right" },
    ],
  });

  const mcu = findByType(nodes, "mcu");
  if (mcu) {
    edges.push({
      from_node: mcu.id,
      from_pin: "i2c_sda",
      to_node: "cell_ic_2",
      to_pin: "i2c_sda",
      signal: "I2C_SDA",
    });
    edges.push({
      from_node: mcu.id,
      from_pin: "i2c_scl",
      to_node: "cell_ic_2",
      to_pin: "i2c_scl",
      signal: "I2C_SCL",
    });
  }
}

function enrichNodeLabel(
  node: SchematicNode,
  components?: Record<string, Record<string, unknown>>,
): void {
  const part = resolveComponentPart(node.component_ref, components);
  if (!part) return;
  if (/\s[–—-]\s/.test(node.label)) return;

  const role = NODE_ROLE_LABELS[node.type] ?? node.type.replace(/_/g, " ");
  if (node.type === "cells" || node.type === "bms_board" || node.type === "contactor") return;
  node.label = `${role} – ${part}`;
}

function resolvePartLabel(node: SchematicNode, components?: Record<string, Record<string, unknown>>): void {
  enrichNodeLabel(node, components);
}

export function adaptBmsView(
  view: SchematicView,
  pack: PackInfo,
  topology: PackTopology,
  components?: Record<string, Record<string, unknown>>,
): SchematicView {
  const adapted = cloneView(view);
  const { series } = topology;
  const cellLabel = seriesCellPinLabel(series);
  const ntcLabel = series <= 1 ? "NTC_1" : `NTC_1-${series}`;

  const cellIc = findByType(adapted.nodes, "cell_monitor_ic");
  if (cellIc) {
    const primarySeries = series > 16 ? 16 : series;
    const afeDims = afeBlockDimensions(primarySeries);
    cellIc.width = afeDims.width;
    cellIc.height = afeDims.height;
    updatePinLabel(cellIc, /^CELL_/i, seriesCellPinLabel(primarySeries));
    cellIc.telemetry = { ...cellIc.telemetry, cells_monitored: primarySeries };
    resolvePartLabel(cellIc, components);

    const part =
      cellIc.component_ref && components?.[cellIc.component_ref]?.part;
    const partStr = typeof part === "string" ? part : null;
    if (series > 16) {
      injectSecondAfe(adapted.nodes, adapted.edges, cellIc, series, partStr);
    } else {
      updatePinLabel(cellIc, /^CELL_/i, cellLabel);
      cellIc.telemetry = { ...cellIc.telemetry, cells_monitored: series };
    }
  }

  const tempNet = findByType(adapted.nodes, "temperature_network");
  if (tempNet) {
    updatePinLabel(tempNet, /^NTC_/i, ntcLabel);
    if (cellIc) {
      tempNet.y = Math.max(tempNet.y, cellIc.y + cellIc.height + 28);
    }
  }

  const balancing = findByType(adapted.nodes, "balancing");
  if (balancing && cellIc) {
    balancing.y = Math.max(balancing.y, cellIc.y + cellIc.height + 20);
  }

  const current = findByType(adapted.nodes, "current_sensor");
  const memory = findByType(adapted.nodes, "memory");
  if (current && memory) {
    const bottomY = Math.max(current.y, memory.y, 320);
    current.y = bottomY;
    memory.y = bottomY + current.height + 24;
    if (current.x >= memory.x - 40 && current.x <= memory.x + memory.width) {
      memory.x = current.x + current.width + 40;
    }
  }

  for (const node of adapted.nodes) {
    resolvePartLabel(node, components);
    if (node.type === "mcu") ensureBlockSize(node, 160, 100);
    if (node.type === "can_transceiver") ensureBlockSize(node, 150, 85);
    if (node.type === "current_sensor" || node.type === "memory") ensureBlockSize(node, 150, 88);
    if (node.type === "temperature_network" || node.type === "balancing") ensureBlockSize(node, 150, 85);
  }

  if (components?.temp_network?.sensor_count !== series) {
    // display-only hint via telemetry on temp node
    if (tempNet) {
      tempNet.telemetry = { ...tempNet.telemetry, sensor_count: series };
    }
  }

  return adapted;
}

/** Reshape schematic layout from pack topology (display + save normalization). */
export function adaptArchitectureForTopology(architecture: BmsArchitecture): BmsArchitecture {
  const topology = parsePackTopology(architecture.pack.topology);
  if (!topology) return architecture;

  return {
    ...architecture,
    views: {
      pack: adaptPackView(architecture.views.pack, architecture.pack, topology),
      bms: adaptBmsView(architecture.views.bms, architecture.pack, topology, architecture.components),
    },
  };
}
