"""Probe Tigris connectivity and optional MCP tool load."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from agent_workbench.infra.tigris_mcp import get_tigris_mcp_settings, load_tigris_mcp_bundle
from agent_workbench.infra.tigris_storage import get_tigris_settings, get_text, list_prefix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CANary Tigris probe")
    parser.add_argument("--probe", action="store_true", help="Also load Tigris MCP tools")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[4]
    load_dotenv(repo_root / ".env")

    settings = get_tigris_settings()
    print(f"Bucket: {settings.bucket}")
    print(f"Prefix: {settings.prefix}")
    print(f"Endpoint: {settings.endpoint_url}")
    print(f"Configured: {settings.configured}")

    if not settings.configured:
        print("ERROR: Tigris credentials missing", file=sys.stderr)
        return 1

    keys = list_prefix(settings, "wiki/")
    print(f"\nWiki objects ({len(keys)}):")
    for key in keys[:30]:
        print(f"  {key}")
    if len(keys) > 30:
        print(f"  ... and {len(keys) - 30} more")

    index = get_text(settings, "wiki/index.md")
    if index:
        print("\nwiki/index.md (first 400 chars):")
        print(index[:400])
    else:
        print("\nwiki/index.md not found — run: make tigris-bootstrap")

    if args.probe:
        mcp_settings = get_tigris_mcp_settings()
        bundle = load_tigris_mcp_bundle(mcp_settings)
        print(f"\nMCP configured: {bundle.configured}")
        print(f"MCP tools: {len(bundle.tools)}")
        for tool in bundle.tools:
            print(f"  - {getattr(tool, 'name', tool)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
