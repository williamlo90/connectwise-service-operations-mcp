# Local operations and recovery

Scope: the synthetic local/simulator release. Deployment operator: William. Connected ConnectWise recovery requires Phase 8A acceptance. There is no browser UI or callback consumer in V1; operators use the HTTP/stdio MCP reference client. Delayed HTTP responses, cancellation and unknown writes are covered by the protocol regression suite.

## Observe and respond

Start the optional local monitor alongside the scheduled worker:

```powershell
docker compose -f compose.yaml -f compose.ops.yaml --profile automation up -d --build --wait api worker monitor
```

The deployment operator reads `local/monitor/metrics.json` and `local/monitor/alerts.jsonl`. This is a local operator inbox, not email/Slack/pager delivery. Keep the folder and Docker access restricted to the machine owner. The monitor has database access across the deployment, so it is not exposed as a tenant API. Its data contains aggregate counts, fixed incident codes and timestamps; no ticket contents, tokens or provider credentials.

Polling occurs every 10 seconds. Worker heartbeat older than 30 seconds, pending queue age over 60 seconds, review jobs, unfinished writes and stale enabled sync schedules raise incidents. Sync freshness uses the configured interval plus 60 seconds. Startup before the first worker tick can produce a transient stale alert. Database unavailability raises its own incident and suppresses conclusions from unavailable business metrics. Firing and resolved events are persisted before state advances; a crash may repeat delivery. One monitor instance owns each inbox.

The current and previous inbox segments are bounded to approximately 5 MiB each. Snapshot/state files replace their predecessors. Docker logs carry sanitized API latency and downstream request latency joined by correlation ID; HTTP status counts distinguish denied/failed requests from completed work. `assistant_runs` records model latency, status and usage; an unknown model cost stays unknown. Local monitoring is not an independently available pager when the entire Docker host fails.

| Incident | Operator action |
| --- | --- |
| Provider unavailable, OOM or timeout | Check the selected runtime and memory cap. Keep the run failed; do not execute a missing draft. Restore runtime capacity, then make a new request after review. Never automatically switch a private request to hosted inference. |
| Credentials rejected / sync review | Repair the relevant credential through local configuration. Do not paste secrets into tickets or logs. Use an administrator to retry the existing review job after repair. |
| Queue backlog / worker stale | Inspect `docker compose --profile automation ps` and worker logs. Restore the worker. Review jobs deliberately block a new job for that tenant; do not delete them to clear the dashboard. |
| Sync stale | Check worker health, downstream connectivity and per-tenant review state. Resume from the committed page; read-only replays retain event uniqueness. |
| Unknown or review write | Use the existing operation's verify action. Check its expected/observed record and external ID. Do not create a new proposal or blindly repost. Escalate ambiguous or mismatched records for manual review. |
| Duplicate incident | Compare operation IDs, idempotency keys and external markers. Preserve evidence and pause new writes while reviewing. Repeating execute on the same approved proposal must return the existing receipt. |
| Database unavailable | Restore availability and verify readiness before writes. If data is lost, follow backup recovery below; stale approvals and unknown external outcomes still require reconciliation. |

## Backup and restore

Database dumps include credentials/configuration, hashed sessions, audit records and business data. Keep them under ignored `local/`, with OS access restricted and disk encryption enabled. Never commit or upload dumps as portfolio evidence. A local disk copy does not protect against loss of that disk. Production off-host encryption, retention and restore objectives remain deployment work.

For a local snapshot, stop this project's API/worker/monitor to quiesce application writes, keep its database running, and use `pg_dump -Fc` from the database container. Transfer the binary dump through a byte-preserving process such as Python `subprocess.run(..., capture_output=True).stdout`; do not redirect binary PostgreSQL archives through legacy PowerShell text pipelines. Resume services after the snapshot. Record the archive hash, schema revision and immutable application image identifier.

Restore first into a **new isolated database**, never directly over the active database. Use `pg_restore --exit-on-error`, compare all public table contents and sequence states with the recorded snapshot, run readiness/permission/write acceptance against the restored environment, and only then plan cutover. Stop application writers during cutover. Revoke restored sessions before reopening access. A restored audit row cannot prove the current state of an external PSA record: reconcile pending/unknown writes against the platform before resuming them.

`python scripts/qualify_local.py` demonstrates a real dump/restore into `cw_ops_restore_test` inside the disposable `cw-ops-qualify` stack and verifies every public table and sequence. It never restores over `cw_ops` or modifies other Docker projects. It retains its local synthetic dump for inspection and publishes only hashes/counts, not dump contents. Snapshot recovery timing is measured; no production RPO/RTO is claimed.

## Upgrade and rollback

Preserve the prior release's Git tag/image and take a verified backup. Phase 7 retains migration `004_automation.sql`, so application rollback to `phase-6` is schema-compatible. The qualification runner rebuilds that exact tracked source without `.env`, switches the isolated API to it, checks a verified internal-note write and permission boundaries, then restores the candidate API. Images should be stored by immutable digest for a real release; a Git rebuild also depends on retained dependency artifacts.

For future schema changes, explicitly document whether the previous application can read the new schema. If not, use a tested data restore/cutover plan; never assume a down migration is safe. For model rollback, select the recorded model digest and prompt version together and rerun the affected quality controls before claiming equivalent performance.

## Qualification commands and boundaries

```powershell
python scripts/test_local.py
python scripts/qualify_local.py
```

Both commands use named disposable stacks, synthetic credentials, no public ports and bounded containers. The qualification runner additionally requires the previously installed pinned Ollama image/model volume to test low-memory failure. Its normal/peak/two-minute soak contract lives in `evaluation/reliability-protocol.json`. No paid model request is made. Real model quality/latency evidence remains separately available in Phase 6; do not mix its inference timings with deterministic load timings.

Review alerts during local use and rerun regression after code/dependency changes. Review model quality after prompt/model changes. Keep raw local diagnostic logs/backups only as long as useful and remove them intentionally through the operator; committed evidence contains synthetic outcomes and source fingerprints. Dependency pinning, access controls and finite regression tests are not a penetration-test or vulnerability-free certification.
