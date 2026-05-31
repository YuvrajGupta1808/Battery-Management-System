export type PinSide = "left" | "right" | "top" | "bottom";

export type SchematicPin = {
  id: string;
  label: string;
  side: PinSide;
};

export type SchematicNode = {
  id: string;
  type: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  pins?: SchematicPin[];
  drill_view?: "bms";
  component_ref?: string;
  telemetry?: Record<string, string | number>;
};

export type SchematicEdge = {
  from_node: string;
  from_pin: string;
  to_node: string;
  to_pin: string;
  signal: string;
};

export type SchematicView = {
  nodes: SchematicNode[];
  edges: SchematicEdge[];
};

export type PackInfo = {
  topology: string;
  cell_count: number;
  chemistry: string;
  nominal_voltage_v: number;
};

export type BmsArchitecture = {
  schema_version: string;
  pack: PackInfo;
  views: {
    pack: SchematicView;
    bms: SchematicView;
  };
  components?: Record<string, Record<string, unknown>>;
};

export type SafetyRule = {
  id: string;
  condition: string;
  action: string;
  component?: string;
  description?: string;
};

export type BmsViewId = "pack" | "bms";

export type PinPosition = {
  x: number;
  y: number;
};

export type NodePinMap = Record<string, Record<string, PinPosition>>;
