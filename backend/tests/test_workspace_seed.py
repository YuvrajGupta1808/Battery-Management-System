from pathlib import Path

import pytest

from agent_workbench.infra.workspace_seed import (
    BMS_OUTPUT_FILES,
    bms_workspace_is_seeded,
    find_repo_bms_seed,
    seed_bms_workspace,
)


@pytest.fixture
def repo_bms_seed() -> Path:
    seed = find_repo_bms_seed()
    if seed is None:
        pytest.skip("Repository BMS seed not available")
    return seed


def test_find_repo_bms_seed() -> None:
    seed = find_repo_bms_seed()
    assert seed is not None
    assert (seed / "SKILL.md").is_file()
    assert (seed / "schema" / "architecture.schema.json").is_file()


def test_seed_bms_workspace_creates_required_files(tmp_path: Path, repo_bms_seed: Path) -> None:
    created = seed_bms_workspace(tmp_path, seed_dir=repo_bms_seed)
    assert created
    assert bms_workspace_is_seeded(tmp_path)
    for rel in BMS_OUTPUT_FILES:
        assert (tmp_path / rel).is_file(), rel

    arch = (tmp_path / "bms" / "architecture.bms.json").read_text(encoding="utf-8")
    assert "template_meta" not in arch
    assert '"schema_version": "1.0"' in arch

    rules = (tmp_path / "bms" / "safety_rules.yaml").read_text(encoding="utf-8")
    assert "- id:" in rules


def test_seed_bms_workspace_is_idempotent(tmp_path: Path, repo_bms_seed: Path) -> None:
    seed_bms_workspace(tmp_path, seed_dir=repo_bms_seed)
    first_arch = (tmp_path / "bms" / "architecture.bms.json").read_text(encoding="utf-8")
    seed_bms_workspace(tmp_path, seed_dir=repo_bms_seed)
    second_arch = (tmp_path / "bms" / "architecture.bms.json").read_text(encoding="utf-8")
    assert first_arch == second_arch
