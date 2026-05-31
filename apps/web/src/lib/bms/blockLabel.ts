/** Layout helpers for schematic block text (keeps labels inside block bounds). */

const PADDING_X = 10;
const CHAR_WIDTH_TITLE = 6;
const CHAR_WIDTH_DETAIL = 5.2;

export type BlockDisplayLabel = {
  lines: string[];
  /** Full label for tooltips / inspector */
  full: string;
};

export type BlockLabelLine = {
  text: string;
  variant: "title" | "part" | "detail";
};

export type SchematicBlockLabel = {
  lines: BlockLabelLine[];
  full: string;
};

/** Human-readable block roles keyed by schematic node type. */
export const NODE_ROLE_LABELS: Record<string, string> = {
  mcu: "MCU",
  cell_monitor_ic: "Cell Monitor AFE",
  can_transceiver: "CAN Transceiver",
  temperature_network: "Temp Network",
  balancing: "Cell Balancing",
  current_sensor: "Current Monitor",
  memory: "EEPROM / Flash",
  bms_board: "BMS Board",
  contactor: "Main Contactor",
  cooling: "Thermal Management",
  cells: "Cell Stack",
  busbars: "Pack Busbars",
  load: "Load",
};

export function nodeRoleLabel(nodeType: string): string {
  return NODE_ROLE_LABELS[nodeType] ?? nodeType.replace(/_/g, " ");
}

export function charsPerLine(blockWidth: number, charWidth: number): number {
  return Math.max(6, Math.floor((blockWidth - PADDING_X * 2) / charWidth));
}

export function truncateLabel(text: string, maxChars: number): string {
  const trimmed = text.trim();
  if (trimmed.length <= maxChars) return trimmed;
  if (maxChars <= 1) return trimmed.slice(0, maxChars);
  return `${trimmed.slice(0, maxChars - 1).trimEnd()}…`;
}

/** Split agent-style labels: "Cell Monitor – BQ76952 (CELL_1–12)". */
export function parseLabelParts(label: string): { title: string; detail: string | null } {
  const dash = label.match(/\s+[–—-]\s+/);
  if (!dash) {
    return { title: label.trim(), detail: null };
  }
  const idx = label.indexOf(dash[0]);
  let title = label.slice(0, idx).trim();
  let detail = label.slice(idx + dash[0].length).trim();

  const paren = detail.match(/^([^(]+?)\s*(\([^)]*\))\s*$/);
  if (paren) {
    const main = paren[1].trim();
    const inside = paren[2].slice(1, -1).trim();
    detail = inside.length <= 20 ? `${main} · ${inside}` : main;
  }

  return { title: title || label.trim(), detail: detail || null };
}

function componentMetaDetail(
  nodeType: string,
  meta: Record<string, unknown> | undefined,
  partNumber: string | null,
): string | null {
  if (!meta) return null;
  if (nodeType === "balancing" && meta.mode) return String(meta.mode);
  if (nodeType === "mcu" && meta.role) return String(meta.role).replace(/_/g, " ");
  if (nodeType === "memory" && meta.role) return String(meta.role).replace(/_/g, " ");
  if (nodeType === "current_sensor" && meta.shunt_mohm != null) return `${meta.shunt_mohm} mΩ shunt`;
  if (nodeType === "cell_monitor_ic" && meta.cells_monitored != null) {
    return `${meta.cells_monitored}S monitored`;
  }
  if (nodeType === "temperature_network" && meta.sensor_count != null) {
    return `${meta.sensor_count} sensors`;
  }
  if (nodeType === "temperature_network" && meta.part && meta.part !== partNumber) {
    return String(meta.part);
  }
  return null;
}

/** Rich block label: functional role, part number, and optional metadata line. */
const GENERIC_BLOCK_LABELS = new Set([
  "MCU",
  "Cell Monitor IC",
  "CAN Transceiver",
  "Temp Network",
  "Balancing",
  "Current Sensor",
  "EEPROM / Flash",
  "Memory",
]);

