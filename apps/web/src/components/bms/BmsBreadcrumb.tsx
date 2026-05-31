import type { BmsViewId } from "../../lib/bms/types";

type BmsBreadcrumbProps = {
  activeView: BmsViewId;
  selectedNodeLabel?: string;
  onNavigate: (view: BmsViewId) => void;
};

const LABELS: Record<BmsViewId, string> = {
  pack: "Pack",
  bms: "BMS",
};

export function BmsBreadcrumb({ activeView, selectedNodeLabel, onNavigate }: BmsBreadcrumbProps) {
  return (
    <nav className="bms-breadcrumb" aria-label="Diagram navigation">
      <button type="button" className={activeView === "pack" && !selectedNodeLabel ? "active" : ""} onClick={() => onNavigate("pack")}>
        Pack
      </button>
      {activeView === "bms" || selectedNodeLabel ? (
        <>
          <span className="bms-breadcrumb-sep">›</span>
          <button type="button" className={activeView === "bms" && !selectedNodeLabel ? "active" : ""} onClick={() => onNavigate("bms")}>
            BMS
          </button>
        </>
      ) : null}
      {selectedNodeLabel ? (
        <>
          <span className="bms-breadcrumb-sep">›</span>
          <span className="bms-breadcrumb-current">{selectedNodeLabel}</span>
        </>
      ) : null}
    </nav>
  );
}
