import { useMemo, useState } from "react";

import { viewBounds } from "../../lib/bms/layout";
import type { BmsArchitecture, BmsViewId, SafetyRule, SchematicNode } from "../../lib/bms/types";
import { BmsBreadcrumb } from "./BmsBreadcrumb";
import { ComponentInspector } from "./ComponentInspector";
import { SchematicBlock } from "./SchematicBlock";
import { SchematicWire } from "./SchematicWire";

type BmsCircuitDiagramProps = {
  architecture: BmsArchitecture;
  safetyRules: SafetyRule[];
  /** Read-only preview for template files with banner overlay */
  mode?: "live" | "template-preview";
};

export function BmsCircuitDiagram({
  architecture,
  safetyRules,
  mode = "live",
}: BmsCircuitDiagramProps) {
  const [activeView, setActiveView] = useState<BmsViewId>("pack");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const packView = architecture.views?.pack;
  const bmsView = architecture.views?.bms;
  const view = activeView === "pack" ? packView : bmsView;
  const nodes = view?.nodes ?? [];
  const edges = view?.edges ?? [];
  const bounds = useMemo(() => viewBounds(nodes), [nodes]);
  const selectedNode: SchematicNode | null = nodes.find((n) => n.id === selectedNodeId) ?? null;
  const isPreview = mode === "template-preview";

  function handleDrill(node: SchematicNode) {
    if (isPreview) return;
    if (node.drill_view === "bms") {
      setActiveView("bms");
      setSelectedNodeId(null);
    }
  }

  function handleNavigate(viewId: BmsViewId) {
    setActiveView(viewId);
    setSelectedNodeId(null);
  }

  function handleSelect(nodeId: string) {
    if (isPreview) return;
    setSelectedNodeId(nodeId);
  }

  if (!view || !architecture.pack) {
    return (
      <div className="bms-diagram-error">
        BMS architecture is incomplete. Ensure <code>pack</code>, <code>views.pack</code>, and <code>views.bms</code>{" "}
        are defined, or ask the agent to regenerate the file.
      </div>
    );
  }

  return (
    <div className={`bms-diagram-shell${isPreview ? " bms-diagram-shell--preview" : ""}`}>
      {isPreview && (
        <div className="bms-preview-banner" role="status">
          <span className="bms-preview-banner-label">Reference template</span>
          <span className="bms-preview-banner-text">
            Preview only — the agent writes your design to <code>bms/architecture.bms.json</code>
          </span>
        </div>
      )}

      <header className="bms-diagram-header">
        <div className="bms-diagram-header-left">
          <BmsBreadcrumb
            activeView={activeView}
            selectedNodeLabel={selectedNode?.label}
            onNavigate={handleNavigate}
          />
          <div className="bms-view-switcher" role="tablist" aria-label="Schematic view">
            <button
              type="button"
              role="tab"
              aria-selected={activeView === "pack"}
              className={activeView === "pack" ? "bms-view-chip active" : "bms-view-chip"}
              onClick={() => handleNavigate("pack")}
            >
              Pack
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeView === "bms"}
              className={activeView === "bms" ? "bms-view-chip active" : "bms-view-chip"}
              onClick={() => handleNavigate("bms")}
            >
              BMS board
            </button>
          </div>
        </div>
        <div className="bms-diagram-meta">
          <span className="bms-meta-chip">{architecture.pack.topology}</span>
          <span className="bms-meta-chip">{architecture.pack.chemistry}</span>
          <span className="bms-meta-chip">{architecture.pack.cell_count} cells</span>
          <span className="bms-meta-chip">{architecture.pack.nominal_voltage_v} V</span>
        </div>
      </header>

      <div className="bms-diagram-body">
        <div className="bms-canvas-wrap">
          <div
            className="bms-canvas-frame"
            style={{ aspectRatio: `${bounds.width} / ${bounds.height}` }}
          >
            <svg
              className="bms-canvas"
              viewBox={`0 0 ${bounds.width} ${bounds.height}`}
              preserveAspectRatio="xMidYMid meet"
              onClick={() => !isPreview && setSelectedNodeId(null)}
            >
              <defs>
                <pattern id="bms-grid" width="20" height="20" patternUnits="userSpaceOnUse">
                  <path d="M 20 0 L 0 0 0 20" fill="none" className="bms-grid-line" />
                </pattern>
                <linearGradient id="bms-canvas-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#0f1419" />
                  <stop offset="100%" stopColor="#0a0e14" />
                </linearGradient>
                <filter id="bms-wire-glow">
                  <feGaussianBlur stdDeviation="1.2" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>
              <rect width={bounds.width} height={bounds.height} fill="url(#bms-canvas-gradient)" />
              <rect width={bounds.width} height={bounds.height} fill="url(#bms-grid)" opacity="0.65" />

              {edges.map((edge) => (
                <SchematicWire
                  key={`${edge.from_node}-${edge.from_pin}-${edge.to_node}-${edge.to_pin}`}
                  edge={edge}
                  nodes={nodes}
                />
              ))}

              {nodes.map((node) => (
                <SchematicBlock
                  key={node.id}
                  node={node}
                  selected={selectedNodeId === node.id}
                  onSelect={handleSelect}
                  onDrill={isPreview ? undefined : handleDrill}
                  readOnly={isPreview}
                  pack={architecture.pack}
                  components={architecture.components}
                />
              ))}
            </svg>
          </div>
          <div className="bms-canvas-legend">
            <span className="bms-legend-item">
              <span className="bms-legend-dot bms-legend-dot--signal" /> Signal
            </span>
            <span className="bms-legend-item">
              <span className="bms-legend-dot bms-legend-dot--drill" /> Drill-down
            </span>
            {!isPreview && (
              <span className="bms-legend-hint">Click BMS board to open internal schematic</span>
            )}
          </div>
        </div>

        <aside className="bms-inspector-pane">
          <ComponentInspector
            architecture={architecture}
            node={selectedNode}
            rules={safetyRules}
            preview={isPreview}
          />
        </aside>
      </div>
    </div>
  );
}
