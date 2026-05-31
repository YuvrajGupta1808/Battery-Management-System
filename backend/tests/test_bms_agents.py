from pathlib import Path

from agent_workbench.domain.agents import AgentSessionContext, build_subagents, build_system_prompt


def test_system_prompt_mentions_bms_authoring() -> None:
    context = AgentSessionContext(
        session_id="s1",
        cwd=Path("/tmp/ws/default"),
        workspace_mode="local",
        mode="accept_edits",
        model="mock:deterministic",
        command_timeout_seconds=120,
    )
    prompt = build_system_prompt(context)
    assert "author BMS circuit diagrams" in prompt
    assert "/bms/SKILL.md" in prompt
    assert "safety_rules.yaml" in prompt
    assert "Default workflow" in prompt
    assert "users never need to ask" in prompt.lower()
    assert "do **not** re-read" in prompt.lower() or "do not re-read" in prompt.lower()
    assert "templates" in prompt


def test_subagents_cover_bms_roles() -> None:
    context = AgentSessionContext(
        session_id="s1",
        cwd=Path("/tmp/ws/default"),
        workspace_mode="local",
        mode="accept_edits",
        model="mock:deterministic",
        command_timeout_seconds=120,
    )
    subagents = build_subagents(context)
    names = {s["name"] for s in subagents}
    assert names == {"explorer", "implementer", "reviewer", "test_runner"}

    implementer = next(s for s in subagents if s["name"] == "implementer")
    assert "architecture.bms.json" in implementer["system_prompt"]
    assert "safety_rules.yaml" in implementer["system_prompt"]

    reviewer = next(s for s in subagents if s["name"] == "reviewer")
    assert "safety" in reviewer["system_prompt"].lower()

    test_runner = next(s for s in subagents if s["name"] == "test_runner")
    assert "fault" in test_runner["system_prompt"].lower() or "validation" in test_runner["system_prompt"].lower()
