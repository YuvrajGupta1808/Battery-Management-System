import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_workbench.api import create_app
from agent_workbench.core.config import get_settings
from agent_workbench.core.dependencies import get_store, get_workspace_manager

FIXTURE = Path(__file__).parent / "fixtures" / "bms" / "architecture.bms.json"


def client_for(tmp_path: Path, monkeypatch) -> TestClient:
    workspace_root = tmp_path / "workspaces"
    monkeypatch.setenv("WORKBENCH_TOKEN", "test-token")
    monkeypatch.setenv("WORKBENCH_WORKSPACE_ROOT", str(workspace_root))
    monkeypatch.setenv("WORKBENCH_ALLOWED_ROOTS", str(workspace_root))
    monkeypatch.setenv("WORKBENCH_DATA_DIR", str(tmp_path / ".data"))
    monkeypatch.setenv("WORKBENCH_DEFAULT_MODEL", "mock:deterministic")
    get_settings.cache_clear()
    get_store.cache_clear()
    get_workspace_manager.cache_clear()
    return TestClient(create_app())


def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def create_session(client: TestClient) -> dict:
    response = client.post(
        "/api/sessions",
        headers=auth_headers(),
        json={"workspace": "default", "workspaceMode": "local", "mode": "accept_everything", "model": "mock:deterministic"},
    )
    assert response.status_code == 200
    return response.json()


def test_apply_valid_bms_architecture(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "workspaces" / "default").mkdir(parents=True)
    client = client_for(tmp_path, monkeypatch)
    session = create_session(client)
    content = FIXTURE.read_text(encoding="utf-8")

    response = client.post(
        f"/api/sessions/{session['id']}/files/apply",
        headers=auth_headers(),
        json={"path": "bms/architecture.bms.json", "content": content},
    )
    assert response.status_code == 200
    assert response.json()["path"] == "bms/architecture.bms.json"

    read_back = client.get(
        f"/api/sessions/{session['id']}/files/content",
        headers=auth_headers(),
        params={"path": "bms/architecture.bms.json"},
    )
    assert read_back.status_code == 200
    parsed = json.loads(read_back.json()["content"])
    assert parsed["pack"]["topology"] == "4s1p"


def test_apply_invalid_bms_architecture_rejected(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "workspaces" / "default").mkdir(parents=True)
    client = client_for(tmp_path, monkeypatch)
    session = create_session(client)

    response = client.post(
        f"/api/sessions/{session['id']}/files/apply",
        headers=auth_headers(),
        json={"path": "bms/architecture.bms.json", "content": "{not json"},
    )
    assert response.status_code == 422
    assert "Invalid JSON" in response.json()["detail"]


def test_apply_valid_safety_rules(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "workspaces" / "default").mkdir(parents=True)
    client = client_for(tmp_path, monkeypatch)
    session = create_session(client)
    content = """\
- id: thermal_fan_on
  condition: "pack_temp_c > 80"
  action: "cooling.fan = ON"
  component: mcu
"""

    response = client.post(
        f"/api/sessions/{session['id']}/files/apply",
        headers=auth_headers(),
        json={"path": "bms/safety_rules.yaml", "content": content},
    )
    assert response.status_code == 200


def test_apply_invalid_safety_rules_rejected(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "workspaces" / "default").mkdir(parents=True)
    client = client_for(tmp_path, monkeypatch)
    session = create_session(client)

    response = client.post(
        f"/api/sessions/{session['id']}/files/apply",
        headers=auth_headers(),
        json={"path": "bms/safety_rules.yaml", "content": "- id: incomplete\n"},
    )
    assert response.status_code == 422


def test_apply_non_bms_file_unvalidated(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "workspaces" / "default").mkdir(parents=True)
    client = client_for(tmp_path, monkeypatch)
    session = create_session(client)

    response = client.post(
        f"/api/sessions/{session['id']}/files/apply",
        headers=auth_headers(),
        json={"path": "notes.txt", "content": "arbitrary content {not json"},
    )
    assert response.status_code == 200


def test_bms_files_appear_in_tree(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "workspaces" / "default").mkdir(parents=True)
    client = client_for(tmp_path, monkeypatch)
    session = create_session(client)

    client.post(
        f"/api/sessions/{session['id']}/files/apply",
        headers=auth_headers(),
        json={"path": "bms/architecture.bms.json", "content": FIXTURE.read_text(encoding="utf-8")},
    )

    tree = client.get(f"/api/sessions/{session['id']}/files/tree", headers=auth_headers()).json()

    def collect_paths(node: dict) -> list[str]:
        paths = [node["path"]] if node.get("path") else []
        for child in node.get("children") or []:
            paths.extend(collect_paths(child))
        return paths

    all_paths = collect_paths(tree)
    assert "bms/architecture.bms.json" in all_paths


def test_apply_architecture_then_update_preserves_validation(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "workspaces" / "default").mkdir(parents=True)
    client = client_for(tmp_path, monkeypatch)
    session = create_session(client)
    content = FIXTURE.read_text(encoding="utf-8")

    client.post(
        f"/api/sessions/{session['id']}/files/apply",
        headers=auth_headers(),
        json={"path": "bms/architecture.bms.json", "content": content},
    )

    bad_update = json.loads(content)
    bad_update["views"]["bms"]["edges"] = [
        {"from_node": "mcu", "from_pin": "bad_pin", "to_node": "can", "to_pin": "mcu", "signal": "X"}
    ]

    response = client.post(
        f"/api/sessions/{session['id']}/files/apply",
        headers=auth_headers(),
        json={"path": "bms/architecture.bms.json", "content": json.dumps(bad_update)},
    )
    assert response.status_code == 422
    assert "unknown pin" in response.json()["detail"]


@pytest.mark.parametrize("path_suffix", ["architecture.bms.json", "custom-pack.bms.json"])
def test_bms_json_path_variants(tmp_path: Path, monkeypatch, path_suffix: str) -> None:
    (tmp_path / "workspaces" / "default").mkdir(parents=True)
    client = client_for(tmp_path, monkeypatch)
    session = create_session(client)
    content = FIXTURE.read_text(encoding="utf-8")

    response = client.post(
        f"/api/sessions/{session['id']}/files/apply",
        headers=auth_headers(),
        json={"path": f"bms/{path_suffix}", "content": content},
    )
    assert response.status_code == 200
