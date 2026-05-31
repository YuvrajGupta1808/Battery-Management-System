from pathlib import Path

from agent_workbench.domain.agents import (
    AgentSessionContext,
    build_opsera_system_addon,
    build_subagents,
)
from agent_workbench.domain.opsera_prompts import (
    architecture_analyze_prompt,
    compliance_audit_prompt,
    security_scan_prompt,
)
from agent_workbench.infra.opsera_mcp import (
    format_opsera_auth_notice,
    get_opsera_settings,
    make_opsera_defaults_interceptor,
    resolve_opsera_scan_root,
    _fallback_prompts,
)


def test_build_opsera_system_addon_empty_when_disabled(tmp_path: Path) -> None:
    context = AgentSessionContext(
        session_id="session-1",
        cwd=tmp_path / "workspaces" / "default",
        workspace_mode="local",
        mode="accept_edits",
        model="mock:deterministic",
        command_timeout_seconds=120,
    )
    settings = get_opsera_settings(workspace_cwd=context.cwd)
    disabled = OpseraSettings_disabled(settings)
    assert build_opsera_system_addon(context, settings=disabled, mcp_connected=False) == ""


def OpseraSettings_disabled(settings):
    from agent_workbench.infra.opsera_mcp import OpseraSettings

    return OpseraSettings(
        enabled=False,
        mcp_url=settings.mcp_url,
        api_token=None,
        scan_root=settings.scan_root,
        workspace_path=settings.workspace_path,
    )


