import type { BmsDiagramState } from "../../lib/bms/layout";

type BmsDiagramPlaceholderProps = {
  state: Exclude<BmsDiagramState, { kind: "ready" }>;
  selectedPath: string;
  onShowSource?: () => void;
};

export function BmsDiagramPlaceholder({ state, selectedPath, onShowSource }: BmsDiagramPlaceholderProps) {
  if (state.kind === "template") {
    return (
      <div className="bms-placeholder">
        <div className="bms-placeholder-visual" aria-hidden="true">
          <svg viewBox="0 0 320 180" className="bms-placeholder-svg">
            <rect width="320" height="180" rx="8" className="bms-placeholder-svg-bg" />
            <rect x="24" y="110" width="72" height="36" rx="3" className="bms-placeholder-block bms-placeholder-block--cells" />
            <rect x="120" y="88" width="64" height="48" rx="3" className="bms-placeholder-block bms-placeholder-block--bms" />
            <rect x="220" y="100" width="48" height="32" rx="3" className="bms-placeholder-block" />
            <path d="M96 128 L120 112 M184 112 L220 116" className="bms-placeholder-wire" />
          </svg>
        </div>
        <div className="bms-placeholder-content">
          <div className="bms-placeholder-badge">Template unavailable</div>
          <h2>Could not preview this template</h2>
          <p>
            <code>{selectedPath}</code> should contain a complete reference diagram. Open the{" "}
            <strong>Source</strong> tab to inspect the JSON, or ask the agent to regenerate workspace seed files.
          </p>
        </div>
      </div>
    );
  }

  if (state.kind === "invalid") {
    return (
      <div className="bms-placeholder bms-placeholder-error">
        <div className="bms-placeholder-content">
          <div className="bms-placeholder-badge">Invalid architecture</div>
          <h2>JSON does not match the BMS schema</h2>
          <p>
            <code>{selectedPath}</code> is missing <code>pack</code>, <code>views.pack</code>, or{" "}
            <code>views.bms</code>, or contains broken structure.
          </p>
          {onShowSource && (
            <button type="button" className="bms-placeholder-action" onClick={onShowSource}>
              Open Source tab
            </button>
          )}
          <p className="bms-placeholder-hint">Ask the agent to fix validation errors and rewrite the file.</p>
        </div>
      </div>
    );
  }

  const isPrimary = selectedPath.replace(/\\/g, "/").toLowerCase().endsWith("bms/architecture.bms.json");
  return (
    <div className="bms-placeholder">
      <div className="bms-placeholder-visual" aria-hidden="true">
        <svg viewBox="0 0 320 180" className="bms-placeholder-svg">
          <rect width="320" height="180" rx="8" className="bms-placeholder-svg-bg" />
          <circle cx="160" cy="90" r="28" className="bms-placeholder-pulse" />
        </svg>
      </div>
      <div className="bms-placeholder-content">
        <div className="bms-placeholder-badge">{isPrimary ? "Empty schematic" : "No nodes"}</div>
        <h2>{isPrimary ? "Architecture file has no diagram nodes yet" : "This view has no components"}</h2>
        <p>
          Pack metadata is set ({state.architecture.pack.topology}, {state.architecture.pack.chemistry},{" "}
          {state.architecture.pack.cell_count} cells) but <code>views.*.nodes</code> are empty.
        </p>
        <p className="bms-placeholder-hint">
          Describe your BMS in the agent chat — topology, ICs, and protection limits — and CANary will populate this
          schematic automatically.
        </p>
      </div>
    </div>
  );
}
