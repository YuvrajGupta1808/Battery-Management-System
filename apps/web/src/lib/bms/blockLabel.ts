/** Layout helpers for schematic block text (keeps labels inside block bounds). */

const PADDING_X = 10;
const CHAR_WIDTH_TITLE = 6;
const CHAR_WIDTH_DETAIL = 5.2;

export type BlockDisplayLabel = {
  lines: string[];
  /** Full label for tooltips / inspector */
  full: string;
};

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
  const total =
    lineCount <= 1 ? titleSize : titleSize + gap + detailSize;
  if (opts?.topAligned) return 12;
  return Math.max(12, (blockHeight - total) / 2 + titleSize * 0.75);
}
