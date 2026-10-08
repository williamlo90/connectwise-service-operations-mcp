# Local setup and use — Phase 2

This release implements deterministic service-ticket workflows against a local HTTP simulator. It does not call ConnectWise or an AI provider. The reference client is a TypeScript command-line application, not a browser UI or an MCP client yet.

## Requirements

- Git, Python 3.10+ (for setup/test scripts), Docker with Linux containers and Docker Compose v2+.
- On Windows, start Docker Desktop with its WSL2 Linux engine. Verify `docker info` succeeds.
- Initial image/package downloads require internet access. Runtime data stays in this local stack.
- Run all commands from this project's root directory. Other project stacks can remain running; the default API port is 8030 and the database has no published port.

## First start

```sh
python scripts/setup_local.py
docker compose --profile tools build
docker compose up -d --wait api
docker compose run --rm seed
docker compose run --rm client --smoke
```

The setup script creates unique passwords in the ignored `.env` file without printing them. Re-running it preserves existing credentials and adds a missing simulator secret. Restrict local access to this file; it is not a cloud secret store. `.env.example` contains placeholders only. Changing the database password in `.env` does not rotate an existing database's password. Seed is idempotent and does not overwrite existing users or tickets.

Readiness: `http://127.0.0.1:8030/health/ready`. This is a JSON API; the root URL is not a website. `API_PORT` in `.env` can select another unused local port. Configuration currently accepts only `synthetic` mode; connected mode is intentionally unavailable until the adapter phases.

## Daily use

```sh
docker compose run --rm client
```

The client logs in as `op-a` using the local demo password passed by Compose, shows accessible tickets, and accepts `A-100`, `list`, or `quit`. It logs out when closed normally. Sessions expire after 30 minutes. Passwords and bearer tokens are not displayed or saved by the client.

For tenant B:

```sh
docker compose run --rm -e DEMO_USERNAME=op-b client
```

Tenant B sees `B-100`; attempting `A-100` returns 404. Tenant A sees only `A-100`, not its other company/board fixtures `A-101` and `A-102`. The same checks apply to direct HTTP requests; client headers cannot choose another tenant or role.

For the note/time proposal → approval → execute → verify workflow, follow [PHASE-2-WORKFLOW.md](PHASE-2-WORKFLOW.md).

## Demo identities

All seven synthetic accounts use the generated `DEMO_PASSWORD`. This shared password is a local seed convenience, not a production account-management design.

| Username | Role / tenant | Available access |
| --- | --- | --- |
| op-a | Operator / A | `/me`, scoped ticket list/detail |
| approver-a | Approver / A | Scoped reads, draft preparation and approval of another user’s proposal |
| op-b | Operator / B | `/me`, B-scoped ticket list/detail |
| approver-b | Approver / B | B-scoped reads and separate-user approval |
| admin-a | Administrator / A | `/me`, sanitized `/admin/config` and sync checkpoints; no ticket/approval privilege by default |
| auditor-a | Auditor / A | `/me`, sanitized `/audit` for A |
| worker-a | Worker / A | `/me` only; no assigned tools or ticket scopes yet |

The interactive CLI is intended for operator/approver ticket reads. It reports 403 when used with a role that cannot read tickets. API login is `POST /auth/login` with JSON `username` and `password`. Authenticated requests use `Authorization: Bearer <token>`; `POST /auth/logout` revokes that token. Never place credentials in a URL or command-line argument.

## Automated checks and isolated reset

```sh
python scripts/test_local.py
```

This builds a separate `cw-ops-test` Compose project, initializes a fresh PostgreSQL database in temporary memory, runs HTTP acceptance plus the compiled TypeScript client, checks API logs for secret leakage, and removes only that test stack in a `finally` block. It does not use `.env`, publish ports, or reset the persistent local database. Run one instance of this test script at a time. Result and source fingerprints are recorded in `docs/evidence/phase-2-run.json`.

For a reset after a forcibly interrupted test:

```sh
docker compose --env-file .env.example -p cw-ops-test -f compose.test.yaml down --remove-orphans
```

## Stop and restart

```sh
docker compose stop
docker compose up -d --wait api
```

To remove this project's containers and network while retaining database data:

```sh
docker compose down
```

Only if you intend to erase this project's synthetic data permanently, use `docker compose down --volumes`. That removes the `cw-ops-local` database volume; the next start requires seeding again. Do not use global Docker prune commands.

## Troubleshooting and limits

- Docker engine unavailable: start Docker Desktop/Linux engine, then rerun `docker info`.
- Port in use: change `API_PORT`, then recreate the API container.
- 401: check username/password, expiry or logout; log in again. Five failed logins for one username within five minutes return 429 until the window expires.
- 403: current role cannot perform that operation. 404 on a ticket also covers out-of-scope records.
- 503 readiness/API: inspect `docker compose ps` and `docker compose logs migrate api`. Apply migrations with `docker compose run --rm migrate`; applied SQL files are checksum-verified and must not be edited after use.
- Configuration errors intentionally hide raw input values. API logs contain generated correlation IDs, route templates, status and elapsed time; no bodies, authorization headers or raw query strings.
- This is a loopback-only development stack. External deployment, complete account lifecycle, AI and MCP protocol acceptance are later phases. PostgreSQL uses a project-specific bootstrap user for this local foundation; split migration/runtime DB privileges before cloud deployment.

## Code layout

`backend/app` contains API/auth/config and database commands; `backend/migrations` holds versioned SQL; `client/src` is the TypeScript reference client; `tests` contains HTTP acceptance; `scripts` handles setup and isolated testing; `docs` holds operator documentation and evidence. `mcp-server`, `skills`, and cloud `deploy` code will be created when those features are implemented, rather than as empty placeholders.
