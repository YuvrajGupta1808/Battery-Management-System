import Editor from "@monaco-editor/react";
import { FilePlus2, Save } from "lucide-react";
import { useMemo, useState } from "react";

import { isBmsDiagramFile, parseArchitecturePreview, parseSafetyRules, resolveDiagramState } from "../../lib/bms/layout";
import { BmsCircuitDiagram } from "../bms/BmsCircuitDiagram";
import { BmsDiagramPlaceholder } from "../bms/BmsDiagramPlaceholder";
import { Button } from "../ui/button";

type WorkbenchTab = "diagram" | "source";

type WorkbenchPaneProps = {
  selectedPath: string;
  fileContent: string;
  savedContent: string;
  editorLanguage: string;
  editorSize: { width: number; height: number };
  sessionCwd?: string;
  isSaving: boolean;
  saveLabel: string;
  hasUnsavedChanges: boolean;
  editorAreaRef: React.RefObject<HTMLDivElement | null>;
  safetyRulesContent: string;
  onContentChange: (value: string) => void;
  onSave: () => void;
};

export function WorkbenchPane({
  selectedPath,
  fileContent,
  editorLanguage,
  editorSize,
  sessionCwd,
  isSaving,
  saveLabel,
  hasUnsavedChanges,
  editorAreaRef,
  safetyRulesContent,
  onContentChange,
  onSave,
}: WorkbenchPaneProps) {
  const isBmsFile = isBmsDiagramFile(selectedPath);
  const [tab, setTab] = useState<WorkbenchTab>("diagram");

  const diagramState = useMemo(
    () => (isBmsFile ? resolveDiagramState(selectedPath, fileContent) : null),
    [isBmsFile, selectedPath, fileContent],
  );
  const templatePreview = useMemo(
    () => (diagramState?.kind === "template" ? parseArchitecturePreview(fileContent) : null),
    [diagramState?.kind, fileContent],
  );
  const safetyRules = useMemo(() => parseSafetyRules(safetyRulesContent), [safetyRulesContent]);

  const activeTab = isBmsFile ? tab : "source";

  return (
    <section className="workbench-pane">
      <header className="editor-tabbar">
        <button className="tab active" type="button">
          <FilePlus2 />
          {selectedPath || "untitled"}
        </button>
        {isBmsFile && (
          <div className="workbench-view-tabs">
            <button
              type="button"
              className={activeTab === "diagram" ? "workbench-view-tab active" : "workbench-view-tab"}
              onClick={() => setTab("diagram")}
            >
              Diagram
            </button>
            <button
              type="button"
              className={activeTab === "source" ? "workbench-view-tab active" : "workbench-view-tab"}
              onClick={() => setTab("source")}
            >
              Source
            </button>
          </div>
        )}
        <div className="editor-actions">
          <span>{sessionCwd ?? "No workspace"}</span>
          <Button
            disabled={!selectedPath || !hasUnsavedChanges || isSaving}
            variant="ghost"
            size="sm"
            onClick={onSave}
            title={saveLabel}
          >
            <Save data-icon="inline-start" />
            {saveLabel}
          </Button>
        </div>
      </header>

      <section className="editor-area" ref={editorAreaRef}>
        {isBmsFile && activeTab === "diagram" ? (
          diagramState?.kind === "ready" ? (
            <BmsCircuitDiagram architecture={diagramState.architecture} safetyRules={safetyRules} />
          ) : diagramState?.kind === "template" && templatePreview ? (
            <BmsCircuitDiagram
              architecture={templatePreview}
              safetyRules={safetyRules}
              mode="template-preview"
            />
          ) : diagramState ? (
            <BmsDiagramPlaceholder
              state={diagramState}
              selectedPath={selectedPath}
              onShowSource={() => setTab("source")}
            />
          ) : (
            <div className="bms-diagram-error">
              Invalid BMS architecture JSON. Switch to Source tab to fix, or ask the agent to regenerate the file.
            </div>
          )
        ) : (
          <Editor
            height={editorSize.height || "100%"}
            width={editorSize.width || "100%"}
            language={editorLanguage}
            theme="vs-dark"
            value={fileContent}
            onChange={(value) => onContentChange(value ?? "")}
            wrapperProps={{ className: "editor-surface" }}
            options={{
              automaticLayout: true,
              fontFamily: "JetBrains Mono, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
              fontSize: 13,
              lineHeight: 21,
              minimap: { enabled: false },
              renderLineHighlight: "line",
              scrollBeyondLastLine: false,
              wordWrap: "on",
            }}
          />
        )}
      </section>
    </section>
  );
}
