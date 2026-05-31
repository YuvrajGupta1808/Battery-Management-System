"""Agent construction for HTTP streaming."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ..infra.opsera_mcp import (
    OpseraSettings,
    format_mcp_prompts_for_system,
    format_opsera_auth_notice,
    get_opsera_settings,
    load_opsera_mcp_bundle,
    opsera_reports_dir,
    resolve_opsera_scan_root,
)
from ..infra.security import redact_env
from ..infra.workspace_backend import WorkspaceLocalShellBackend
from .fireworks_openai import FireworksReasoningChatOpenAI
from .models import SessionMode, WorkspaceMode

try:  # Optional: the app runs in mock mode without these packages.
    from deepagents import FilesystemPermission, create_deep_agent
    from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover - exercised in environments without deepagents
    FilesystemPermission = None  # type: ignore[assignment]
    create_deep_agent = None  # type: ignore[assignment]
    CompositeBackend = None  # type: ignore[assignment]
    StateBackend = None  # type: ignore[assignment]
    StoreBackend = None  # type: ignore[assignment]
    ChatOpenAI = None  # type: ignore[assignment]


def build_system_prompt(context: AgentSessionContext) -> str:
    workspace = context.cwd.resolve()
    return f"""You are CANary AI — a BMS validation engineer running in a local workbench.

Active workspace root: {workspace}

Primary job: **author BMS circuit diagrams** as structured files the UI renders as SVG schematics.

## Default workflow (you do this automatically — users never need to ask)

When the user describes a pack, topology, parts, or protection thresholds (even briefly):

1. Read `/bms/SKILL.md`, `/bms/templates/architecture.template.bms.json`, and `/bms/templates/safety_rules.template.yaml` **once** — in parallel if possible.
2. `write_file` **both** `/bms/architecture.bms.json` and `/bms/safety_rules.yaml` in the **same tool batch**:
   - Start from the templates; remove `template_meta`; apply the user's topology, part numbers, labels, and thresholds.
   - **Reshape the schematic per topology** (cell stack width, AFE count/pins, busbars for 2p+, part-specific labels) — not just `pack{{}}` fields.
   - Overwrite is allowed on those two output paths.
3. Reply with a short summary of what was designed — **then stop**.
   - Do **not** create todos for standard design requests.
   - Do **not** re-read output files to verify (validation runs on write).
   - Do **not** read the JSON schema unless a write is rejected.
   - Do **not** spawn subagents for a straightforward new design.
   - Keep reasoning under ~10 lines.

Users say things like: "4s1p NMC e-scooter, BQ76952, fan at 75°C" — you infer the rest from SKILL + templates.

## Threshold / rules-only changes

Read existing `/bms/architecture.bms.json` and `/bms/safety_rules.yaml`, explain Current → Proposed → Reason, write the changed file(s), stop.

## File rules

- Paths: `/bms/...` only — never host paths like `/Users/...`.
- Never edit files under `/bms/templates/`.
- Every edge must reference existing node and pin ids (backend rejects dangling edges).
- Safety rules: top-level YAML list (`- id: ...`); use `component: mcu`; no `rules:` wrapper.

Scope: stay inside this workspace (`/` = workspace root). Backend validates BMS writes — if rejected, read the error, fix once, rewrite.

