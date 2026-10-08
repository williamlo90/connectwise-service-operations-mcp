# Phase 2 delivery — deterministic local workflows

Status: passed against the local HTTP simulator on 2026-10-08. Real ConnectWise access remains pending; this result does not establish vendor compatibility.

## Delivered

- Public-reference PSA subset with an immutable community SDK revision, source hashes, license, field/endpoint mapping and explicit assumptions: [contract](../contracts/PSA-SUBSET.md), [manifest](../contracts/reference-manifest.json).
- Stateful HTTP simulator backed by PostgreSQL: two tenant configurations, ticket/company/board/member context, public/internal note fixtures, internal-note and time-entry writes, pagination, read-back and fault injection.
- Deterministic summary with source facts; internal-note proposals; status/member recommendations; explicit-duration time-entry proposals with UTC conversion and configured work/member mappings.
- Separate-user approval bound to payload hash, proposal expiry and source/config snapshot. Company/board/role checks run in Python. The visible recovery marker is part of the approved payload.
- One durable dispatch per proposal, UUID idempotency conflict detection, external-ID receipts, field-by-field read-back, and read-only recovery for unknown outcomes. Ambiguous or mismatching evidence never reports success.
- Manual paginated sync with transactional checkpoint, bounded read retries, generation tracking and scoped cache freshness. Cached data cannot authorize a write.
- Interactive TypeScript workflow CLI and [Project 01/08 consumer examples](../client/src/consumer-examples.ts) using [contract 1.0.0](../contracts/MCP-CONSUMERS-V1.md) through an HTTP bridge.

## Verification

Run `python scripts/test_local.py` from the project root. It builds fresh images and uses a standalone temporary PostgreSQL stack without touching the local persistent database.

[phase-2-run.json](evidence/phase-2-run.json) records **27 passing HTTP tests** (17 workflow tests plus 10 foundation regression tests), compiled TypeScript client smoke, separate-session CLI workflow checks (including declined approval and piped time inputs), Project 01/08 consumer smoke, source fingerprints and API-log secret checks. The recorded test run took 9.037 seconds; this is test-suite elapsed time, not an application latency benchmark. It captured 224 structured API request events.

Coverage includes exact note/time payloads, two tenant mappings, missing/invalid duration, scope and role denial, self-approval denial, expired/tampered/stale proposals, revoked approver, concurrent execution, idempotency-key conflict, 429 retry, sync checkpoint preservation, cache staleness, timeout after committed note/time writes, ambiguous recovery markers, mismatched read-back and failed dispatch without automatic repost.

[phase-2-local-cli.json](evidence/phase-2-local-cli.json) records the operator → approver → execute → verify flow against the upgraded persistent local stack. The local API is available at `http://127.0.0.1:8030`; PostgreSQL and simulator remain internal to Compose. The local verification creates one synthetic internal note.

The earlier [Phase 1 evidence](evidence/phase-1-run.json) remains a historical snapshot. Current source fingerprints belong to Phase 2; the `phase-2` tag identifies the current learning checkpoint.

## Use and boundaries

Follow [LOCAL-SETUP.md](LOCAL-SETUP.md), then [PHASE-2-WORKFLOW.md](PHASE-2-WORKFLOW.md) for the runnable demo and recovery steps.

This phase has no LLM, MCP protocol transport, scheduler or cloud deployment. Status/assignment are recommendations only. Search uses a known local scope registry; source context is fetched live from the simulator. Full-scan pagination is not a consistent vendor snapshot, and absent records are retained as stale. There is no native downstream idempotency or atomic freshness precondition, so the implementation does not promise distributed exactly-once writes. Read-back normalization, visibility flags, actual API version and real tenant behavior require Phase 8A validation.

Next: Phase 3 AI assistant and reusable skills, keeping these domain rules authoritative. Provider access remains a separate dependency.
