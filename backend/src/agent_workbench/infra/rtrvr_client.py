"""Retriever AI (rtrvr.ai) cloud agent + scrape client."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RtrvrSettings:
    enabled: bool
    api_key: str | None
    base_url: str
    timeout_seconds: int

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.api_key)


def get_rtrvr_settings() -> RtrvrSettings:
    key = (
        os.getenv("RTRVR_API_KEY")
        or os.getenv("ITE_RTRVR_API_KEY")
        or os.getenv("RETRIEVER_API_KEY")
    )
    enabled_raw = os.getenv("WORKBENCH_RTRVR_ENABLED", "true").strip().lower()
    return RtrvrSettings(
        enabled=enabled_raw not in {"0", "false", "no", "off"},
        api_key=key,
        base_url=os.getenv("RTRVR_API_URL", "https://api.rtrvr.ai").rstrip("/"),
        timeout_seconds=int(os.getenv("RTRVR_TIMEOUT_SECONDS", "240")),
    )


def _request(
    settings: RtrvrSettings,
    path: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if not settings.configured:
        raise RuntimeError("rtrvr.ai not configured. Set RTRVR_API_KEY in .env")
    url = f"{settings.base_url}{path}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=settings.timeout_seconds) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"rtrvr.ai HTTP {exc.code}: {detail[:500]}") from exc


def agent_run(
    settings: RtrvrSettings,
    *,
    input_text: str,
    urls: list[str] | None = None,
    verbosity: str = "final",
) -> dict[str, Any]:
    """POST /agent — browse URLs and return structured or text result."""
    payload: dict[str, Any] = {
        "input": input_text,
        "response": {"verbosity": verbosity},
    }
    if urls:
        payload["urls"] = urls
    return _request(settings, "/agent", payload)


def scrape_run(settings: RtrvrSettings, *, urls: list[str]) -> dict[str, Any]:
    """POST /scrape — fast page tree extraction."""
    return _request(settings, "/scrape", {"urls": urls})


def extract_result_text(response: dict[str, Any]) -> str:
    """Normalize agent/scrape response to markdown-friendly text."""
    if not response.get("success"):
        return f"rtrvr error: {response.get('status', 'unknown')}"

    result = response.get("result") or {}
    if isinstance(result.get("json"), dict):
        return "```json\n" + json.dumps(result["json"], indent=2) + "\n```"
    if isinstance(result.get("text"), str) and result["text"].strip():
        return result["text"].strip()

    parts: list[str] = []
    for block in response.get("output") or []:
        if block.get("type") == "text" and block.get("text"):
            parts.append(str(block["text"]).strip())
        elif block.get("type") == "json" and block.get("data"):
            parts.append("```json\n" + json.dumps(block["data"], indent=2) + "\n```")
    return "\n\n".join(parts) if parts else json.dumps(response, indent=2)[:8000]
