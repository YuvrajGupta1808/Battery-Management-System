import {
  ArrowRight,
  Battery,
  Bot,
  CircuitBoard,
  FileJson,
  Layers,
  Presentation,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

/** Public demo deck — problem, solution, Tigris/Opsera integration, live demo flow. */
export const DEMO_SLIDES_URL =
  "https://docs.google.com/presentation/d/1CKAFcLRS_bu9ad1yHA_NGsjL9XdnqZ1kjYYGaqD6e_8/edit?usp=sharing";

import { CanaryMark } from "../components/CanaryMark";
import { Button } from "../components/ui/button";

type LandingPageProps = {
  onOpenWorkbench: () => void;
};

const FEATURES = [
  {
    icon: Bot,
    title: "Agent-authored diagrams",
    description:
      "Describe your pack in plain language. The coding agent writes structured BMS architecture files — topology, ICs, pins, wires, and layout.",
  },
  {
    icon: CircuitBoard,
    title: "Interactive SVG schematics",
    description:
      "The workbench renders agent output as schematic blocks with pack and board drill-down, wire labels, and component inspection.",
  },
  {
    icon: ShieldCheck,
    title: "Safety rules you can inspect",
    description:
      "Thermal, OVP, UVP, and OCP logic live in versioned YAML. Select MCU or memory blocks to see linked protection rules.",
  },
  {
    icon: FileJson,
    title: "Schema-backed validation",
    description:
      "Invalid agent writes are rejected before they hit disk — with actionable errors so the agent can fix and retry.",
  },
] as const;

const STEPS = [
  {
    icon: Sparkles,
    title: "Describe the pack",
    description: "Tell CANary your cell count, topology, chemistry, and protection requirements.",
  },
  {
    icon: Layers,
    title: "Agent authors artifacts",
    description: "The agent creates bms/architecture.bms.json and bms/safety_rules.yaml in your workspace.",
  },
  {
    icon: Battery,
    title: "Review and iterate",
    description: "Inspect the diagram, edit source, and re-run the agent until the design is right.",
  },
] as const;

export function LandingPage({ onOpenWorkbench }: LandingPageProps) {
  return (
    <div className="landing-page">
      <div className="landing-grid-bg" aria-hidden="true" />

      <header className="landing-header">
        <div className="landing-brand">
          <CanaryMark size={36} className="landing-brand-mark" />
          <div>
            <strong>CANary</strong>
            <span>BMS Validation Workbench</span>
          </div>
        </div>
        <div className="landing-header-actions">
          <a
            className="landing-slides-link landing-slides-link--header"
            href={DEMO_SLIDES_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Presentation aria-hidden="true" />
            Demo slides
          </a>
          <Button className="landing-header-cta" onClick={onOpenWorkbench}>
            Open Workbench
            <ArrowRight />
          </Button>
        </div>
      </header>

      <main className="landing-main">
        <section className="landing-hero">
          <div className="landing-hero-mark" aria-hidden="true">
            <CanaryMark size={64} />
          </div>
          <p className="landing-eyebrow">Agentic BMS design & validation</p>
          <h1>
            Design battery management systems
            <span> in natural language</span>
          </h1>
          <p className="landing-lede">
            CANary helps engineers describe pack requirements conversationally. A coding agent authors circuit
            diagrams and safety rules as structured files; the UI renders them as interactive SVG schematics with
            drill-down and auditable artifacts.
          </p>
          <div className="landing-hero-actions">
            <Button size="default" className="landing-primary-cta" onClick={onOpenWorkbench}>
              Start in the workbench
              <ArrowRight />
            </Button>
            <a
              className="landing-slides-link landing-slides-link--hero"
              href={DEMO_SLIDES_URL}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Presentation aria-hidden="true" />
              View demo slides
            </a>
          </div>
          <p className="landing-slides-note">
            Problem statement, architecture, Tigris &amp; Opsera integration —{" "}
            <a href={DEMO_SLIDES_URL} target="_blank" rel="noopener noreferrer">
              open the deck
            </a>
          </p>
        </section>

        <section className="landing-section">
          <div className="landing-section-head">
            <h2>What CANary does</h2>
            <p>From requirements to validated BMS artifacts in one agentic loop.</p>
          </div>
          <div className="landing-feature-grid">
            {FEATURES.map(({ icon: Icon, title, description }) => (
              <article className="landing-feature-card" key={title}>
                <div className="landing-feature-icon">
                  <Icon />
                </div>
                <h3>{title}</h3>
                <p>{description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section landing-flow">
          <div className="landing-section-head">
            <h2>How it works</h2>
            <p>Three steps from prompt to inspectable BMS design.</p>
          </div>
          <ol className="landing-steps">
            {STEPS.map(({ icon: Icon, title, description }, index) => (
              <li className="landing-step" key={title}>
                <div className="landing-step-index">{index + 1}</div>
                <div className="landing-step-icon">
                  <Icon />
                </div>
                <div>
                  <h3>{title}</h3>
                  <p>{description}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="landing-artifacts">
          <div className="landing-artifacts-copy">
            <h2>Auditable workspace artifacts</h2>
            <p>
              Everything the agent produces lives under your workspace — schema-validated JSON for diagrams, YAML for
              safety logic, and SKILL guides for repeatable authoring.
            </p>
            <pre className="landing-artifact-tree">{`workspaces/default/bms/
├── architecture.bms.json   # topology, views, components
├── safety_rules.yaml       # thermal, OVP, UVP, OCP
├── schema/                 # JSON Schema contract
├── templates/              # agent starting points
└── SKILL.md                # diagram authoring guide`}</pre>
          </div>
          <div className="landing-artifacts-panel">
            <div className="landing-panel-tab">Diagram</div>
            <div className="landing-panel-preview">
              <div className="landing-preview-node pack">4S Cell Stack</div>
              <div className="landing-preview-wire" />
              <div className="landing-preview-node board">BMS Board</div>
              <div className="landing-preview-wire secondary" />
              <div className="landing-preview-node contactor">Contactor</div>
            </div>
            <p>Pack view with drill-down into MCU, AFE, CAN, and protection blocks.</p>
          </div>
        </section>

        <section className="landing-cta-band">
          <div>
            <h2>Ready to design your pack?</h2>
            <p>Open the workbench, pick a workspace, and ask the agent to author your first BMS diagram.</p>
          </div>
          <Button className="landing-primary-cta" onClick={onOpenWorkbench}>
            Open Workbench
            <ArrowRight />
          </Button>
        </section>
      </main>

      <footer className="landing-footer">
        <span>CANary — BMS Validation Workbench</span>
        <a className="landing-slides-link landing-slides-link--footer" href={DEMO_SLIDES_URL} target="_blank" rel="noopener noreferrer">
          <Presentation aria-hidden="true" />
          CANary demo slides (Google Slides)
        </a>
        <span>Agent-authored diagrams · Schema validation · Safety rule inspection</span>
      </footer>
    </div>
  );
}
