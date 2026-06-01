"""Tests for Tigris MCP defaults (langchain-mcp-adapters interceptors)."""

from __future__ import annotations

import pytest

from agent_workbench.infra.tigris_mcp import (
    apply_tigris_tool_defaults,
    normalize_tigris_object_key,
)
from agent_workbench.infra.tigris_storage import TigrisSettings


@pytest.fixture
def storage() -> TigrisSettings:
    return TigrisSettings(
        enabled=True,
        bucket="canary-bms-knowledge",
        prefix="dev/default",
        endpoint_url="https://t3.storage.dev",
        access_key_id="tid_test",
        secret_access_key="tsec_test",
        region="auto",
    )


def test_normalize_object_key_adds_prefix(storage: TigrisSettings) -> None:
    assert normalize_tigris_object_key(storage, "wiki/index.md") == "dev/default/wiki/index.md"
    assert normalize_tigris_object_key(storage, "dev/default/wiki/index.md") == "dev/default/wiki/index.md"


def test_apply_defaults_injects_bucket_name(storage: TigrisSettings) -> None:
    args = apply_tigris_tool_defaults(storage, "tigris_get_object", {"key": "wiki/index.md"})
    assert args["bucketName"] == "canary-bms-knowledge"
    assert args["key"] == "dev/default/wiki/index.md"


def test_apply_defaults_maps_bucket_alias(storage: TigrisSettings) -> None:
    args = apply_tigris_tool_defaults(
        storage,
        "tigris_list_objects",
        {"bucket": "other-bucket", "prefix": "wiki/"},
    )
    assert args["bucketName"] == "other-bucket"
    assert "bucket" not in args
    assert args["prefix"] == "dev/default/wiki/"


def test_system_addon_wiki_first_policy() -> None:
    from agent_workbench.infra.tigris_mcp import TigrisMCPSettings, format_tigris_system_addon
    from agent_workbench.infra.tigris_storage import TigrisSettings

    settings = TigrisMCPSettings(
        enabled=True,
        storage=TigrisSettings(
            enabled=True,
            bucket="canary-bms-knowledge",
            prefix="dev/default",
            endpoint_url="https://t3.storage.dev",
            access_key_id="x",
            secret_access_key="y",
            region="auto",
        ),
    )
    text = format_tigris_system_addon(settings, mcp_connected=True)
    assert "Wiki-first policy" in text
    assert 'never need to say "read Tigris"' in text