Never read or write secret files. Ask for approval before shell commands when required."""


def build_opsera_system_addon(
    context: AgentSessionContext,
    *,
    settings: OpseraSettings,
    mcp_connected: bool,
    mcp_prompts: dict[str, str] | None = None,
) -> str:
    if not settings.enabled:
        return ""
    scan_root = resolve_opsera_scan_root(context.cwd)
    workspace = context.cwd.resolve()
    reports_dir = opsera_reports_dir(scan_root)
    prompt_section = format_mcp_prompts_for_system(mcp_prompts or {}) if mcp_connected else ""
    auth_notice = format_opsera_auth_notice(settings)
    tools_line = (
        "MCP tools: **security-scan**, **architecture-analyze**, **compliance-audit**, "
        "**business-docs-generate**, **dora-metrics**, **sql-security**, **opsera_report_telemetry**. "
        "(`vibe-shift` CI/CD is Cursor MCP only — needs AWS cluster/region.)"
        if mcp_connected
        else "MCP scan tools are **offline** until you authenticate (see Auth below)."
    )
    workflow = (
        f"1. Call `security-scan` with `phase: 1` once — CANary auto-completes phase 2 in that response.\n"
        f"2. **Never** run `execute` to check gitleaks/semgrep — tool check is already done.\n"
        f"3. Ignore Opsera text: 'Proceed with scan?', 'STOP and WAIT', missing-tool menus.\n"
        f"4. Path `{workspace}`, scan_type `full`, severity `high`. Reports: `{reports_dir}`.\n"
        f"5. After phase 6, summarize findings and fix critical/high issues in-repo."
        if mcp_connected
        else "Tell the user to run `make opsera-login` or use Cursor MCP for Opsera scans until auth is configured."
    )
    return f"""

## Opsera DevSecOps

{auth_notice}

{tools_line}

- **Active workspace** (default scan path): `{workspace}`
- **Repository root** (full codebase scans): `{scan_root}`
- **Reports**: `{reports_dir}`
- Skill: `/skills/opsera-devsecops/SKILL.md`

When the user asks to scan, audit, or check compliance — **only** (not a BMS design request):
- Go **directly** to Opsera MCP tools. Do **not** read `/bms/architecture.bms.json` or `/bms/safety_rules.yaml` first.
{workflow}

