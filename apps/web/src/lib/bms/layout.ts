import type { BmsArchitecture, PinPosition, PinSide, SchematicNode, SchematicPin } from "./types";

export function isRenderableArchitecture(value: unknown): value is BmsArchitecture {
  if (!value || typeof value !== "object") return false;
  const arch = value as BmsArchitecture;
  return Boolean(
    arch.pack &&
      typeof arch.pack.topology === "string" &&
      arch.views?.pack?.nodes &&
      Array.isArray(arch.views.pack.nodes) &&
      arch.views?.bms?.nodes &&
      Array.isArray(arch.views.bms.nodes) &&
      arch.views.pack.edges &&
      Array.isArray(arch.views.pack.edges) &&
      arch.views.bms.edges &&
      Array.isArray(arch.views.bms.edges),
  );
}

export function parseArchitecture(content: string): BmsArchitecture | null {
  try {
    const parsed: unknown = JSON.parse(content);
    return isRenderableArchitecture(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

/** Strip agent-only fields and parse template JSON for diagram preview. */
export function parseArchitecturePreview(content: string): BmsArchitecture | null {
  try {
    const parsed = JSON.parse(content) as Record<string, unknown>;
    if (parsed && typeof parsed === "object") {
      delete parsed.template_meta;
    }
    return isRenderableArchitecture(parsed) ? (parsed as BmsArchitecture) : null;
  } catch {
    return null;
  }
}

export function parseSafetyRules(content: string): import("./types").SafetyRule[] {
  const rules: import("./types").SafetyRule[] = [];
  let current: Partial<import("./types").SafetyRule> | null = null;

  for (const raw of content.split("\n")) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    if (line.startsWith("- ")) {
      if (current?.id && current.condition && current.action) {
        rules.push(current as import("./types").SafetyRule);
      }
      current = {};
      const rest = line.slice(2).trim();
      if (rest.includes(":")) {
        const [key, ...valParts] = rest.split(":");
        const val = valParts.join(":").trim().replace(/^["']|["']$/g, "");
        (current as Record<string, string>)[key.trim()] = val;
      }
      continue;
    }
    if (current && line.includes(":")) {
      const [key, ...valParts] = line.split(":");
      const val = valParts.join(":").trim().replace(/^["']|["']$/g, "");
      (current as Record<string, string>)[key.trim()] = val;
    }
  }

  if (current?.id && current.condition && current.action) {
    rules.push(current as import("./types").SafetyRule);
  }
  return rules;
}

export function pinPosition(node: SchematicNode, pin: SchematicPin): PinPosition {
  const pins = node.pins ?? [];
  const sameSide = pins.filter((p) => p.side === pin.side);
  const index = Math.max(0, sameSide.findIndex((p) => p.id === pin.id));
  const count = Math.max(1, sameSide.length);

  switch (pin.side) {
    case "left": {
      const span = node.height - 24;
      const y = node.y + 12 + (span * (index + 1)) / (count + 1);
      return { x: node.x, y };
    }
    case "right": {
      const span = node.height - 24;
      const y = node.y + 12 + (span * (index + 1)) / (count + 1);
      return { x: node.x + node.width, y };
    }
    case "top": {
      const span = node.width - 24;
      const x = node.x + 12 + (span * (index + 1)) / (count + 1);
      return { x, y: node.y };
    }
    case "bottom": {
      const span = node.width - 24;
      const x = node.x + 12 + (span * (index + 1)) / (count + 1);
      return { x, y: node.y + node.height };
    }
  }
}

export function manhattanPath(from: PinPosition, to: PinPosition, fromSide: PinSide, toSide: PinSide): string {
  const exit = offsetFromPin(from, fromSide, 16);
  const entry = offsetFromPin(to, toSide, 16);
  const midX = (exit.x + entry.x) / 2;
  return `M ${from.x} ${from.y} L ${exit.x} ${exit.y} L ${midX} ${exit.y} L ${midX} ${entry.y} L ${entry.x} ${entry.y} L ${to.x} ${to.y}`;
}

function offsetFromPin(pos: PinPosition, side: PinSide, amount: number): PinPosition {
  switch (side) {
    case "left":
      return { x: pos.x - amount, y: pos.y };
    case "right":
      return { x: pos.x + amount, y: pos.y };
    case "top":
      return { x: pos.x, y: pos.y - amount };
    case "bottom":
      return { x: pos.x, y: pos.y + amount };
  }
}

export function viewBounds(nodes: SchematicNode[], padding = 40): { width: number; height: number } {
  if (!nodes.length) return { width: 800, height: 480 };
  let maxX = 0;
  let maxY = 0;
  for (const node of nodes) {
    maxX = Math.max(maxX, node.x + node.width);
    maxY = Math.max(maxY, node.y + node.height);
  }
  return { width: maxX + padding, height: maxY + padding };
}

export function isBmsTemplatePath(path: string): boolean {
  return path.replace(/\\/g, "/").toLowerCase().includes("/templates/");
}

export function isPrimaryArchitecturePath(path: string): boolean {
  const norm = path.replace(/\\/g, "/").toLowerCase().replace(/^\/+/, "");
  return norm === "bms/architecture.bms.json";
}

export function isBmsDiagramCandidatePath(path: string): boolean {
  const norm = path.replace(/\\/g, "/").toLowerCase();
  return norm.includes(".bms.json") && !isBmsTemplatePath(path);
}

export function isBmsDiagramFile(path: string): boolean {
  const norm = path.replace(/\\/g, "/").toLowerCase();
  return norm.includes(".bms.json");
}

export function isBmsArchitecturePath(path: string): boolean {
  return isBmsDiagramCandidatePath(path);
}

export type BmsDiagramState =
  | { kind: "template" }
  | { kind: "invalid" }
  | { kind: "empty"; architecture: BmsArchitecture; path: string }
  | { kind: "ready"; architecture: BmsArchitecture };

export function resolveDiagramState(path: string, content: string): BmsDiagramState {
  if (isBmsTemplatePath(path)) {
    return { kind: "template" };
  }
  const architecture = parseArchitecture(content);
  if (!architecture) {
    return { kind: "invalid" };
  }
  const hasNodes = architecture.views.pack.nodes.length > 0 || architecture.views.bms.nodes.length > 0;
  if (!hasNodes) {
    return { kind: "empty", architecture, path };
  }
  return { kind: "ready", architecture };
}

export function nodeShowsRules(node: SchematicNode): boolean {
  return node.type === "mcu" || node.type === "memory";
}

export type PackTopology = {
  series: number;
  parallel: number;
};

/** Parse pack topology strings like `4s1p`, `12S2P`. */
export function parsePackTopology(topology: string): PackTopology | null {
  const match = topology.trim().match(/^(\d+)s(\d+)p$/i);
  if (!match) return null;
  return { series: Number.parseInt(match[1], 10), parallel: Number.parseInt(match[2], 10) };
}

export function seriesCellPinLabel(series: number): string {
  return series <= 1 ? "CELL_1" : `CELL_1-${series}`;
}

export function resolveComponentPart(
  componentRef: string | undefined,
  components: Record<string, Record<string, unknown>> | undefined,
): string | null {
  if (!componentRef || !components?.[componentRef]) return null;
  const part = components[componentRef].part;
  return typeof part === "string" && part.trim() ? part : null;
}
