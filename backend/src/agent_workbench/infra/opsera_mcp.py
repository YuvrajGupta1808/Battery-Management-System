"""Opsera DevSecOps MCP client for Deep Agents (langchain-mcp-adapters)."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from langchain_mcp_adapters.interceptors import MCPToolCallRequest

from ..domain.opsera_prompts import (
    architecture_analyze_prompt,
    compliance_audit_prompt,
    security_scan_prompt,
)
from .opsera_oauth import create_opsera_oauth_provider, has_stored_opsera_oauth

logger = logging.getLogger(__name__)

_OPSERA_TOOL_NAMES = frozenset(
    {
        "security-scan",
        "architecture-analyze",
        "compliance-audit",
        "business-docs-generate",
        "dora-metrics",
        "sql-security",
        "opsera_report_telemetry",
        # vibe-shift requires AWS cluster/region — invoke via Cursor MCP only
    }
)

_OPSERA_MCP_PROMPTS = ("security-scan", "architecture-analyze", "compliance-audit")

_bundle_lock = Lock()
_bundle_cache: OpseraMCPBundle | None = None
_bundle_cache_key: tuple[str, str, str, str, str, bool] | None = None


@dataclass(frozen=True)
class OpseraSettings:
    enabled: bool
    mcp_url: str
    api_token: str | None
    scan_root: Path | None
    workspace_path: Path | None = None

    @property
    def default_scan_path(self) -> Path | None:
        """Active BMS workspace when set; otherwise repository root."""
        if self.workspace_path is not None:
            return self.workspace_path.resolve()
        if self.scan_root is not None:
            return self.scan_root.resolve()
        return None

    @property
    def auth_mode(self) -> str:
        if self.api_token:
            return "token"
        if has_stored_opsera_oauth():
            return "oauth"
        return "none"

    @property
    def configured(self) -> bool:
        return self.enabled and self.auth_mode != "none"


@dataclass
class OpseraMCPBundle:
    """Tools and MCP prompts loaded from Opsera via MultiServerMCPClient."""

    tools: list[Any] = field(default_factory=list)
    mcp_prompts: dict[str, str] = field(default_factory=dict)
    scan_root: Path | None = None
    configured: bool = False

    @property
    def enabled(self) -> bool:
        return self.configured and len(self.tools) > 0


def get_opsera_settings(*, workspace_cwd: Path | None = None) -> OpseraSettings:
    enabled_raw = os.getenv("WORKBENCH_OPSERA_ENABLED", "true").strip().lower()
    enabled = enabled_raw not in {"0", "false", "no", "off"}
    scan_root: Path | None = None
    if workspace_cwd is not None:
        scan_root = resolve_opsera_scan_root(workspace_cwd)
    explicit_root = os.getenv("WORKBENCH_OPSERA_SCAN_ROOT", "").strip()
    if explicit_root:
        scan_root = Path(explicit_root).expanduser().resolve()
    workspace = workspace_cwd.expanduser().resolve() if workspace_cwd is not None else None
    return OpseraSettings(
        enabled=enabled,
        mcp_url=os.getenv("OPSERA_MCP_URL", "https://agent.opsera.ai/mcp").strip(),
        api_token=(os.getenv("OPSERA_API_TOKEN") or os.getenv("OPSERA_TOKEN") or "").strip() or None,
        scan_root=scan_root,
        workspace_path=workspace,
    )


def resolve_opsera_scan_root(workspace_cwd: Path) -> Path:
    """Repository root for Opsera scans (not the per-client workspace folder)."""
    explicit = os.getenv("WORKBENCH_OPSERA_SCAN_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    current = workspace_cwd.expanduser().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "backend" / "pyproject.toml").is_file() and (candidate / "apps").is_dir():
            return candidate
    return current


def opsera_reports_dir(scan_root: Path) -> Path:
    return scan_root / "docs" / "opsera-scan" / "reports"


_OPSERA_SCAN_CLI_TOOLS = ("gitleaks", "semgrep", "grype", "checkov", "hadolint")


def check_opsera_scan_cli_tools() -> tuple[list[str], list[str]]:
    """Return (installed, missing) Opsera CLI scanners."""
    installed: list[str] = []
    missing: list[str] = []
    for name in _OPSERA_SCAN_CLI_TOOLS:
        if shutil.which(name):
            installed.append(name)
        else:
            missing.append(name)
    return installed, missing


def format_cli_tools_status() -> str:
    installed, missing = check_opsera_scan_cli_tools()
    parts = [f"{name} ✓" for name in installed]
    parts.extend(f"{name} (skipped)" for name in missing)
    return ", ".join(parts) if parts else "none"


def _tool_result_to_text(result: Any) -> str:
    if isinstance(result, tuple) and result:
        return _tool_result_to_text(result[0])
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        return _messages_to_prompt_text(result)
    if isinstance(result, dict):
        text = result.get("text")
        if isinstance(text, str):
            return text
    return str(result)


def _with_sanitized_text(result: Any, sanitized: str) -> Any:
    if isinstance(result, tuple) and result:
        tail = result[1:] if len(result) > 1 else ()
        return (sanitized, *tail)
    return sanitized


def sanitize_security_scan_response(phase: int, text: str) -> str:
    """Replace Opsera phase 1–2 questionnaires with CANary next-step guidance."""
    if phase not in (1, 2):
        return text
    return (
        "# CANary — tool check complete (phases 1–2)\n\n"
        f"CLI scanners: {format_cli_tools_status()}.\n\n"
        "**Do not** run `execute` to verify gitleaks, semgrep, grype, checkov, or hadolint.\n"
        "**Do not** ask the user to confirm tools, install tools, or proceed with scan.\n"
        "**Next:** Run any Phase 3 scan shell commands below via `execute`, then call "
        "`security-scan` with `phase: 3` and `scans_complete: true`. Continue through phase 6.\n\n"
        "---\n\n"
        f"{text}"
    )


def _prepare_security_scan_args(settings: OpseraSettings, kwargs: dict[str, Any]) -> dict[str, Any]:
    args = dict(kwargs)
    scan_path = settings.default_scan_path
    if scan_path is not None and not args.get("path"):
        args["path"] = str(scan_path)
    args.setdefault("scan_type", "full")
    args.setdefault("severity_threshold", "high")
    args.setdefault("scan_mode", "standard")
    args.setdefault("user_confirmed", True)
    if args.get("phase") in (None, 1):
        args.setdefault("phase", 1)
    return apply_security_scan_phase_defaults(args)


def wrap_security_scan_tool(tool: Any, settings: OpseraSettings) -> Any:
    """Auto-chain phases 1→2 and strip Opsera tool-check questionnaires from responses."""
    if getattr(tool, "name", "") != "security-scan":
        return tool
    original_coro = getattr(tool, "coroutine", None)
    if original_coro is None:
        return tool

    async def wrapped_coro(**kwargs: Any) -> Any:
        args = _prepare_security_scan_args(settings, kwargs)
        phase = int(args.get("phase") or 1)
        if phase == 1:
            phase1_args = {**args, "phase": 1}
            phase2_args = apply_security_scan_phase_defaults({**args, "phase": 2})
            result1 = await original_coro(**phase1_args)
            result2 = await original_coro(**phase2_args)
            combined = f"{_tool_result_to_text(result1)}\n\n---\n\n{_tool_result_to_text(result2)}"
            return _with_sanitized_text(result2, sanitize_security_scan_response(2, combined))
        result = await original_coro(**args)
        return _with_sanitized_text(result, sanitize_security_scan_response(phase, _tool_result_to_text(result)))

    return tool.model_copy(update={"coroutine": wrapped_coro, "func": None})


def apply_security_scan_phase_defaults(args: dict[str, Any]) -> dict[str, Any]:
    """CANary auto-approvals for Opsera security-scan phases (no user questionnaires)."""
    phase = int(args.get("phase") or 1)
    if phase >= 2:
        _, missing = check_opsera_scan_cli_tools()
        args["tools_ready"] = True
        if missing:
            args["skipped_tools"] = missing
        elif "skipped_tools" in args and not args["skipped_tools"]:
            args.pop("skipped_tools", None)
    if phase >= 4:
        args.setdefault("reports_generated", True)
    if phase >= 5:
        args.setdefault("telemetry_reported", True)
    return args


def _opsera_connection(settings: OpseraSettings) -> dict[str, Any]:
    """HTTP MCP connection config per LangChain docs (streamable-http → transport: http)."""
    conn: dict[str, Any] = {
        "transport": "http",
        "url": settings.mcp_url,
    }
    if settings.auth_mode == "token" and settings.api_token:
        conn["headers"] = {"Authorization": f"Bearer {settings.api_token}"}
    elif settings.auth_mode == "oauth":
        conn["auth"] = create_opsera_oauth_provider(settings.mcp_url)
    return {"opsera": conn}


def make_opsera_defaults_interceptor(settings: OpseraSettings):
    """Inject CANary defaults into Opsera MCP tools — no user questionnaires."""

    async def inject_defaults(request: MCPToolCallRequest, handler):
        args = dict(request.args or {})
        scan_path = settings.default_scan_path
        repo_root = settings.scan_root

        if request.name == "security-scan":
            if scan_path is not None and not args.get("path"):
                args["path"] = str(scan_path)
            args.setdefault("scan_type", "full")
            args.setdefault("severity_threshold", "high")
            args.setdefault("scan_mode", "standard")
            args.setdefault("user_confirmed", True)
            if args.get("phase") in (None, 1):
                args.setdefault("phase", 1)
            args = apply_security_scan_phase_defaults(args)
        elif request.name == "architecture-analyze" and repo_root is not None:
            args.setdefault("repositories", str(repo_root))
            args.setdefault("project_name", "CANary")
            args.setdefault("report_format", "Markdown")
        elif request.name == "compliance-audit":
            args.setdefault("framework", "soc2")
            args.setdefault("scope", "full")
            args.setdefault("evidence_collection", "hybrid")
            args.setdefault("output_format", "detailed")
            if args.get("include_remediation") is None:
                args["include_remediation"] = True
        elif request.name == "business-docs-generate" and repo_root is not None:
            args.setdefault("repositories", str(repo_root))
            args.setdefault("project_name", "CANary")
            args.setdefault("output_format", "Markdown")
        elif request.name == "dora-metrics" and repo_root is not None:
            args.setdefault("repository_path", str(repo_root))
            args.setdefault("period_days", 90)
            args.setdefault("output_format", "summary")
        elif request.name == "sql-security" and repo_root is not None:
            args.setdefault("action", "scan")
            args.setdefault("sql_file", str(repo_root))
            args.setdefault("severity_threshold", "high")

        if args != request.args:
            request = request.override(args=args)
        return await handler(request)

    return inject_defaults


async def _logging_interceptor(request: MCPToolCallRequest, handler):
    logger.info("Opsera MCP tool call: %s", request.name)
    try:
        result = await handler(request)
        logger.info("Opsera MCP tool completed: %s", request.name)
        return result
    except Exception:
        logger.exception("Opsera MCP tool failed: %s", request.name)
        raise


def create_opsera_mcp_client(settings: OpseraSettings) -> Any:
    """Build a MultiServerMCPClient for Opsera (stateless sessions per tool call)."""
    from langchain_mcp_adapters.client import MultiServerMCPClient

    interceptors = [_logging_interceptor, make_opsera_defaults_interceptor(settings)]

    return MultiServerMCPClient(
        _opsera_connection(settings),
        tool_interceptors=interceptors,
    )


def _messages_to_prompt_text(messages: Any) -> str:
    parts: list[str] = []
    for message in messages or []:
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
            continue
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
    return "\n\n".join(parts)


def _canary_prompts(settings: OpseraSettings) -> dict[str, str]:
    repo = settings.scan_root or Path(".")
    scan_path = settings.default_scan_path or repo
    return {
        "security-scan": security_scan_prompt(scan_path=scan_path, scan_root=repo),
        "architecture-analyze": architecture_analyze_prompt(project_name="CANary", scan_root=repo),
        "compliance-audit": compliance_audit_prompt(scan_root=repo),
    }


def _fallback_prompts(scan_root: Path | None, workspace_path: Path | None = None) -> dict[str, str]:
    repo = scan_root or Path(".")
    scan_path = workspace_path or repo
    return {
        "security-scan": security_scan_prompt(scan_path=scan_path, scan_root=repo),
        "architecture-analyze": architecture_analyze_prompt(project_name="CANary", scan_root=repo),
        "compliance-audit": compliance_audit_prompt(scan_root=repo),
    }


async def _load_opsera_bundle_async(settings: OpseraSettings) -> OpseraMCPBundle:
    if not settings.configured:
        return OpseraMCPBundle(configured=False, scan_root=settings.scan_root)

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        logger.warning("langchain-mcp-adapters not installed; Opsera MCP disabled")
        return OpseraMCPBundle(configured=False, scan_root=settings.scan_root)

    client: MultiServerMCPClient = create_opsera_mcp_client(settings)

    mcp_tools = await client.get_tools()
    filtered = make_tools_sync_compatible(
        [
            wrap_security_scan_tool(tool, settings)
            if getattr(tool, "name", "") == "security-scan"
            else tool
            for tool in mcp_tools
            if getattr(tool, "name", "") in _OPSERA_TOOL_NAMES
        ]
    )

    # CANary-authored guidance only — Opsera server prompts require interactive questionnaires.
    canary_prompts = _canary_prompts(settings)

    return OpseraMCPBundle(
        tools=filtered,
        mcp_prompts=canary_prompts,
        scan_root=settings.scan_root,
        configured=True,
    )


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_tools_sync_compatible(tools: list[Any]) -> list[Any]:
    """langchain-mcp-adapters tools are async-only; Deep Agents stream invokes sync `func`."""
    wrapped: list[Any] = []
    for tool in tools:
        coroutine = getattr(tool, "coroutine", None)
        if coroutine is None or getattr(tool, "func", None) is not None:
            wrapped.append(tool)
            continue

        def _sync(*, _coro=coroutine, **kwargs: Any) -> Any:
            return _run_async(_coro(**kwargs))

        wrapped.append(tool.model_copy(update={"func": _sync}))
    return wrapped


def load_opsera_mcp_bundle(settings: OpseraSettings) -> OpseraMCPBundle:
    """Load Opsera MCP tools + prompts (cached per URL, auth, scan root)."""
    global _bundle_cache, _bundle_cache_key
    fallbacks = _fallback_prompts(settings.scan_root, settings.workspace_path)
    fallback_only = OpseraMCPBundle(
        tools=[],
        mcp_prompts=fallbacks,
        scan_root=settings.scan_root,
        configured=False,
    )

    if not settings.enabled:
        return fallback_only

    if not settings.configured:
        logger.info(
            "Opsera MCP not authenticated. Run: make opsera-login "
            "(browser sign-in, same as Cursor MCP). Optional: set OPSERA_API_TOKEN in .env."
        )
        return fallback_only

    scan_key = str(settings.scan_root or "")
    workspace_key = str(settings.workspace_path or "")
    cache_key = (
        settings.mcp_url,
        settings.auth_mode,
        settings.api_token or "",
        scan_key,
        workspace_key,
        settings.enabled,
    )
    with _bundle_lock:
        if _bundle_cache is not None and _bundle_cache_key == cache_key:
            return _bundle_cache

    try:
        bundle = _run_async(_load_opsera_bundle_async(settings))
    except Exception:
        logger.exception("Failed to load Opsera MCP bundle")
        bundle = OpseraMCPBundle(
            tools=[],
            mcp_prompts=fallbacks,
            scan_root=settings.scan_root,
            configured=False,
        )

    with _bundle_lock:
        _bundle_cache = bundle
        _bundle_cache_key = cache_key
    return bundle


def load_opsera_tools(settings: OpseraSettings) -> list[Any]:
    """Return LangChain tools from the Opsera MCP bundle (MCP + prompt helpers)."""
    return list(load_opsera_mcp_bundle(settings).tools)


def clear_opsera_tools_cache() -> None:
    global _bundle_cache, _bundle_cache_key
    with _bundle_lock:
        _bundle_cache = None
        _bundle_cache_key = None


def format_opsera_auth_notice(settings: OpseraSettings) -> str:
    if settings.auth_mode == "oauth":
        return "Auth: browser OAuth session (stored in `.data/opsera-oauth.json`)."
    if settings.auth_mode == "token":
        return "Auth: `OPSERA_API_TOKEN` bearer token."
    return (
        "Auth: **not connected**. Opsera MCP scan tools are unavailable in this chat session. "
        "Run `make opsera-login` once (browser Google sign-in — same as Cursor MCP), then restart the backend. "
        "Or use Opsera in **Cursor Agent** chat via `.cursor/mcp.json` (no token needed there)."
    )


def format_mcp_prompts_for_system(mcp_prompts: dict[str, str]) -> str:
    if not mcp_prompts:
        return ""
    return (
        "### Security scan phase loop\n\n"
        "- One `security-scan` call with `phase: 1` auto-completes phase 2 (CANary wrapper)\n"
        "- **Never** run `execute` for gitleaks/semgrep tool checks — already done\n"
        "- Run Phase 3 shell commands via `execute`, then call `security-scan` phase 3→6\n"
        "- Ignore Opsera confirmation banners\n"
    )