{prompt_section}"""


def build_subagents(context: AgentSessionContext, *, include_devsecops: bool = False) -> list[dict[str, str]]:
    workspace = str(context.cwd.resolve())
    subagents: list[dict[str, str]] = [
        {
            "name": "explorer",
            "description": "Read-only BMS architecture and safety rules analysis.",
            "system_prompt": (
                f"Inspect BMS files under {workspace}: architecture.bms.json, safety_rules.yaml, bms/SKILL.md. "
                "Analyze topology, components, and protection rules. Do not edit files."
            ),
        },
        {
            "name": "implementer",
            "description": "Writes BMS diagram files and safety rules in the workspace.",
            "system_prompt": (
                f"Write /bms/architecture.bms.json and /bms/safety_rules.yaml inside {workspace}. "
                "Default: read /bms/SKILL.md and templates once, write both output files from templates "
                "(remove template_meta), stop without re-reading. Follow bms/SKILL.md. Summarize briefly."
            ),
        },
        {
            "name": "reviewer",
            "description": "Read-only review of BMS diagrams and safety rule consistency.",
            "system_prompt": (
                "Review BMS architecture and safety_rules.yaml for schema compliance, threshold consistency, "
                "and missing protection coverage. Prioritize actionable safety findings."
            ),
        },
        {
            "name": "test_runner",
            "description": "Verifies BMS files parse and drafts validation scenarios.",
            "system_prompt": (
                f"Verify BMS JSON/YAML files under {workspace} are valid. Draft fault-injection test scenarios "
                "(no simulation execution yet). Keep output concise."
            ),
        },
    ]
    if include_devsecops:
        scan_root = resolve_opsera_scan_root(context.cwd)
        workspace = context.cwd.resolve()
        reports_dir = opsera_reports_dir(scan_root)
        subagents.append(
            {
                "name": "devsecops",
                "description": "Opsera security scans, architecture analysis, compliance audits, and remediation.",
                "system_prompt": (
                    f"Opsera security-scan on `{workspace}` (repo `{scan_root}`). Reports `{reports_dir}`. "
                    "Run phases 1→6 in one run. Phase 1 call auto-completes phase 2 in CANary. "
                    "**Never** use `execute` for gitleaks/semgrep tool checks. "
                    "Do not read BMS files unless fixing findings. "
                    "After phase 6: fix critical/high findings; report Findings → Fix → Verification."
                ),
            }
        )
    return subagents


def get_interrupt_config(mode_id: SessionMode) -> dict[str, Any]:
    mode_to_interrupt: dict[str, dict[str, Any]] = {
        "ask_before_edits": {
            "edit_file": {"allowed_decisions": ["approve", "reject"]},
            "write_file": {"allowed_decisions": ["approve", "reject"]},
            "write_todos": {"allowed_decisions": ["approve", "reject"]},
            "execute": {"allowed_decisions": ["approve", "reject"]},
        },
        "accept_edits": {
            "execute": {"allowed_decisions": ["approve", "reject"]},
        },
        "accept_everything": {},
    }
    return mode_to_interrupt[mode_id]


@dataclass(frozen=True)
class AgentSessionContext:
    session_id: str
    cwd: Path
    workspace_mode: WorkspaceMode
    mode: SessionMode
    model: str
    command_timeout_seconds: int


class MockCodingAgent:
    """Deterministic local fallback that exercises the same stream surface as Deep Agents."""

    def __init__(self, context: AgentSessionContext) -> None:
        self.context = context

    def stream(self, payload: dict[str, Any], **_: Any) -> Iterable[dict[str, Any]]:
        message = payload.get("messages", [{}])[-1].get("content", "")
        yield {"type": "updates", "ns": (), "data": {"model_request": {"status": "started"}}}
        yield {
            "type": "custom",
            "ns": (),
            "data": {
                "event": "todo",
                "items": [
                    {"id": "understand", "text": "Understand the request", "status": "completed"},
                    {"id": "inspect", "text": "Inspect workspace files", "status": "active"},
                    {"id": "implement", "text": "Prepare implementation changes", "status": "pending"},
                    {"id": "verify", "text": "Run focused verification", "status": "pending"},
                ],
            },
        }
        yield {
            "type": "custom",
            "ns": ("tools:explorer",),
            "data": {
                "event": "subagent",
                "name": "explorer",
                "status": "running",
                "summary": f"Inspecting {self.context.cwd}",
            },
        }
        yield {
            "type": "messages",
            "ns": (),
            "data": (
                {"type": "ai", "content": "I will inspect the workspace, plan the edits, and stream each step. "},
                {"langgraph_node": "model_request"},
            ),
        }
        yield {
            "type": "custom",
            "ns": (),
            "data": {
                "event": "tool_call",
                "name": "ls",
                "args": {"path": str(self.context.cwd)},
                "result": f"Workspace listing requested for {self.context.cwd}",
            },
        }
        if self.context.mode != "accept_everything":
            yield {
                "type": "custom",
                "ns": (),
                "data": {
                    "event": "approval_required",
                    "tool": "execute",
                    "payload": {"command": "pytest", "cwd": str(self.context.cwd)},
                },
            }
        yield {
            "type": "custom",
            "ns": (),
            "data": {
                "event": "file_change",
                "path": "README.md",
                "operation": "read",
                "summary": "Mock agent inspected the project README.",
            },
        }
        yield {
            "type": "messages",
            "ns": (),
            "data": (
                {
                    "type": "ai",
                    "content": f"Request captured: {message[:140]}. Real Deep Agents streaming will activate when dependencies and model credentials are configured.",
                },
                {"langgraph_node": "model_request"},
            ),
        }
        yield {
            "type": "custom",
            "ns": ("tools:explorer",),
            "data": {"event": "subagent", "name": "explorer", "status": "completed", "summary": "Workspace scan complete."},
        }


def _permissions() -> list[Any]:
    if FilesystemPermission is None:
        return []
    return [
        FilesystemPermission(operations=["read", "write"], paths=["/workspace/.env", "/workspace/.env.*"], mode="deny"),
        FilesystemPermission(operations=["read", "write"], paths=["/workspace/**"], mode="allow"),
        FilesystemPermission(operations=["read", "write"], paths=["/memories/**"], mode="allow"),
        FilesystemPermission(operations=["read", "write"], paths=["/skills/**"], mode="allow"),
        FilesystemPermission(operations=["write"], paths=["/policies/**"], mode="deny"),
        FilesystemPermission(operations=["read", "write"], paths=["/**"], mode="deny"),
    ]


def build_agent(
    context: AgentSessionContext,
    *,
    checkpointer: Any | None = None,
    store: Any | None = None,
) -> Any:
    """Build a Deep Agent when installed, otherwise a deterministic mock agent."""

    if context.model.startswith("mock:") or create_deep_agent is None:
        return MockCodingAgent(context)
    if context.workspace_mode == "remote_sandbox":
        return MockCodingAgent(context)

    # Fireworks is OpenAI-compatible. When users select Fireworks models via
    # openai:accounts/fireworks/models/*, map FIREWORKS_* env vars to the
    # OpenAI-compatible env names expected by LangChain adapters.
    if "accounts/fireworks/models/" in context.model:
        if not os.getenv("OPENAI_API_KEY") and os.getenv("FIREWORKS_API_KEY"):
            os.environ["OPENAI_API_KEY"] = str(os.getenv("FIREWORKS_API_KEY"))
        if not os.getenv("OPENAI_BASE_URL"):
            os.environ["OPENAI_BASE_URL"] = "https://api.fireworks.ai/inference/v1"

    assert StateBackend is not None
    assert CompositeBackend is not None
    assert StoreBackend is not None

    from ..infra.deep_agent_resources import get_checkpointer, get_langgraph_store

    resolved_checkpointer = checkpointer if checkpointer is not None else get_checkpointer()
    resolved_store = store if store is not None else get_langgraph_store()

    opsera_settings = get_opsera_settings(workspace_cwd=context.cwd)
    opsera_bundle = load_opsera_mcp_bundle(opsera_settings)
    opsera_tools = opsera_bundle.tools
    opsera_enabled = opsera_bundle.enabled

    shell_backend = WorkspaceLocalShellBackend(
        root_dir=str(context.cwd),
        inherit_env=True,
        env=redact_env(os.environ.copy()),
    )
    ephemeral_backend = StateBackend()
    session_ns = context.session_id

    # Pass a CompositeBackend instance (not a factory). MemoryMiddleware resolves callable
    # backends by synthesizing ToolRuntime and omits required fields on current langchain.
    backend = CompositeBackend(
        default=shell_backend,
        routes={
            "/memories/": StoreBackend(
                store=resolved_store,
                namespace=lambda _rt: (session_ns,),
            ),
            "/skills/": StoreBackend(
                store=resolved_store,
                namespace=lambda _rt: (session_ns,),
            ),
            "/policies/": StoreBackend(
                store=resolved_store,
                namespace=lambda _rt: ("workbench",),
            ),
            "/conversation_history/": ephemeral_backend,
        },
    )

    model: Any = context.model
    if context.model.startswith("openai:") and ChatOpenAI is not None:
        openai_model = context.model.split("openai:", 1)[1]
        chat_kwargs: dict[str, Any] = {
            "model": openai_model,
            "timeout": float(max(context.command_timeout_seconds, 30)),
            "max_retries": 1,
        }
        if "accounts/fireworks/models/" in context.model:
            chat_kwargs["base_url"] = os.getenv("OPENAI_BASE_URL", "https://api.fireworks.ai/inference/v1")
            model = FireworksReasoningChatOpenAI(**chat_kwargs)
        else:
            model = ChatOpenAI(**chat_kwargs)

    kwargs: dict[str, Any] = {
        "model": model,
        "system_prompt": build_system_prompt(context)
        + build_opsera_system_addon(
            context,
            settings=opsera_settings,
            mcp_connected=opsera_bundle.configured,
            mcp_prompts=opsera_bundle.mcp_prompts,
        ),
        "backend": backend,
        "interrupt_on": get_interrupt_config(context.mode),
        "subagents": build_subagents(context, include_devsecops=opsera_enabled),
        "memory": [
            "/memories/WORKBENCH.md",
            "/policies/compliance.md",
        ],
        "skills": ["/skills/"],
        "store": resolved_store,
        "checkpointer": resolved_checkpointer,
    }
    if opsera_tools:
        kwargs["tools"] = opsera_tools
    # Deep Agents 0.5.x permission middleware does not yet support command-capable
    # backends. Keep shell safety on the backend boundary through workspace root
    # scoping, env redaction, and interrupt_on execute approvals.
    if os.getenv("WORKBENCH_ENABLE_DEEPAGENTS_PERMISSIONS") == "true":
        kwargs["permissions"] = _permissions()
    return create_deep_agent(**kwargs)
