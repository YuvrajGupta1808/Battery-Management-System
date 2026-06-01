"""Tests for Tigris storage settings."""

from __future__ import annotations

import pytest

from agent_workbench.infra.tigris_storage import TigrisSettings, get_tigris_settings


def test_tigris_settings_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("TIGRIS_STORAGE_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("TIGRIS_STORAGE_SECRET_ACCESS_KEY", raising=False)
    settings = get_tigris_settings()
    assert isinstance(settings, TigrisSettings)
    assert not settings.configured


def test_object_key_with_prefix() -> None:
    settings = TigrisSettings(
        enabled=True,
        bucket="canary-bms-knowledge",
        prefix="dev/default",
        endpoint_url="https://t3.storage.dev",
        access_key_id="tid_x",
        secret_access_key="tsec_y",
        region="auto",
    )
    assert settings.object_key("wiki/index.md") == "dev/default/wiki/index.md"


def test_bms_wiki_schema_exists() -> None:
    from pathlib import Path

    wiki = Path(__file__).resolve().parents[2] / "workspaces/default/bms/WIKI.md"
    if not wiki.is_file():
        pytest.skip("WIKI.md not in repo")
    text = wiki.read_text(encoding="utf-8")
    assert "Tigris" in text
    assert "index.md" in text
