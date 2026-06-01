"""Tigris MCP client for Deep Agents (langchain-mcp-adapters + stdio server)."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from langchain_mcp_adapters.interceptors import MCPToolCallRequest

from .tigris_storage import TigrisSettings, get_tigris_settings, mcp_env

logger = logging.getLogger(__name__)

# Tools that accept bucketName (all except list_buckets).
_TIGRIS_BUCKET_TOOLS = frozenset(
    {
        "tigris_create_bucket",
        "tigris_delete_bucket",
        "tigris_list_objects",
        "tigris_put_object",
        "tigris_put_object_from_path",
        "tigris_get_object",
        "tigris_delete_object",
        "tigris_get_signed_url_object",
        "tigris_upload_file_and_get_url",
    }
)

_bundle_lock = Lock()
_bundle_cache: TigrisMCPBundle | None = None
_bundle_cache_key: tuple[str, str, str, bool] | None = None


@dataclass(frozen=True)
class TigrisMCPSettings:
    enabled: bool
    storage: TigrisSettings

    @property
    def configured(self) -> bool:
        return self.enabled and self.storage.configured


@dataclass
class TigrisMCPBundle:
    """Tools loaded from Tigris via MultiServerMCPClient."""

    tools: list[Any] = field(default_factory=list)
    configured: bool = False
    client: Any | None = None

    @property
    def enabled(self) -> bool:
        return self.configured and len(self.tools) > 0


def get_tigris_mcp_settings() -> TigrisMCPSettings:
    storage = get_tigris_settings()
    return TigrisMCPSettings(enabled=storage.enabled, storage=storage)


def _npx_command() -> str:
    return os.getenv("TIGRIS_MCP_NPX", "npx")


def _tigris_connection(settings: TigrisMCPSettings) -> dict[str, Any]:
    """stdio MCP connection config per LangChain docs."""
    env = {**os.environ, **mcp_env(settings.storage)}
    return {
        "tigris": {
            "transport": "stdio",
            "command": _npx_command(),
            "args": ["-y", "@tigrisdata/tigris-mcp-server", "run"],
            "env": env,
        }
    }


def normalize_tigris_object_key(storage: TigrisSettings, key: str | None) -> str | None:
    """Ensure wiki/raw paths include the configured Tigris prefix."""
    if not key:
        return key
    rel = key.lstrip("/")
    prefix = storage.prefix.rstrip("/")
    if prefix and not rel.startswith(f"{prefix}/"):
        return storage.object_key(rel)
    return rel


def apply_tigris_tool_defaults(storage: TigrisSettings, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Inject bucketName and prefix paths for Tigris MCP tools."""
    out = dict(args or {})

    if out.get("bucket") and not out.get("bucketName"):
        out["bucketName"] = out.pop("bucket")

    if tool_name in _TIGRIS_BUCKET_TOOLS and not out.get("bucketName"):
        out["bucketName"] = storage.bucket

    if "key" in out:
        out["key"] = normalize_tigris_object_key(storage, out.get("key"))

    if "prefix" in out and out["prefix"]:
        out["prefix"] = normalize_tigris_object_key(storage, out.get("prefix"))

    return out


def make_tigris_defaults_interceptor(settings: TigrisMCPSettings):
    """Inject CANary Tigris defaults (bucketName, object key prefix)."""

    async def inject_defaults(request: MCPToolCallRequest, handler):
        args = apply_tigris_tool_defaults(settings.storage, request.name, dict(request.args or {}))
        if args != request.args:
            request = request.override(args=args)
        return await handler(request)

    return inject_defaults


async def _tigris_logging_interceptor(request: MCPToolCallRequest, handler):
    logger.info("Tigris MCP tool call: %s", request.name)
    try:
        result = await handler(request)
        logger.info("Tigris MCP tool completed: %s", request.name)
        return result
    except Exception:
        logger.exception("Tigris MCP tool failed: %s", request.name)
        raise


def create_tigris_mcp_client(settings: TigrisMCPSettings) -> Any:
    """Build a MultiServerMCPClient for Tigris (stateless sessions per tool call)."""
    from langchain_mcp_adapters.client import MultiServerMCPClient

    interceptors = [_tigris_logging_interceptor, make_tigris_defaults_interceptor(settings)]

    return MultiServerMCPClient(
        _tigris_connection(settings),
        tool_interceptors=interceptors,
    )


def format_tigris_auth_notice(settings: TigrisMCPSettings) -> str:
    if settings.configured:
        return (
            f"Tigris MCP **online** — bucket `{settings.storage.bucket}`, "
            f"prefix `{settings.storage.prefix}/`."
        )
    return (
        "Tigris MCP **offline** — set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in `.env` "
        "(from https://storage.new/accesskey)."
    )


