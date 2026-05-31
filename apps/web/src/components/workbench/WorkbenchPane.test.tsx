import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { fireEvent, render, screen } from "@testing-library/react";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";

import { WorkbenchPane } from "./WorkbenchPane";

const fixtureDir = join(dirname(fileURLToPath(import.meta.url)), "../../lib/bms/__fixtures__");
const fixture = readFileSync(join(fixtureDir, "architecture.bms.json"), "utf-8");

describe("WorkbenchPane", () => {
  const baseProps = {
    selectedPath: "",
    fileContent: "",
    savedContent: "",
    editorLanguage: "markdown",
    editorSize: { width: 800, height: 600 },
    sessionCwd: "/workspaces/default",
    isSaving: false,
    saveLabel: "Save",
    hasUnsavedChanges: false,
    editorAreaRef: createRef<HTMLDivElement>(),
    safetyRulesContent: "",
    onContentChange: vi.fn(),
    onSave: vi.fn(),
  };

  it("shows diagram and source tabs for .bms.json files", () => {
    render(
      <WorkbenchPane
        {...baseProps}
        selectedPath="bms/architecture.bms.json"
        fileContent={fixture}
      />,
    );
    expect(screen.getByRole("button", { name: "Diagram" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Source" })).toBeInTheDocument();
  });

  it("renders diagram by default for bms files", () => {
    render(
      <WorkbenchPane
        {...baseProps}
        selectedPath="bms/architecture.bms.json"
        fileContent={fixture}
      />,
    );
    expect(screen.getByText("BMS Board")).toBeInTheDocument();
  });

  it("previews template files on diagram tab", () => {
    render(
      <WorkbenchPane
        {...baseProps}
        selectedPath="bms/templates/architecture.template.bms.json"
        fileContent={fixture}
      />,
    );
    expect(screen.getByText("Reference template")).toBeInTheDocument();
    expect(screen.getByText("BMS Board")).toBeInTheDocument();
  });

  it("shows error for invalid bms json on diagram tab", () => {
    render(
      <WorkbenchPane
        {...baseProps}
        selectedPath="bms/architecture.bms.json"
        fileContent="{invalid"
      />,
    );
    expect(screen.getByText(/JSON does not match the BMS schema/)).toBeInTheDocument();
  });

  it("does not show diagram tabs for regular files", () => {
    render(
      <WorkbenchPane
        {...baseProps}
        selectedPath="README.md"
        fileContent="# Hello"
      />,
    );
    expect(screen.queryByRole("button", { name: "Diagram" })).not.toBeInTheDocument();
  });

  it("calls onSave when save clicked with changes", () => {
    const onSave = vi.fn();
    render(
      <WorkbenchPane
        {...baseProps}
        selectedPath="README.md"
        fileContent="# changed"
        hasUnsavedChanges
        onSave={onSave}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalled();
  });
});
