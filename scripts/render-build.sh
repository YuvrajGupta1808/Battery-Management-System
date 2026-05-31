#!/usr/bin/env bash
set -o errexit

echo "==> Installing Python dependencies"
python -m pip install -U pip
pip install -e "./backend[deepagents]"

echo "==> Installing Node dependencies and building web UI"
corepack enable
corepack prepare pnpm@10.15.1 --activate
pnpm install --frozen-lockfile 2>/dev/null || pnpm install

export VITE_API_BASE_URL=""
export VITE_WORKBENCH_TOKEN="${WORKBENCH_TOKEN:-dev-local-token}"
pnpm build:web

echo "==> Build complete"
