"""Seed CANary BMS artifacts into new workspaces."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

BMS_OUTPUT_FILES = (
    "bms/SKILL.md",
    "bms/README.md",
    "bms/schema/architecture.schema.json",
    "bms/templates/architecture.template.bms.json",
    "bms/templates/safety_rules.template.yaml",
    "bms/architecture.bms.json",
    "bms/safety_rules.yaml",
)


def find_repo_bms_seed() -> Path | None:
    """Locate committed `workspaces/default/bms` in the repository checkout."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "workspaces" / "default" / "bms"
        if (candidate / "SKILL.md").is_file() and (candidate / "schema" / "architecture.schema.json").is_file():
            return candidate
    return None


def resolve_bms_seed_dir(explicit: Path | None = None) -> Path:
    if explicit is not None:
        if not (explicit / "SKILL.md").is_file():
            raise FileNotFoundError(f"BMS seed directory is missing SKILL.md: {explicit}")
        return explicit
    found = find_repo_bms_seed()
    if found is None:
        raise FileNotFoundError(
            "CANary BMS seed files not found. Expected workspaces/default/bms in the repository checkout."
        )
    return found


def _architecture_from_template(template_path: Path) -> str:
    data = json.loads(template_path.read_text(encoding="utf-8"))
    data.pop("template_meta", None)
    return json.dumps(data, indent=2) + "\n"


def seed_bms_workspace(workspace_root: Path, *, seed_dir: Path | None = None, overwrite: bool = False) -> list[str]:
    """Copy BMS scaffolding into `workspace_root` (idempotent unless overwrite=True).

    Creates schema, templates, SKILL, starter architecture, and safety rules so agents
    can run immediately in a fresh workspace.
    """
    source = resolve_bms_seed_dir(seed_dir)
    workspace_root.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        dest = workspace_root / "bms" / rel
        if dest.exists() and not overwrite:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        created.append(f"bms/{rel.as_posix()}")

    template_path = source / "templates" / "architecture.template.bms.json"
    arch_dest = workspace_root / "bms" / "architecture.bms.json"
    if template_path.is_file() and (overwrite or not arch_dest.exists()):
        arch_dest.parent.mkdir(parents=True, exist_ok=True)
        arch_dest.write_text(_architecture_from_template(template_path), encoding="utf-8")
        rel_arch = "bms/architecture.bms.json"
        if rel_arch not in created:
            created.append(rel_arch)

    rules_template = source / "templates" / "safety_rules.template.yaml"
    rules_dest = workspace_root / "bms" / "safety_rules.yaml"
    if rules_template.is_file() and (overwrite or not rules_dest.exists()):
        rules_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(rules_template, rules_dest)
        rel_rules = "bms/safety_rules.yaml"
        if rel_rules not in created:
            created.append(rel_rules)

    return created


def bms_workspace_is_seeded(workspace_root: Path) -> bool:
    return all((workspace_root / rel).is_file() for rel in BMS_OUTPUT_FILES)
