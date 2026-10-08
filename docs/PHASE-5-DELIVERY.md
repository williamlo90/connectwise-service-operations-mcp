# Phase 5 — scheduled local automation

Status: **complete for the local PSA simulator**. The Python worker runs scheduled ticket-cache refreshes with PostgreSQL job ownership, transactional checkpoints, bounded retries and an administrator review queue. The existing MCP path remains responsible for human-approved, verified note/time writes.

| Check | Result |
| --- | --- |
| Backend regression | 52 passed, including 11 automation cases |
| MCP protocol acceptance | 11 scenarios passed; verified note/time writes and interrupted-response recovery retained |
| CLI | HTTP/MCP workflows and automation status/jobs passed |
| Duplicate work | Concurrent triggers/workers and unchanged scans produced no duplicate change observations |
| Crash recovery | A real subprocess killed after an uncommitted page rolled back cache/events/cursor; subsequent processing completed |
| Source failure | Rate limit retry, partial-page checkpoint, malformed source, rejected credentials and exhausted retry budget behaved as specified |
| Authorization | Admin-only controls, strict schedule input, cross-tenant denial and separately configured A/B caches passed |
| Local worker runtime | Healthy container; scheduled startup scans completed for both tenants with a 128 MiB / 0.5 CPU cap |

Evidence: [isolated test report](evidence/phase-5-run.json), [worker runtime](evidence/phase-5-worker-runtime.json). The reports distinguish synthetic tests from the local persistent worker. No paid inference is involved. The worker performs GET-only downstream synchronization; it cannot approve or execute a business write.

Migration `004_automation.sql` adds schedules, jobs, source-change observations and heartbeat state. Seed initializes two independent schedules without overwriting existing settings. The manual sync endpoint and worker share the same page-processing service and HTTP adapter. Runtime configuration remains simulator-only; enabling real ConnectWise endpoints is still Phase 8A.

See [operations and recovery](PHASE-5-AUTOMATION.md). The worker is opt-in through the Compose `automation` profile. Failed jobs in `review` block new scans for that tenant until an administrator repairs the cause and retries. Automatic write reconciliation, model quality comparisons, queue retention and production reliability qualification are not claimed by this phase.

Checkpoint: **phase-5**. Previous tags remain unchanged. Next: Phase 6 evaluation design, frozen datasets and measured workflow quality.
