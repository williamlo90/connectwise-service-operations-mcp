# Local setup and quick start

This is the current local/simulator release: FastAPI, PostgreSQL, a PSA HTTP simulator, TypeScript CLI/stdio MCP, optional AI, scheduled sync and a local alert inbox. The minimal human review page is served by the API; the CLI and stdio MCP handle preparation and execution. It does not contact a real ConnectWise tenant.

## Requirements

Git, Python 3.10+ for helper scripts, Docker with Linux containers and Compose v2+. On Windows, start Docker Desktop with WSL2 and verify `docker info`. Initial dependency/image downloads require network access. The tested workstation has 16 GiB RAM; the Docker engine sees about 7.61 GiB. The core containers have explicit memory/CPU limits; allow additional headroom for builds and other projects. Ollama adds a 1.5 GiB container cap when selected.

Run commands from the project root. The default project is `cw-ops-local`, API is loopback-only port 8030, and PostgreSQL/simulator have no published ports. Use only one persistent checkout with this default project name. Separate clones require distinct Compose project names and ports; directory names alone do not isolate this stack.

## First start

```sh
python scripts/setup_local.py
docker compose -f compose.yaml -f compose.ops.yaml --profile tools --profile automation build
docker compose -f compose.yaml -f compose.ops.yaml up -d --wait api
docker compose -f compose.yaml -f compose.ops.yaml run --rm seed
docker compose -f compose.yaml -f compose.ops.yaml run --rm client --smoke
docker compose -f compose.yaml -f compose.ops.yaml --profile automation up -d --wait worker monitor
```

Setup creates unique passwords in ignored `.env` without printing or overwriting existing values. Keep that file private. `.env.example` is a template, not a credential. Changing `.env` does not rotate a password already stored in PostgreSQL. Seed is idempotent: rerunning it preserves users, records and settings. Hosted AI remains disabled in a fresh setup; no provider key is needed for these steps.

Human review page: **http://localhost:8030/**. Readiness endpoint: `http://127.0.0.1:8030/health/ready`. Change `API_PORT` in `.env` if necessary. Read `local/monitor/metrics.json` and `alerts.jsonl` for local monitoring; the worker needs a few seconds to perform its first sync.

## First task

```sh
docker compose run --rm client --mcp --tools
docker compose run --rm client --mcp --workflow context A-100
docker compose run --rm client --mcp --workflow note A-100
```

Follow [USER-GUIDE.md](USER-GUIDE.md) to review, approve as a separate identity, execute and verify. AI is optional; configure Ollama/OpenAI only through [the assistant guide](PHASE-3-ASSISTANT.md). The default provider is local Ollama; starting the core stack alone does not start that model runtime.

## Synthetic identities

All seven demo accounts use the generated `DEMO_PASSWORD`. This is a synthetic seed convenience, not production identity provisioning.

| Identity | Role and allowed use |
| --- | --- |
| op-a / op-b | Scoped reads and preparation/execution in tenant A / B |
| approver-a / approver-b | Scoped reads and approval of another user's proposal |
| admin-a | Tenant A configuration, scheduled sync and review recovery; no business approval |
| auditor-a | Tenant A sanitized audit trail; no writes |
| worker-a | Granted tenant A summary skill only; no note/time/write privilege |

Pass `-e DEMO_USERNAME=op-b` to `docker compose run` for the tenant B operator and use `B-100`. Requests for another tenant's ticket return 404; changing headers cannot change a user's scope. Sessions expire after 30 minutes and normal CLI exit logs out. Never pass passwords/tokens in command arguments or URLs.

## Stop, restart and remove

```sh
docker compose -f compose.yaml -f compose.ops.yaml --profile automation stop
docker compose -f compose.yaml -f compose.ops.yaml --profile automation up -d --wait api worker monitor
```

If using Ollama, include `-f compose.ai.yaml` consistently in lifecycle commands and start `ollama` explicitly when needed. `down` using the same Compose files removes only this project's containers/network and retains named database/model volumes. Use `down --volumes` only when intentionally erasing that named project's data; take a backup first. Never use global prune to reset this project. The bind-mounted ignored `local/monitor` folder remains after container removal.

## Reproduce checks

```sh
python scripts/test_local.py
python scripts/record_demo.py
python scripts/qualify_local.py
```

Run these serially. Each uses its own disposable project and removes it on completion. Regression and demo do not need model keys. Qualification additionally uses the previously installed pinned Ollama/model volume for OOM testing. Current regression evidence is `docs/evidence/workspace-regression.json`; quality and qualification evidence retain their original scope. To replay the frozen AI evaluation, use the `phase-6` checkpoint; later file changes intentionally fail its frozen-hash guard.

`python scripts/check_installation.py` tests the **committed HEAD** in a fresh extracted Git snapshot with generated credentials, fresh named volumes and a dynamic loopback port. It uses the existing Docker download/build cache; this is not a newly provisioned physical machine. Uncommitted changes are excluded.

## Help and limits

401: log in again and check local credentials. 403: the role cannot perform that action. 404 also hides inaccessible records. 409: review the conflict/stale source; do not force an old approval. 429: wait for the login window or relevant rate limit. 503 readiness: inspect `docker compose logs migrate api` and use the [operations runbook](OPERATIONS-RUNBOOK.md).

Connected mode and production environment configuration are not enabled. Real ConnectWise permissions/contract checks remain Phase 8A. Cloud account lifecycle, TLS, separate migration/runtime database roles and remote access controls must be implemented and tested before Phase 9 deployment.