export function formatSchematicBlockLabels(
  nodeType: string,
  label: string,
  blockWidth: number,
  options?: {
    partNumber?: string | null;
    componentMeta?: Record<string, unknown>;
    maxLines?: number;
  },
): SchematicBlockLabel {
  const maxLines = options?.maxLines ?? 3;
  const part = options?.partNumber?.trim() || null;
  const role = nodeRoleLabel(nodeType);
  const parsed = parseLabelParts(label);
  const metaDetail = componentMetaDetail(nodeType, options?.componentMeta, part);

  let title = role;
  let partLine = part;
  let detailLine = parsed.detail ?? metaDetail;

  if (nodeType === "cells" || nodeType === "bms_board" || nodeType === "contactor" || nodeType === "cooling") {
    title = parsed.title || label.trim() || role;
    if (part && !title.includes(part)) {
      partLine = part;
    } else {
      partLine = null;
    }
  } else if (parsed.detail && parsed.title !== role && !GENERIC_BLOCK_LABELS.has(parsed.title)) {
    title = parsed.title;
    partLine = parsed.detail.split(" · ")[0]?.trim() ?? part;
    const parenDetail = parsed.detail.includes(" · ") ? parsed.detail.split(" · ").slice(1).join(" · ") : null;
    detailLine = parenDetail ?? metaDetail;
  } else if (part) {
    if (parsed.title === part || label.trim() === part) {
      title = role;
      partLine = part;
    } else if (
      parsed.title &&
      parsed.title !== role &&
      !parsed.title.includes(part) &&
      !GENERIC_BLOCK_LABELS.has(parsed.title)
    ) {
      title = parsed.title;
      partLine = part;
    } else {
      title = role;
      partLine = part;
    }
  } else if (parsed.title && parsed.title !== role && !GENERIC_BLOCK_LABELS.has(parsed.title)) {
    title = parsed.title;
  }

  if (partLine && detailLine === partLine) detailLine = metaDetail;

  const lines: BlockLabelLine[] = [];
  lines.push({
    text: truncateLabel(title, charsPerLine(blockWidth, CHAR_WIDTH_TITLE)),
    variant: "title",
  });

  if (partLine && lines.length < maxLines) {
    lines.push({
      text: truncateLabel(partLine, charsPerLine(blockWidth, CHAR_WIDTH_DETAIL)),
      variant: "part",
    });
  }

  if (detailLine && lines.length < maxLines && detailLine !== partLine && detailLine !== title) {
    lines.push({
      text: truncateLabel(detailLine, charsPerLine(blockWidth, CHAR_WIDTH_DETAIL)),
      variant: "detail",
    });
  }

  const fullParts = [title, partLine, detailLine].filter(Boolean);
  return { lines, full: fullParts.join(" · ") };
}

export function formatBlockDisplayLabel(
  label: string,
  blockWidth: number,
  options?: { partNumber?: string | null; maxLines?: number },
): BlockDisplayLabel {
  const maxLines = options?.maxLines ?? 2;
  const { title, detail } = parseLabelParts(label);
  const part = options?.partNumber?.trim() || null;

  let secondary = detail;
  if (part) {
    if (!secondary) {
      secondary = part;
    } else if (!secondary.includes(part)) {
      secondary = `${secondary} · ${part}`;
    }
  }

  const lines: string[] = [];
  lines.push(truncateLabel(title, charsPerLine(blockWidth, CHAR_WIDTH_TITLE)));

  if (secondary && maxLines >= 2) {
    lines.push(truncateLabel(secondary, charsPerLine(blockWidth, CHAR_WIDTH_DETAIL)));
  }

  return { lines, full: label.trim() };
}

export function blockLabelStartY(
  blockHeight: number,
  lineCount: number,
  opts?: { topAligned?: boolean },
): number {
  const titleSize = 10;
  const detailSize = 9;
  const gap = 2;
  const total = lineCount <= 1 ? titleSize : titleSize + (lineCount - 1) * (detailSize + gap);
  if (opts?.topAligned) return 12;
  return Math.max(12, (blockHeight - total) / 2 + titleSize * 0.75);
}