def format_tigris_system_addon(settings: TigrisMCPSettings, *, mcp_connected: bool) -> str:
    if not settings.enabled:
        return ""
    bucket = settings.storage.bucket
    prefix = settings.storage.prefix
    wiki_index = f"{prefix}/wiki/index.md"
    tools_line = (
        "MCP tools: `tigris_list_objects`, `tigris_get_object`, `tigris_put_object`, "
        "`tigris_get_signed_url_object`, etc. Use **`bucketName`** (not `bucket`) — "
        f"defaults to `{bucket}`. Object **`key`** must include prefix, e.g. `{wiki_index}`."
        if mcp_connected
        else "Tigris MCP tools **offline** until credentials are configured."
    )
    auto_policy = (
        "**Wiki-first policy (mandatory when MCP is online):** Before any BMS answer, comparison, "
        "threshold choice, or schematic decision, fetch the wiki index and read the pages you need. "
        "Users never need to say \"read Tigris\" or \"check the wiki\" — you do this automatically.\n\n"
        f"**Start here every time:** `tigris_get_object` key=`{wiki_index}` "
        f"(bucketName defaults to `{bucket}`).\n"
        "**Then follow links** to `wiki/entities/` (parts), `wiki/concepts/` (protection, topology, thermal), "
        "`wiki/sources/` (datasheets, rtrvr extractions).\n"
        "**Triggers (non-exhaustive):** part A vs B, chemistry, series count, OVP/UVP/OCP, balancing, "
        "thermal limits, scope, standards, \"which IC\", \"should I use\", design rationale.\n"
        "**Q&A only:** wiki → answer → stop (no file writes).\n"
        "**Design request:** wiki + local templates → write `architecture.bms.json` + `safety_rules.yaml`."
        if mcp_connected
        else "Configure Tigris in `.env` and restart the backend."
    )
    ingest = (
        f"- **Ingest:** PDFs → `{prefix}/raw/`; compiled pages → `{prefix}/wiki/`; update `index.md` + `log.md`.\n"
        f"- **Never** store wiki markdown locally — remote only on Tigris.\n"
        f"- Local workspace: diagram files only (`architecture.bms.json`, `safety_rules.yaml`)."
        if mcp_connected
        else ""
    )
    return f"""

## Tigris remote wiki (Karpathy LLM Wiki pattern)

{format_tigris_auth_notice(settings)}

{tools_line}

- **Bucket:** `{bucket}` (`bucketName` in tool args)
- **Prefix:** `{prefix}/`
- **Wiki index key:** `{wiki_index}`
- **Schema:** read `{prefix}/schema/WIKI.md` on Tigris; local pointer `/bms/WIKI.md`
- Skill: `/skills/bms-wiki/SKILL.md`

{auto_policy}
{ingest}"""


async def _load_tigris_bundle_async(settings: TigrisMCPSettings) -> TigrisMCPBundle:
    if not settings.configured:
        return TigrisMCPBundle(configured=False)

    if shutil.which(_npx_command()) is None:
        logger.warning("npx not found; Tigris MCP disabled")
        return TigrisMCPBundle(configured=False)

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        logger.warning("langchain-mcp-adapters not installed; Tigris MCP disabled")
        return TigrisMCPBundle(configured=False)

    client: MultiServerMCPClient = create_tigris_mcp_client(settings)
    tools = await client.get_tools(server_name="tigris")
    return TigrisMCPBundle(
        tools=make_tools_sync_compatible(list(tools)),
        configured=True,
        client=client,
    )


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_tools_sync_compatible(tools: list[Any]) -> list[Any]:
    """langchain-mcp-adapters tools are async-only; Deep Agents stream invokes sync `func`."""
    wrapped: list[Any] = []
    for tool in tools:
        coroutine = getattr(tool, "coroutine", None)
        if coroutine is None or getattr(tool, "func", None) is not None:
            wrapped.append(tool)
            continue

        def _sync(*, _coro=coroutine, **kwargs: Any) -> Any:
            return _run_async(_coro(**kwargs))

        wrapped.append(tool.model_copy(update={"func": _sync}))
    return wrapped


def load_tigris_mcp_bundle(settings: TigrisMCPSettings) -> TigrisMCPBundle:
    """Load Tigris MCP tools (cached per bucket, prefix, endpoint)."""
    global _bundle_cache, _bundle_cache_key
    fallback = TigrisMCPBundle(configured=False)

    if not settings.enabled or not settings.configured:
        return fallback

    cache_key = (
        settings.storage.bucket,
        settings.storage.prefix,
        settings.storage.endpoint_url,
        settings.enabled,
    )
    with _bundle_lock:
        if _bundle_cache is not None and _bundle_cache_key == cache_key:
            return _bundle_cache

    try:
        bundle = _run_async(_load_tigris_bundle_async(settings))
    except Exception:
        logger.exception("Failed to load Tigris MCP bundle")
        bundle = fallback

    with _bundle_lock:
        _bundle_cache = bundle
        _bundle_cache_key = cache_key
    return bundle
