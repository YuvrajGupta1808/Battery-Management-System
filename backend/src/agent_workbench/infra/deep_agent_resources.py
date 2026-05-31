"""Process-wide LangGraph checkpointer and Deep Agents store (memory doc alignment)."""

from __future__ import annotations

from threading import Lock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langgraph.store.memory import InMemoryStore

_lock = Lock()
_checkpointer: Any | None = None
_store: Any | None = None


def get_checkpointer() -> Any:
    """Shared in-memory checkpointer so thread_id survives across HTTP streams."""
    global _checkpointer
    with _lock:
        if _checkpointer is None:
            from langgraph.checkpoint.memory import MemorySaver

            _checkpointer = MemorySaver()
        return _checkpointer


def get_langgraph_store() -> Any:
    """Shared store backing `/memories/`, `/skills/`, and `/policies/` StoreBackend routes."""
    global _store
    with _lock:
        if _store is None:
            from langgraph.store.memory import InMemoryStore

            store = InMemoryStore()
            _seed_org_policies(store)
            _store = store
        return _store


def _seed_org_policies(store: InMemoryStore | Any) -> None:
    from deepagents.backends.utils import create_file_data

    ns = ("workbench",)
    key = "/policies/compliance.md"
    if store.get(ns, key) is None:
        store.put(
            ns,
            key,
            create_file_data(
                """## Local workbench policies
- Do not exfiltrate secrets from .env or credential files.
- Prefer minimal diffs and explain risky commands before execution.
"""
            ),
        )


def ensure_session_store_seeded(store: Any, session_id: str, *, workspace_root: str | None = None) -> None:
    """Per-session long-term memory and skill seeds (namespaced store); idempotent."""
    from deepagents.backends.utils import create_file_data

    ns = (session_id,)
    workspace_line = (
        f"\nActive workspace root: `{workspace_root}`\n"
        if workspace_root
        else "\n"
    )

    mem_key = "/memories/WORKBENCH.md"
    if store.get(ns, mem_key) is None:
        store.put(
            ns,
            mem_key,
            create_file_data(
                f"""## Session memory
Use this file for preferences and durable facts for this conversation session.
You may update it when the user asks you to remember something.
{workspace_line}"""
            ),
        )

    skill_key = "/skills/bms-diagram-author/SKILL.md"
    workspace_hint = workspace_root or "the configured workspace root"
    if store.get(ns, skill_key) is None:
        store.put(
            ns,
            skill_key,
            create_file_data(
                f"""---
name: bms-diagram-author
description: Author BMS circuit diagrams for CANary SVG rendering.
---

# BMS Diagram Author (session hint)

Follow the main agent system prompt default workflow for every BMS design request.
Read workspace `/bms/SKILL.md` + templates once, write `/bms/architecture.bms.json` and `/bms/safety_rules.yaml`, stop.
Users supply requirements only — never ask them to repeat workflow steps.
Active workspace: `{workspace_hint}`
"""
            ),
        )

    skill_key_legacy = "/skills/workbench-hint/SKILL.md"
    if store.get(ns, skill_key_legacy) is None:
        store.put(
            ns,
            skill_key_legacy,
            create_file_data(
                f"""---
name: workbench-hint
description: Workspace scoping rules for file tools in the local agent workbench.
---

# workbench-hint

- Active workspace: `{workspace_hint}`
- Primary artifacts: `/bms/architecture.bms.json`, `/bms/safety_rules.yaml`
- Read `/bms/SKILL.md` for diagram authoring rules.
- File tools treat `/` as the workspace root, not the host filesystem.
- Use `/memories/` for durable notes that should survive future turns in this session.
"""
            ),
        )
