from pathlib import Path

from agent_workbench.domain.agents import AgentSessionContext, build_subagents, build_system_prompt


def test_build_system_prompt_scopes_to_workspace(tmp_path: Path) -> None:
    context = AgentSessionContext(
        session_id="session-1",
        cwd=tmp_path / "workspaces" / "default",
        workspace_mode="local",
        mode="accept_edits",
        model="mock:deterministic",
        command_timeout_seconds=120,
    )
    prompt = build_system_prompt(context)
    assert str(context.cwd.resolve()) in prompt
    assert "bms/SKILL.md" in prompt
    assert "architecture.bms.json" in prompt
    assert "automatically" in prompt


def test_build_subagents_reference_workspace(tmp_path: Path) -> None:
    context = AgentSessionContext(
        session_id="session-1",
        cwd=tmp_path / "workspaces" / "Client-App",
        workspace_mode="local",
        mode="accept_edits",
        model="mock:deterministic",
        command_timeout_seconds=120,
    )
    subagents = build_subagents(context)
    workspace = str(context.cwd.resolve())
    assert all(workspace in item["system_prompt"] for item in subagents[:2])
    assert "architecture.bms.json" in subagents[1]["system_prompt"]
