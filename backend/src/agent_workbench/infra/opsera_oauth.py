"""Opsera MCP browser OAuth (same flow as Cursor — no manual API token)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

logger = logging.getLogger(__name__)

DEFAULT_REDIRECT_PORT = 8766
DEFAULT_REDIRECT_URI = f"http://127.0.0.1:{DEFAULT_REDIRECT_PORT}/callback"


@dataclass
class OpseraOAuthPaths:
    token_path: Path

    @classmethod
    def from_env(cls, data_dir: Path | None = None) -> OpseraOAuthPaths:
        explicit = os.getenv("WORKBENCH_OPSERA_OAUTH_PATH", "").strip()
        if explicit:
            return cls(token_path=Path(explicit).expanduser().resolve())
        root = data_dir or Path(os.getenv("WORKBENCH_DATA_DIR", ".data")).expanduser()
        return cls(token_path=(root / "opsera-oauth.json").resolve())


class FileTokenStorage:
    """Persist Opsera OAuth tokens on disk (like Cursor's saved MCP session)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _read(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    async def get_tokens(self) -> OAuthToken | None:
        raw = self._read().get("tokens")
        if not raw:
            return None
        try:
            return OAuthToken.model_validate(raw)
        except Exception:
            return None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        data = self._read()
        data["tokens"] = tokens.model_dump(mode="json")
        self._write(data)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        raw = self._read().get("client_info")
        if not raw:
            return None
        try:
            return OAuthClientInformationFull.model_validate(raw)
        except Exception:
            return None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        data = self._read()
        data["client_info"] = client_info.model_dump(mode="json")
        self._write(data)


async def _redirect_handler(authorization_url: str) -> None:
    print(f"Opening browser for Opsera sign-in…\n{authorization_url}")
    webbrowser.open(authorization_url)


async def _callback_handler(port: int = DEFAULT_REDIRECT_PORT) -> tuple[str, str | None]:
    """Local redirect listener for OAuth authorization code."""
    loop = asyncio.get_running_loop()
    result: asyncio.Future[tuple[str, str | None]] = loop.create_future()

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request_line = (await reader.readline()).decode("utf-8", errors="ignore").strip()
            if not request_line.startswith("GET "):
                writer.close()
                return
            target = request_line.split(" ", 2)[1]
            parsed = urlparse(target)
            params = parse_qs(parsed.query)
            code = (params.get("code") or [""])[0]
            state = (params.get("state") or [None])[0]
            body = (
                "<html><body><h2>Opsera connected</h2>"
                "<p>You can close this tab and return to CANary.</p></body></html>"
            ).encode()
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html; charset=utf-8\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode() + body
            writer.write(response)
            await writer.drain()
            if not result.done() and code:
                result.set_result((code, state))
        except Exception as exc:
            if not result.done():
                result.set_exception(exc)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    server = await asyncio.start_server(handle, host="127.0.0.1", port=port)
    try:
        return await asyncio.wait_for(result, timeout=300.0)
    finally:
        server.close()
        await server.wait_closed()


def create_opsera_oauth_provider(
    mcp_url: str,
    *,
    token_path: Path | None = None,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
) -> OAuthClientProvider:
    paths = OpseraOAuthPaths(token_path=token_path) if token_path else OpseraOAuthPaths.from_env()
    storage = FileTokenStorage(paths.token_path)
    port = urlparse(redirect_uri).port or DEFAULT_REDIRECT_PORT

    async def callback_handler() -> tuple[str, str | None]:
        return await _callback_handler(port=port)

    client_metadata = OAuthClientMetadata(
        redirect_uris=[redirect_uri],
        token_endpoint_auth_method="none",
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        client_name="CANary BMS Workbench",
    )
    return OAuthClientProvider(
        server_url=mcp_url,
        client_metadata=client_metadata,
        storage=storage,
        redirect_handler=_redirect_handler,
        callback_handler=callback_handler,
    )


def has_stored_opsera_oauth(token_path: Path | None = None) -> bool:
    paths = OpseraOAuthPaths(token_path=token_path) if token_path else OpseraOAuthPaths.from_env()
    if not paths.token_path.is_file():
        return False
    storage = FileTokenStorage(paths.token_path)
    tokens = storage._read().get("tokens") or {}
    return bool(tokens.get("access_token"))


async def run_opsera_browser_login(mcp_url: str, *, token_path: Path | None = None) -> Path:
    """Sign in to Opsera via browser (Google SSO). Stores tokens for the Deep Agent."""
    paths = OpseraOAuthPaths(token_path=token_path) if token_path else OpseraOAuthPaths.from_env()
    auth = create_opsera_oauth_provider(mcp_url, token_path=paths.token_path)
    async with httpx.AsyncClient(auth=auth, follow_redirects=True, timeout=120.0) as client:
        response = await client.post(
            mcp_url,
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}},
        )
        if response.status_code >= 400 and not has_stored_opsera_oauth(paths.token_path):
            raise RuntimeError(
                f"Opsera login did not complete (HTTP {response.status_code}). "
                "Complete the browser sign-in prompt and retry."
            )
    logger.info("Opsera OAuth tokens saved to %s", paths.token_path)
    print(f"Opsera OAuth tokens saved to {paths.token_path}")
    return paths.token_path
