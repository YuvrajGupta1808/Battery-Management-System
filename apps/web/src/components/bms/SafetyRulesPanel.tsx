import type { SafetyRule } from "../../lib/bms/types";

type SafetyRulesPanelProps = {
  rules: SafetyRule[];
  title?: string;
  compact?: boolean;
};

export function SafetyRulesPanel({ rules, title = "Safety Rules", compact }: SafetyRulesPanelProps) {
  if (!rules.length) {
    return (
      <section className={`bms-safety-rules empty${compact ? " compact" : ""}`}>
        <h4>{title}</h4>
        <p>No safety rules linked. Ask the agent to create `bms/safety_rules.yaml`.</p>
      </section>
    );
  }

  return (
    <section className={`bms-safety-rules${compact ? " compact" : ""}`}>
      <h4>{title}</h4>
      <ul>
        {rules.map((rule) => (
          <li key={rule.id}>
            <div className="bms-rule-id">{rule.id}</div>
            <div className="bms-rule-condition">
              If <code>{rule.condition}</code>
            </div>
            <div className="bms-rule-action">
              → <code>{rule.action}</code>
            </div>
            {rule.description && <p className="bms-rule-desc">{rule.description}</p>}
          </li>
        ))}
      </ul>
    </section>
  );
}
