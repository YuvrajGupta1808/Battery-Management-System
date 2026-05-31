"""List Opsera MCP tools and run minimal smoke probes (phase 1 / first pass only)."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

from agent_workbench.infra.opsera_mcp import (
    create_opsera_mcp_client,
    get_opsera_settings,
    resolve_opsera_scan_root,
)


def _text(result: Any, limit: int = 1200) -> str:
    if isinstance(result, tuple) and result:
        result = result[0]
    if isinstance(result, str):
        text = result
    elif isinstance(result, list):
        parts: list[str] = []
        for block in result:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        text = "\n".join(parts) if parts else str(result)
    else:
        text = str(result)
    text = text.strip()
    if len(text) > limit:
        return text[:limit] + f"\n... [{len(text) - limit} chars truncated]"
    return text


def _headline(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if stripped:
            return stripped[:120]
    return "(empty response)"


async def _list_tools(settings) -> list[Any]:
    client = create_opsera_mcp_client(settings)
    return await client.get_tools()


def _probe_args(tool_name: str, repo: Path, workspace: Path) -> dict[str, Any] | None:
    repo_s = str(repo)
    workspace_s = str(workspace)
    probes: dict[str, dict[str, Any]] = {
        "security-scan": {
            "phase": 1,
            "path": repo_s,
            "scan_type": "full",
            "severity_threshold": "high",
            "user_confirmed": True,
        },
        "architecture-analyze": {
            "repositories": repo_s,
            "project_name": "CANary",
            "report_format": "Markdown",
        },
        "compliance-audit": {
            "framework": "soc2",
            "scope": "full",
            "evidence_collection": "hybrid",
            "output_format": "detailed",
            "include_remediation": True,
        },
        "business-docs-generate": {
            "repositories": repo_s,
            "project_name": "CANary",
            "document_types": "Functional Requirements Document",
            "output_format": "Markdown",
        },
        "dora-metrics": {
            "repository_path": repo_s,
            "period_days": 30,
            "output_format": "summary",
            "include_pr_metrics": False,
            "include_pipeline_metrics": False,
        },
        "sql-security": {
            "action": "scan",
            "sql_file": repo_s,
            "severity_threshold": "high",
        },
        "opsera_report_telemetry": {
            "toolName": "opsera_probe",
            "status": "success",
            "total": 0,
            "target": "CANary/Battery-Management-System",
            "targetType": "repository",
        },
    }
    return probes.get(tool_name)


async def _probe_tool(tool: Any, repo: Path, workspace: Path) -> dict[str, Any]:
    name = getattr(tool, "name", "?")
    args = _probe_args(name, repo, workspace)
    if args is None:
        return {
            "tool": name,
            "status": "skipped",
            "reason": "no safe default probe (e.g. vibe-shift needs AWS cluster/region)",
        }
    try:
        coroutine = getattr(tool, "coroutine", None)
        if coroutine is None:
            return {"tool": name, "status": "error", "reason": "tool has no async coroutine"}
        result = await coroutine(**args)
        text = _text(result)
        return {
            "tool": name,
            "status": "ok",
            "headline": _headline(text),
            "preview": text,
            "args": args,
        }
    except Exception as exc:
        return {"tool": name, "status": "error", "reason": str(exc), "args": args}


async def run_probes(*, workspace: Path, probe: bool, json_out: bool) -> int:
    settings = get_opsera_settings(workspace_cwd=workspace)
    repo = settings.scan_root or resolve_opsera_scan_root(workspace)

    if not settings.configured:
        print("Opsera MCP not authenticated. Run: make opsera-login", file=sys.stderr)
        return 1

    tools = await _list_tools(settings)
    catalog = []
    for tool in sorted(tools, key=lambda t: getattr(t, "name", "")):
        name = getattr(tool, "name", "?")
        desc = getattr(tool, "description", "") or ""
        desc_one_line = re.sub(r"\s+", " ", desc)[:200]
        catalog.append({"name": name, "description": desc_one_line})

    results: list[dict[str, Any]] = []
    if probe:
        for tool in tools:
            results.append(await _probe_tool(tool, repo, workspace))

    payload = {
        "mcp_url": settings.mcp_url,
        "repo_root": str(repo),
        "workspace": str(workspace),
        "tool_count": len(catalog),
        "tools": catalog,
        "probes": results,
        "canary_exposed": [
            "security-scan",
            "architecture-analyze",
            "compliance-audit",
            "opsera_report_telemetry",
        ],
        "canary_not_exposed": [
            t["name"] for t in catalog if t["name"] not in {
                "security-scan",
                "architecture-analyze",
                "compliance-audit",
                "opsera_report_telemetry",
            }
        ],
    }

    if json_out:
        print(json.dumps(payload, indent=2))
        return 0 if all(r.get("status") in {"ok", "skipped"} for r in results) else 2

    print(f"Opsera MCP: {settings.mcp_url}")
    print(f"Repo root:  {repo}")
    print(f"Workspace:  {workspace}")
    print(f"\n{len(catalog)} tools on server:\n")
    for item in catalog:
        exposed = " [CANary Deep Agent]" if item["name"] in payload["canary_exposed"] else ""
        print(f"  • {item['name']}{exposed}")
        print(f"    {item['description']}\n")

    if payload["canary_not_exposed"]:
        print("Not wired into CANary Deep Agent yet:")
        for name in payload["canary_not_exposed"]:
            print(f"  - {name}")
        print()

    if probe:
        print("Smoke probes (phase 1 / minimal args):\n")
        for row in results:
            status = row["status"].upper()
            print(f"  [{status}] {row['tool']}")
            if row["status"] == "ok":
                print(f"         → {row['headline']}")
            elif row["status"] == "skipped":
                print(f"         → {row.get('reason', '')}")
            else:
                print(f"         → {row.get('reason', '')}")
        print()

    return 0 if not probe or all(r.get("status") in {"ok", "skipped"} for r in results) else 2


def main() -> None:
    parser = argparse.ArgumentParser(description="List and smoke-test Opsera MCP tools")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("workspaces/default"),
        help="Active workspace path (default: workspaces/default)",
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Invoke each tool with minimal safe args (may take several minutes)",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON results")
    args = parser.parse_args()
    workspace = args.workspace.expanduser().resolve()
    raise SystemExit(asyncio.run(run_probes(workspace=workspace, probe=args.probe, json_out=args.json)))


if __name__ == "__main__":
    main()
