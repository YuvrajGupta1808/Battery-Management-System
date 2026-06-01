.PHONY: dev dev-backend dev-web test test-backend test-web build-web opsera-login opsera-probe tigris-bootstrap tigris-probe tigris-ls

dev:
	pnpm dev

dev-backend:
	PYTHONPATH=backend/src .venv/bin/python -m uvicorn agent_workbench.main:app --host 127.0.0.1 --port 8787 --reload

dev-web:
	pnpm --dir apps/web dev --host 127.0.0.1 --port 5175 --strictPort

test: test-backend test-web

test-backend:
	PYTHONPATH=backend/src .venv/bin/python -m pytest backend/tests

test-web:
	pnpm --dir apps/web test

build-web:
	pnpm --dir apps/web build

opsera-login:
	PYTHONPATH=backend/src .venv/bin/python -m agent_workbench.scripts.opsera_login

opsera-probe:
	PYTHONPATH=backend/src .venv/bin/python -m agent_workbench.scripts.opsera_probe --workspace workspaces/default --probe

opsera-list:
	PYTHONPATH=backend/src .venv/bin/python -m agent_workbench.scripts.opsera_probe --workspace workspaces/default

tigris-bootstrap:
	PYTHONPATH=backend/src .venv/bin/python -m agent_workbench.scripts.tigris_bootstrap

tigris-probe:
	PYTHONPATH=backend/src .venv/bin/python -m agent_workbench.scripts.tigris_probe --probe

tigris-ls:
	PYTHONPATH=backend/src .venv/bin/python -m agent_workbench.scripts.tigris_bootstrap --list

tigris-enrich:
	PYTHONPATH=backend/src .venv/bin/python -m agent_workbench.scripts.tigris_enrich --report

rtrvr-sync:
	PYTHONPATH=backend/src .venv/bin/python -m agent_workbench.scripts.rtrvr_sync --verify

rtrvr-sync-offline:
	PYTHONPATH=backend/src .venv/bin/python -m agent_workbench.scripts.rtrvr_sync --offline --verify
