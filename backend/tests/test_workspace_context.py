from pathlib import Path

from agent_workbench.infra.workspace_context import build_workspace_context_message, list_workspace_files


def test_list_workspace_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# default\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    files = list_workspace_files(tmp_path)
    assert "README.md" in files
    assert "src/main.py" in files


def test_build_workspace_context_message(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# default\n", encoding="utf-8")
    message = build_workspace_context_message(tmp_path)
    assert str(tmp_path.resolve()) in message
    assert "/README.md" in message
    assert "entire project scope" in message
    assert "write product documentation directly" in message


def test_build_workspace_context_includes_bms_hint(tmp_path: Path) -> None:
    (tmp_path / "bms").mkdir()
    (tmp_path / "bms" / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    message = build_workspace_context_message(tmp_path)
    assert "CANary BMS" in message
    assert "requirements only" in message
