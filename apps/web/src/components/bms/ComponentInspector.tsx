import type { BmsArchitecture, SafetyRule, SchematicNode } from "../../lib/bms/types";
import { SafetyRulesPanel } from "./SafetyRulesPanel";

type ComponentInspectorProps = {
  architecture: BmsArchitecture;
  node: SchematicNode | null;
  rules: SafetyRule[];
  preview?: boolean;
};

export function ComponentInspector({ architecture, node, rules, preview }: ComponentInspectorProps) {
  if (!node) {
    return (
      <div className="bms-inspector empty">
        <div className="bms-inspector-hero">
          <p className="bms-inspector-eyebrow">Pack overview</p>
          <h3>{architecture.pack.topology.toUpperCase()} · {architecture.pack.chemistry}</h3>
          <p className="bms-inspector-lead">
            {preview
              ? "Reference schematic — describe your pack in the agent chat to generate a live architecture."
              : "Select a block in the schematic to inspect pins, parts, and linked safety rules."}
          </p>
        </div>
        <dl className="bms-pack-summary bms-pack-summary--cards">
          <div className="bms-summary-card">
            <dt>Topology</dt>
            <dd>{architecture.pack.topology}</dd>
          </div>
          <div className="bms-summary-card">
            <dt>Cells</dt>
            <dd>{architecture.pack.cell_count}</dd>
          </div>
          <div className="bms-summary-card">
            <dt>Chemistry</dt>
            <dd>{architecture.pack.chemistry}</dd>
          </div>
          <div className="bms-summary-card">
            <dt>Nominal V</dt>
            <dd>{architecture.pack.nominal_voltage_v} V</dd>
          </div>
        </dl>
        {rules.length > 0 && (
          <SafetyRulesPanel rules={rules} title="Protection rules" compact />
        )}
      </div>
    );
  }

  const componentMeta =
    node.component_ref && architecture.components ? architecture.components[node.component_ref] : undefined;

  const nodeRules = rules.filter(
    (r) => r.component === node.id || r.component === node.type || r.component === node.component_ref,
  );

  return (
    <div className="bms-inspector">
      <h3>{node.label}</h3>
      <p className="bms-inspector-type">{node.type.replace(/_/g, " ")}</p>

      {node.telemetry && Object.keys(node.telemetry).length > 0 && (
        <section>
          <h4>Telemetry</h4>
          <dl className="bms-kv">
            {Object.entries(node.telemetry).map(([key, val]) => (
              <div key={key} className="bms-kv-row">
                <dt>{key}</dt>
                <dd>{String(val)}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {componentMeta && (
        <section>
          <h4>Component</h4>
          <dl className="bms-kv">
            {Object.entries(componentMeta).map(([key, val]) => (
              <div key={key} className="bms-kv-row">
                <dt>{key}</dt>
                <dd>{String(val)}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {(node.type === "mcu" || node.type === "memory") && (
        <SafetyRulesPanel rules={nodeRules.length ? nodeRules : rules} title="Safety Rules" />
      )}
    </div>
  );
}
