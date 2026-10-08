# Scheduled ticket synchronization

The optional Python worker refreshes the PSA ticket cache for each configured tenant. It uses the same HTTP adapter and page-processing function as the manual sync endpoint. It does not call a model, approve proposals or create downstream notes/time entries. Human writes continue through the Phase 4 MCP workflow and its separate approval/read-back controls.

## Start and operate

```sh
docker compose --profile tools --profile automation build
docker compose up -d --wait api
docker compose run --rm seed
docker compose --profile automation up -d --wait worker
docker compose run --rm -e DEMO_USERNAME=admin-a client --automation status
docker compose run --rm -e DEMO_USERNAME=admin-a client --automation jobs
```

The seed creates schedules for synthetic tenants A and B, initially due and repeating every 300 seconds. Re-running seed preserves existing schedule settings. The worker has a 128 MiB / 0.5 CPU cap, no host port and no hosted AI credentials. It processes one page per tick and checks for work every two seconds. Stop only this worker with `docker compose --profile automation stop worker`; other projects and services are unaffected.

```sh
docker compose run --rm -e DEMO_USERNAME=admin-a client --automation pause
docker compose run --rm -e DEMO_USERNAME=admin-a client --automation resume
docker compose run --rm -e DEMO_USERNAME=admin-a client --automation retry JOB_ID
```

Pause prevents new pages from starting for that tenant; a page already running may commit. Resume keeps the configured interval. `jobs` accepts an optional offset and returns `next_offset`. `retry` is an explicit administrator action for a reviewed job after its cause has been repaired. It restarts the read-only scan while preserving job identity and total attempt history. Operator/approver/worker accounts cannot use these admin controls.

Authenticated administration endpoints are `GET /automation/status`, `GET /automation/jobs`, `POST /automation/jobs/{id}/retry`, and `POST /automation/schedule`. Schedule input is exactly `{ "enabled": true, "interval_seconds": 300 }`, with intervals from 60 to 3600 seconds. Identity supplies the tenant; requests cannot select another tenant. Tenant B has a separate seeded schedule and mappings. Its schedule can run without impersonating a tenant administrator; provisioning a tenant B human administrator is an explicit deployment/account-management concern.

## State and recovery

`automation_schedules` stores durable due times. Each scheduled event has a unique tenant/event key, and a partial unique index permits only one unfinished job per tenant. Missed intervals are coalesced to one scan after downtime; they do not create a catch-up backlog. A review job blocks later scheduled jobs for its tenant until repaired.

Workers claim jobs with PostgreSQL `FOR UPDATE SKIP LOCKED`. The job lock is held during one bounded HTTP read and database transaction. Cache writes, change observations, cursor movement and job progress commit together. A crash before commit releases the lock and rolls the page back; a later worker reads it again. There is no lease timeout that can create overlapping owners. Manual sync and scheduled sync share the same locked cursor, so they can jointly advance a scan without racing its checkpoint.

The cursor is a full-scan page/generation checkpoint, not a vendor change-feed token. A completed scan increments its generation and records freshness. The backend validates IDs and required source fields before cache updates. `ticket_change_events` records changed source hashes; replaying an unchanged page does not emit another observation. Events do not themselves authorize business actions. Records absent from a later scan are retained and become stale; deletion is not inferred. A changing remote dataset can shift offset pages, so subsequent scans provide refresh rather than a point-in-time snapshot.

| Condition | Recovery |
| --- | --- |
| Rate limit / transient read failure | PSA GET retries are bounded to three requests; the job then waits 5 seconds, followed by 10 seconds for its third and final attempt |
| Three failed job attempts on a page | Job moves to `review`; successful pages reset the consecutive-attempt budget |
| Credentials rejected or missing, invalid mapping configuration, malformed source | Immediate `review`; repair configuration/source, then explicitly retry |
| Process killed mid-page | Transaction rolls back; another worker resumes the durable cursor |
| More than 100 successful pages without completing | Review instead of an unbounded scan |
| Database unavailable | No checkpoint is advanced; worker logs a sanitized availability event and retries its next tick; heartbeat becomes stale |
| External ticket updated | Next scan updates the cache and emits a new source observation; writes still re-read authoritative context before approval/execution |
| Unknown outcome from a human-approved write | Preserve proposal/key, reuse the existing operation and use `--mcp --workflow verify OPERATION_ID`; sync never reposts it |

Review items are the local dead-letter queue. There is no automatic redrive of permanent failures. Credential values and source bodies are excluded from worker logs. The job UUID is propagated as a correlation header to the PSA adapter; API administration changes also produce audit events. Heartbeat reports whether the worker loop is alive, while per-tenant job status exposes sync failures; a healthy loop does not mean every tenant has synchronized successfully.

## Validation and boundaries

Run `python scripts/test_local.py` for the isolated synthetic suite. Automation cases invoke production scheduler/page code against PostgreSQL and the HTTP simulator, including a subprocess killed after writing an uncommitted page. The real worker entrypoint and health command are exercised. MCP acceptance separately covers verified note/time writes and recovery after lost responses.

The scheduler is enabled only through the `automation` Compose profile. It has no n8n dependency and makes no paid model requests. Local backup/restore, bounded load and alerts were qualified in Phase 7; see [the runbook](OPERATIONS-RUNBOOK.md). Longer production workloads and tenant retention remain deployment work. The adapter still accepts only the local simulator origin; real ConnectWise access and validation remain Phase 8A.
