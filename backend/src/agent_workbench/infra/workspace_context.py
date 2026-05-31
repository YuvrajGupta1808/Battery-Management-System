"""Helpers for describing the active workspace to agents."""

from __future__ import annotations

from pathlib import Path

IGNORED_NAMES = {".git", "node_modules", "dist", "coverage", ".data", ".venv", "venv", "__pycache__"}


def list_workspace_files(root: Path, *, limit: int = 200) -> list[str]:
    """Return workspace-relative file paths for agent context."""
    root = root.resolve()
    if not root.is_dir():
        return []

    paths: list[str] = []
    for path in sorted(root.rglob("*")):
        if any(part in IGNORED_NAMES for part in path.parts):
            continue
        if path.is_file():
            paths.append(path.relative_to(root).as_posix())
        if len(paths) >= limit:
            break
    return paths


def build_workspace_context_message(root: Path) -> str:
    """System context injected at the start of each agent run."""
    files = list_workspace_files(root)
    root_posix = root.resolve().as_posix()
    if files:
        listing = "\n".join(f"- /{path}" for path in files)
        inventory = f"Workspace files ({len(files)}):\n{listing}"
    else:
        inventory = "Workspace files: none yet."

    bms_hint = ""
    if (root / "bms" / "SKILL.md").is_file():
        bms_hint = (
            "\n\nCANary BMS: the agent system prompt defines the full design workflow. "
            "User messages are requirements only (topology, parts, thresholds)."
        )

    return (
        f"Active workspace: {root_posix}\n"
        f"{inventory}\n\n"
        "This workspace is the entire project scope for this session.\n"
        "- Do not list, read, grep, or glob outside this workspace.\n"
        "- There is no separate repository service or parent project to inspect.\n"
        "- For README tasks, edit `/README.md` in this workspace after at most one listing/read pass.\n"
        "- If no BMS source code exists yet, write product documentation directly in `/README.md`."
        f"{bms_hint}"
    )