def test_build_opsera_system_addon_includes_workspace_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "backend").mkdir(parents=True)
    (repo / "apps").mkdir()
    (repo / "backend" / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    workspace = repo / "workspaces" / "Test2"
    workspace.mkdir(parents=True)

    context = AgentSessionContext(
        session_id="session-1",
        cwd=workspace,
        workspace_mode="local",
        mode="accept_edits",
        model="mock:deterministic",
        command_timeout_seconds=120,
    )
    settings = get_opsera_settings(workspace_cwd=context.cwd)
    addon = build_opsera_system_addon(context, settings=settings, mcp_connected=True, mcp_prompts={})
    assert "security-scan" in addon
    assert "opsera_prompt_security_scan" not in addon
    assert "never" in addon.lower()


def test_devsecops_subagent_when_enabled(tmp_path: Path) -> None:
    context = AgentSessionContext(
        session_id="session-1",
        cwd=tmp_path / "workspaces" / "default",
        workspace_mode="local",
        mode="accept_edits",
        model="mock:deterministic",
        command_timeout_seconds=120,
    )
    without = build_subagents(context, include_devsecops=False)
    with_devsecops = build_subagents(context, include_devsecops=True)
    assert len(with_devsecops) == len(without) + 1
    assert "opsera_prompt_security_scan" not in with_devsecops[-1]["system_prompt"]
    assert "Never" in with_devsecops[-1]["system_prompt"]


def test_resolve_opsera_scan_root_finds_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "backend").mkdir(parents=True)
    (repo / "apps").mkdir()
    (repo / "backend" / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    workspace = repo / "workspaces" / "default"
    workspace.mkdir(parents=True)
    assert resolve_opsera_scan_root(workspace) == repo.resolve()


def test_opsera_prompts_include_scan_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    workspace = repo / "workspaces" / "Test2"
    workspace.mkdir(parents=True)
    text = security_scan_prompt(scan_path=workspace, scan_root=repo)
    assert "Do not" in text
    assert "MANDATORY" in text
    assert "BMS architecture" in text
    assert "CANary" in architecture_analyze_prompt(project_name="CANary", scan_root=repo)
    assert "soc2" in compliance_audit_prompt(scan_root=repo)


def test_opsera_settings_disabled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WORKBENCH_OPSERA_ENABLED", "false")
    settings = get_opsera_settings(workspace_cwd=tmp_path)
    assert settings.enabled is False
    assert settings.configured is False


def test_sanitize_security_scan_response_phase2(monkeypatch) -> None:
    from agent_workbench.infra.opsera_mcp import sanitize_security_scan_response

    monkeypatch.setattr(
        "agent_workbench.infra.opsera_mcp.check_opsera_scan_cli_tools",
        lambda: (["gitleaks", "semgrep"], ["grype"]),
    )
    text = sanitize_security_scan_response(2, "Proceed with scan? (yes/no)")
    assert "tool check complete" in text
    assert "Do not" in text and "execute" in text
    assert "gitleaks ✓" in text
    assert "Proceed with scan?" in text


def test_wrap_security_scan_tool_auto_chains_phase2(monkeypatch, tmp_path: Path) -> None:
    from agent_workbench.infra.opsera_mcp import OpseraSettings, wrap_security_scan_tool

    calls: list[int] = []

    async def fake_coro(**kwargs):
        calls.append(int(kwargs["phase"]))
        return f"phase-{kwargs['phase']}-body"

    class FakeTool:
        name = "security-scan"

        def __init__(self) -> None:
            self.coroutine = None
            self.func = None

        def model_copy(self, *, update):
            cloned = FakeTool()
            cloned.__dict__.update({**self.__dict__, **update})
            return cloned

    tool = FakeTool()
    tool.coroutine = fake_coro

    settings = OpseraSettings(
        enabled=True,
        mcp_url="https://example.com/mcp",
        api_token="token",
        scan_root=tmp_path,
        workspace_path=tmp_path / "workspaces" / "default",
    )
    wrapped = wrap_security_scan_tool(tool, settings)
    result = _run_async(wrapped.coroutine(phase=1, path=str(settings.workspace_path)))  # noqa: PLW2901
    assert calls == [1, 2]
    assert "tool check complete" in result
    assert "phase-1-body" in result
    assert "phase-2-body" in result


def _run_async(coro):
    import asyncio

    return asyncio.run(coro)


def test_apply_security_scan_phase_defaults(monkeypatch, tmp_path: Path) -> None:
    from agent_workbench.infra.opsera_mcp import apply_security_scan_phase_defaults

    monkeypatch.setattr(
        "agent_workbench.infra.opsera_mcp.shutil.which",
        lambda name: name if name in {"gitleaks", "semgrep"} else None,
    )
    args = apply_security_scan_phase_defaults({"phase": 2, "path": str(tmp_path)})
    assert args["tools_ready"] is True
    assert set(args["skipped_tools"]) == {"grype", "checkov", "hadolint"}


def test_opsera_defaults_interceptor(tmp_path: Path) -> None:
    import asyncio

    from agent_workbench.infra.opsera_mcp import OpseraSettings

    repo = tmp_path / "repo"
    workspace = repo / "workspaces" / "Test2"
    workspace.mkdir(parents=True)
    settings = OpseraSettings(
        enabled=True,
        mcp_url="https://agent.opsera.ai/mcp",
        api_token=None,
        scan_root=repo,
        workspace_path=workspace,
    )
    interceptor = make_opsera_defaults_interceptor(settings)
    captured: dict[str, object] = {}

    async def handler(request):
        captured["args"] = dict(request.args)
        return "ok"

    async def run():
        from langchain_mcp_adapters.interceptors import MCPToolCallRequest

        request = MCPToolCallRequest(
            name="security-scan",
            args={"phase": 1},
            server_name="opsera",
        )
        await interceptor(request, handler)

    asyncio.run(run())
    args = captured["args"]
    assert args["path"] == str(workspace)
    assert args["scan_type"] == "full"
    assert args["severity_threshold"] == "high"
    assert args["user_confirmed"] is True


def test_opsera_defaults_interceptor_phase1_no_tools_ready(tmp_path: Path) -> None:
    import asyncio

    from agent_workbench.infra.opsera_mcp import OpseraSettings

    workspace = tmp_path / "workspaces" / "Test2"
    workspace.mkdir(parents=True)
    settings = OpseraSettings(
        enabled=True,
        mcp_url="https://agent.opsera.ai/mcp",
        api_token=None,
        scan_root=tmp_path,
        workspace_path=workspace,
    )
    interceptor = make_opsera_defaults_interceptor(settings)
    captured: dict[str, object] = {}

    async def handler(request):
        captured["args"] = dict(request.args)
        return "ok"

    async def run():
        from langchain_mcp_adapters.interceptors import MCPToolCallRequest

        request = MCPToolCallRequest(
            name="security-scan",
            args={"phase": 1},
            server_name="opsera",
        )
        await interceptor(request, handler)

    asyncio.run(run())
    assert "tools_ready" not in captured["args"]


def test_opsera_defaults_interceptor_phase2_tools_ready(monkeypatch, tmp_path: Path) -> None:
    import asyncio

    from agent_workbench.infra.opsera_mcp import OpseraSettings

    monkeypatch.setattr(
        "agent_workbench.infra.opsera_mcp.shutil.which",
        lambda name: None,
    )
    workspace = tmp_path / "workspaces" / "Test2"
    workspace.mkdir(parents=True)
    settings = OpseraSettings(
        enabled=True,
        mcp_url="https://agent.opsera.ai/mcp",
        api_token=None,
        scan_root=tmp_path,
        workspace_path=workspace,
    )
    interceptor = make_opsera_defaults_interceptor(settings)
    captured: dict[str, object] = {}

    async def handler(request):
        captured["args"] = dict(request.args)
        return "ok"

    async def run():
        from langchain_mcp_adapters.interceptors import MCPToolCallRequest

        request = MCPToolCallRequest(
            name="security-scan",
            args={"phase": 2},
            server_name="opsera",
        )
        await interceptor(request, handler)

    asyncio.run(run())
    assert captured["args"]["tools_ready"] is True
    assert "skipped_tools" in captured["args"]


def test_mcp_tools_support_sync_invoke(tmp_path: Path) -> None:
    from agent_workbench.infra.opsera_mcp import (
        clear_opsera_tools_cache,
        load_opsera_mcp_bundle,
    )

    if not get_opsera_settings(workspace_cwd=tmp_path).configured:
        return

    clear_opsera_tools_cache()
    settings = get_opsera_settings(workspace_cwd=tmp_path / "workspaces" / "default")
    bundle = load_opsera_mcp_bundle(settings)
    if not bundle.configured:
        return

    tool = next(t for t in bundle.tools if t.name == "security-scan")
    assert getattr(tool, "func", None) is not None
    result = tool.invoke(
        {
            "phase": 1,
            "path": str(tmp_path),
            "scan_type": "full",
            "severity_threshold": "high",
            "user_confirmed": True,
        }
    )
    assert result is not None


def test_format_opsera_auth_notice_without_token(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPSERA_API_TOKEN", raising=False)
    monkeypatch.setattr("agent_workbench.infra.opsera_mcp.has_stored_opsera_oauth", lambda: False)
    settings = get_opsera_settings(workspace_cwd=tmp_path)
    notice = format_opsera_auth_notice(settings)
    assert "make opsera-login" in notice
    assert "Cursor" in notice
