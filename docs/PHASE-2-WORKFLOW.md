# Deterministic service workflow

Run the setup/build/start/seed commands in [LOCAL-SETUP.md](LOCAL-SETUP.md) first. For an existing Phase 1 installation, rerun them: setup preserves passwords and adds a simulator secret; migrations add workflow tables without resetting data. The simulator and database have no published ports.

## Read and prepare

```sh
docker compose run --rm client --workflow context A-100
docker compose run --rm client --workflow note A-100
```

The note command prompts for internal text and returns a proposal ID, exact payload, payload hash and expiry. Copy the proposal ID from the result. No external record is created yet. For a time entry:

```sh
docker compose run --rm client --workflow time A-100
```

Enter a work description, documented integer minutes, timer/work-log evidence, and an ISO start such as `2026-10-08T09:00:00+07:00`. Duration is never inferred from ticket age or note text. Billing policy is nonbillable for this local subset.

## Review and approve

Replace `PROPOSAL_ID` with the returned UUID:

```sh
docker compose run --rm -e DEMO_USERNAME=approver-a client --workflow approve PROPOSAL_ID
```

The approver sees the complete payload and duration evidence. Type `APPROVE` only after reviewing them. The recovery marker in the note text is intentional and covered by the approval hash. The proposer cannot approve their own proposal. A proposal expires after 30 minutes; source or mapping changes require a new reviewed proposal.

## Execute and verify

Switch back to the proposer:

```sh
docker compose run --rm client --workflow execute PROPOSAL_ID
```

The client prints the generated idempotency key before sending. Preserve it when retrying an interrupted request:

```sh
docker compose run --rm client --workflow execute PROPOSAL_ID IDEMPOTENCY_KEY
docker compose run --rm client --workflow verify OPERATION_ID
```

`verified` means the simulator record was read back and matched every approved field. The receipt includes external ID and verification time. `unknown` means the outcome could not be established; `review` means evidence was ambiguous or mismatched. Neither is success. Repeating execute never posts that proposal again. Use verify to reconcile; if unresolved, inspect the downstream record and operation evidence before preparing any replacement. Do not blindly make another proposal after a timeout.

For tenant B use `DEMO_USERNAME=op-b`, ticket `B-100`, and `approver-b`. The same numeric remote ticket ID belongs to a separate connection with its own company, board, member and time-work mappings.

## Recommendations, sync and consumer examples

Status/assignment recommendations are available through `POST /workflow/tickets/{id}/recommend` with `status_id` and/or `member_id`. They validate against configured board/member scope and do not alter tickets.

An administrator session can call `POST /workflow/sync` once per page until `completed=true`, then inspect `GET /workflow/sync/status`. Operators can read `/workflow/tickets/{id}/cached`; stale cache never authorizes a write. Synchronization is manual in this phase; scheduling/review queues arrive in Phase 5. Search uses the local scope registry; use context for source-current information.

```sh
docker compose run --rm client --consumer-smoke
python scripts/test_local.py
```

The consumer smoke creates two unapproved demo proposals and tests the Project 01/08 contract through HTTP. The acceptance runner uses an isolated temporary PostgreSQL database, removes only that test stack, and writes `docs/evidence/phase-2-run.json`.

Real ConnectWise validation remains Phase 8A. Phase 2 does not use an LLM, real tenant, MCP protocol transport, scheduled worker or Azure deployment.
