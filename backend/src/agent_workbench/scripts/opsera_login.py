"""One-time browser login for Opsera MCP (Deep Agent workbench)."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

from agent_workbench.infra.opsera_oauth import run_opsera_browser_login


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Sign in to Opsera via browser for CANary Deep Agent MCP tools.",
    )
    parser.add_argument(
        "--url",
        default=os.getenv("OPSERA_MCP_URL", "https://agent.opsera.ai/mcp"),
        help="Opsera MCP endpoint (default: OPSERA_MCP_URL or agent.opsera.ai)",
    )
    args = parser.parse_args()

    print(
        "This opens your browser for Opsera sign-in (Google SSO), "
        "the same way Cursor MCP connects without an API token."
    )
    try:
        path = asyncio.run(run_opsera_browser_login(args.url))
    except Exception as exc:
        print(f"Opsera login failed: {exc}", file=sys.stderr)
        return 1
    print(f"Done. Restart the CANary backend if it is already running.\nTokens: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
