#!/usr/bin/env bash
set -o errexit

echo "==> Installing Python dependencies"
python -m pip install -U pip
pip install -e "./backend[deepagents]"

echo "==> Installing Node dependencies and building web UI"
# Render's Python runtime has Node but a read-only corepack shim — use npx pnpm directly.
export VITE_API_BASE_URL=""
export VITE_WORKBENCH_TOKEN="${WORKBENCH_TOKEN:-dev-local-token}"
npx --yes pnpm@10.15.1 install --frozen-lockfile 2>/dev/null || npx --yes pnpm@10.15.1 install
npx --yes pnpm@10.15.1 build:web

echo "==> Build complete"
