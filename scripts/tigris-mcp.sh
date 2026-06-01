#!/usr/bin/env bash
# Launch Tigris MCP server with credentials from repo .env (no secrets in mcp.json).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
export AWS_ENDPOINT_URL_S3="${AWS_ENDPOINT_URL_S3:-${AWS_ENDPOINT_URL:-https://t3.storage.dev}}"
export AWS_REGION="${AWS_REGION:-auto}"
exec npx -y @tigrisdata/tigris-mcp-server run
