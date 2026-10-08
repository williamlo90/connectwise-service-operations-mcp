# Phase 1 delivery — local foundation

Date: 2026-10-08, Asia/Jakarta. Status: **passed for the Phase 1 local scope**. This is synthetic local acceptance, not ConnectWise or MCP protocol validation.

## Delivered behavior

- FastAPI login with scrypt password hashes, opaque expiring sessions stored as token hashes, logout/revocation, and a five-failure login throttle per username over five minutes.
- Server-derived identity, role and tenant. Ticket list and direct-ID routes share tenant/company/board scope filtering and parameterized SQL. The API ignores client headers purporting to choose a role or tenant.
- PostgreSQL migrations with checksums and a transaction/advisory lock; idempotent seed containing two tenants, six role identities and four tickets.
- Sanitized structured request logs with generated correlation IDs; tenant-scoped audit events; health and schema readiness checks.
- Compiled TypeScript reference CLI performing actual HTTP login, list, detail and logout. Browser UI and MCP transport are future work.
- Digest-pinned Linux Docker images, locked Python and Node dependencies, generated ignored local credentials, loopback-only API and an unpublished database.
- Reproducible disposable test database reset and English [setup/use/troubleshooting guide](LOCAL-SETUP.md).

## Verification

Command: `python scripts/test_local.py`.

**10 tests passed** against a running HTTP server and real PostgreSQL in the separate `cw-ops-test` Compose project:

1. Anonymous and invalid-token access denied.
2. Audit actor/tenant/correlation correctness and hashed session storage.
3. Unsupported connected/production configuration and weak database password rejected, with input hidden in validation messages.
4. Liveness and database/schema readiness.
5. Idempotent migration and seed rerun.
6. Failed-login throttle.
7. Logout, token expiry and disabled-account rejection.
8. Operator/Approver/Administrator/Auditor/Worker read-role matrix.
9. List and direct-ID access isolation across tenants, companies and boards.
10. Login privilege-field injection, SQL-like query input and pagination bounds.

The compiled TypeScript client also passed login/list/detail against the test stack. The runner verified structured request events and absence of the tested password/token markers in API logs, then removed the disposable stack. Full result, case names, timing and source SHA-256 fingerprints are in [phase-1-run.json](evidence/phase-1-run.json). The `phase-1` Git tag identifies this learning checkpoint; source fingerprints identify the tested files.

The documented setup commands were also run against a newly created persistent local stack: build, migrations, readiness, seed and client smoke passed. Host HTTP checks returned 200 for `/health/live` and `/health/ready`. The API remains available at `http://127.0.0.1:8030`; local API and PostgreSQL containers were healthy at handoff. No other project containers or data were reset.

## Boundaries and next step

No ConnectWise API requests, provider calls, cloud deployments or external messages were made. Data is seeded synthetic application data; the HTTP simulator and ConnectWise adapter are not built yet. Phase 2 adds the reference contract, simulator and deterministic proposal/approval workflows. Account provisioning/rotation, runtime-versus-migration DB privilege separation and full security/load/backup qualification remain later-phase work before cloud deployment.

The documented layout reserves MCP server, skills and deployment implementation for their respective phases without creating empty executable placeholders. Phase 0A access to ConnectWise and hosted providers remains open; Phase 8A will validate the actual ConnectWise tenant.
