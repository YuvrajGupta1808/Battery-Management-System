import json
from pathlib import Path

import pytest

from agent_workbench.infra.workspace_backend import (
    WorkspaceLocalShellBackend,
    WorkspacePathError,
    is_bms_output_path,
    normalize_virtual_path,
    prepare_bms_write_content,
)
from agent_workbench.infra.workspace_seed import find_repo_bms_seed


@pytest.fixture
def repo_bms_seed() -> Path:
    seed = find_repo_bms_seed()
    if seed is None:
        pytest.skip("Repository BMS seed not available")
    return seed


def test_normalize_host_workspace_path() -> None:
    root = Path("/Users/dev/Battery-Management-System/workspaces/default")
    host_readme = str(root / "README.md")
    assert normalize_virtual_path(host_readme, root) == "/README.md"
    assert normalize_virtual_path(str(root), root) == "/"
    assert normalize_virtual_path("/README.md", root) == "/README.md"
    assert normalize_virtual_path("README.md", root) == "/README.md"


def test_workspace_backend_reads_existing_readme(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# default\n", encoding="utf-8")
    backend = WorkspaceLocalShellBackend(root_dir=tmp_path)
    host_path = str(readme)
    result = backend.read(host_path)
    assert result.error is None
    assert result.file_data is not None
    assert "# default" in result.file_data["content"]


def test_workspace_backend_lists_host_root(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# default\n", encoding="utf-8")
    backend = WorkspaceLocalShellBackend(root_dir=tmp_path)
    result = backend.ls(str(tmp_path))
    assert result.error is None
    assert any(entry["path"].endswith("README.md") for entry in result.entries)


def test_normalize_rejects_parent_repo_path() -> None:
    root = Path("/Users/dev/Battery-Management-System/workspaces/default")
    with pytest.raises(WorkspacePathError, match="outside the active workspace"):
        normalize_virtual_path("/Users/dev/Battery-Management-System", root)


def test_ls_outside_workspace_returns_error(tmp_path: Path) -> None:
    backend = WorkspaceLocalShellBackend(root_dir=tmp_path)
    result = backend.ls("/Users/dev/Battery-Management-System")
    assert result.error is not None
    assert "outside the active workspace" in result.error
    assert result.entries == []


def test_is_bms_output_path() -> None:
    assert is_bms_output_path("bms/architecture.bms.json")
    assert is_bms_output_path("/bms/safety_rules.yaml")
    assert not is_bms_output_path("bms/templates/architecture.template.bms.json")


def test_prepare_bms_write_strips_template_meta() -> None:
    payload = json.dumps({"schema_version": "1.0", "template_meta": {"purpose": "x"}, "pack": {}, "views": {}})
    _, error = prepare_bms_write_content("bms/architecture.bms.json", payload)
    assert error is not None


def test_workspace_backend_overwrites_bms_architecture(tmp_path: Path) -> None:
    bms_dir = tmp_path / "bms"
    bms_dir.mkdir()
    arch_path = bms_dir / "architecture.bms.json"
    arch_path.write_text('{"old": true}\n', encoding="utf-8")

    template = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "workspaces"
            / "default"
            / "bms"
            / "templates"
            / "architecture.template.bms.json"
        ).read_text(encoding="utf-8")
    )
    template.pop("template_meta", None)
    content = json.dumps(template, indent=2) + "\n"

    backend = WorkspaceLocalShellBackend(root_dir=tmp_path)
    result = backend.write("/bms/architecture.bms.json", content)
    assert result.error is None
    written = json.loads(arch_path.read_text(encoding="utf-8"))
    assert written["schema_version"] == "1.0"
    assert "template_meta" not in written


def test_workspace_backend_rejects_dangling_edges(tmp_path: Path) -> None:
    bms_dir = tmp_path / "bms"
    bms_dir.mkdir()
    broken = {
        "schema_version": "1.0",
        "pack": {"topology": "4s1p", "cell_count": 4, "chemistry": "NMC", "nominal_voltage_v": 14.8},
        "views": {
            "pack": {
                "nodes": [
                    {
                        "id": "cells",
                        "type": "cells",
                        "label": "Cells",
                        "x": 10,
                        "y": 10,
                        "width": 80,
                        "height": 60,
                        "pins": [{"id": "p1", "label": "B+", "side": "right"}],
                    }
                ],
                "edges": [
                    {
                        "from_node": "cells",
                        "from_pin": "p1",
                        "to_node": "missing",
                        "to_pin": "p1",
                        "signal": "PACK+",
                    }
                ],
            },
            "bms": {
                "nodes": [
                    {
                        "id": "mcu",
                        "type": "mcu",
                        "label": "MCU",
                        "x": 10,
                        "y": 10,
                        "width": 80,
                        "height": 60,
                        "pins": [],
                    }
                ],
                "edges": [],
            },
        },
    }
    backend = WorkspaceLocalShellBackend(root_dir=tmp_path)
    result = backend.write("/bms/architecture.bms.json", json.dumps(broken))
    assert result.error is not None
    assert "unknown to_node" in result.error


def test_workspace_backend_reads_full_bms_json_by_default(tmp_path: Path, repo_bms_seed: Path) -> None:
    from agent_workbench.infra.workspace_seed import seed_bms_workspace

    seed_bms_workspace(tmp_path, seed_dir=repo_bms_seed)
    arch_path = tmp_path / "bms" / "architecture.bms.json"
    total_lines = len(arch_path.read_text(encoding="utf-8").splitlines())
    assert total_lines > 100

    backend = WorkspaceLocalShellBackend(root_dir=tmp_path)
    result = backend.read("/bms/architecture.bms.json", offset=0, limit=100)
    assert result.error is None
    assert result.file_data is not None
    content = result.file_data["content"]
    if isinstance(content, list):
        content = "".join(content)
    assert content.count("\n") + 1 >= total_lines


def test_workspace_backend_blocks_non_bms_overwrite(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# keep\n", encoding="utf-8")
    backend = WorkspaceLocalShellBackend(root_dir=tmp_path)
    result = backend.write("/README.md", "# replaced\n")
    assert result.error is not None
    assert "already exists" in result.error
