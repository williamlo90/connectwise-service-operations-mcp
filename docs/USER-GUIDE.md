# Operator guide

Use the [quick start](LOCAL-SETUP.md) first. This guide operates the synthetic PSA simulator. [Replay the recorded terminal demo](demo/demo.html), read its [plain transcript](demo/transcript.txt), or replay the [asciicast](demo/service-operations.cast) in a compatible player. The recording uses the actual CLI and MCP subprocesses; approvals in it are scripted test identities.

## Browser workspace

Open **http://localhost:8030/** after starting the local stack. The responsive workspace uses the existing domain HTTP API; the MCP/CLI remains available independently.

1. Click **Sign in** and use `op-a` with the generated `DEMO_PASSWORD` from your local `.env`.
2. Read the scoped ticket context. Enter technician observations and choose **Prepare proposal**. For time entries, supply minutes, duration evidence and a start time in your browser's local timezone.
3. Open the account menu, sign in as `approver-a`, and review the proposal. Expand **Inspect exact payload & evidence**, confirm the checkbox, then select **Approve exact payload**.
4. Sign back in as `op-a` and choose **Execute approved update**. A verified result includes the downstream record ID.
5. For an unknown/review outcome, choose **Verify existing operation**. After a browser/network interruption, refresh and open the existing proposal before doing anything else.

The activity table includes the latest 40 proposals within your scope, including proposals created through MCP. Refresh loads the latest state. Switching tenants clears the previous workspace; tokens remain only in page memory, and a reload requires login. No credentials are embedded in the frontend. The browser covers deterministic note/time operations; optional AI assistance remains in the CLI.

For an independent tenant, use `op-b` and `approver-b`. Administrator, auditor and worker accounts use their existing tools rather than this operator workspace.

Browser acceptance and screenshots: [workspace validation](WORKSPACE-UI.md).

## Read the ticket and prepare an internal note

```sh
docker compose run --rm client --mcp --workflow context A-100
docker compose run --rm client --mcp --workflow note A-100
```

At `Internal note >`, enter `Checked VPN settings; customer retest is pending.` The command returns a proposal ID and the exact internal-note payload. Copy that ID; no note exists downstream yet. Check the ticket/company/board and source statements. A source saying something happened is not independent proof that the issue is resolved.

## Review and approve as a separate person

```sh
docker compose run --rm -e DEMO_USERNAME=approver-a client --workflow approve PROPOSAL_ID
```

Replace `PROPOSAL_ID` with the actual ID. Read the payload, duration evidence if present and destination. Type `APPROVE` only if correct. Any other response submits no approval. The proposer cannot approve their own draft. Approval is a direct authenticated domain action and is intentionally absent from the MCP tool catalog.

## Execute and verify

```sh
docker compose run --rm client --mcp --workflow execute PROPOSAL_ID
docker compose run --rm client --mcp --workflow verify OPERATION_ID
```

Keep the printed idempotency key, proposal ID and operation ID. A `verified` receipt means the expected fields matched the simulator read-back. Check the external ID and resulting evidence. Repeating execute with the same proposal reuses its existing receipt; it does not create another record.

## Record documented time

```sh
docker compose run --rm client --mcp --workflow time A-100
```

Supply, in order: work description, integer minutes, timer/work-log evidence and an ISO start timestamp including timezone. Example: `Checked VPN connection`, `25`, `Technician timer recorded 25 minutes`, `2026-10-08T09:00:00+07:00`. The service calculates the end time and hours, uses configured member/work mappings, and defaults to `DoNotBill`. Review and approve that proposal with the same separate-user process. Never invent duration to make a draft complete.

## Optional AI assistance

After [configuring the chosen runtime](PHASE-3-ASSISTANT.md), use `docker compose run --rm client --ai summary A-100` or replace `summary` with `note`/`time`. Note/time asks for technician evidence; time also requires duration. AI selects sources and proposes a draft. It cannot approve or execute.

For a completed note/time run, use `docker compose run --rm client --ai prepare RUN_ID` to materialize a proposal, then follow the review/approval workflow. OpenAI requires explicit hosted enablement and an API key in `.env`; select it with `-e AI_PROVIDER=openai`. The model selection is explicit and has no automatic hosted fallback. Runtime costs shown as null are unknown, not free.

## Interpret the outcome

| Status / response | Meaning and next action |
| --- | --- |
| AI `completed` | Valid source selection/draft; inspect it before materializing. It is not approval or a downstream write. |
| AI `abstained`, `rejected`, `failed`, `cancelled` | No usable draft; inspect the reason/source/runtime. Do not execute. Cancellation may not stop a request already sent to the provider. |
| Proposal + payload hash | Prepared only. Ask the separate approver to review current evidence. |
| `approved` | Exact fresh payload approved by another authorized user. Execute through the operator session. |
| `verified` | Expected fields matched read-back; retain the receipt. |
| `unknown` | A write may exist but the system cannot prove its outcome. Verify the existing operation; do not create a replacement. |
| `review` | Evidence is ambiguous/mismatched or a job exceeded its retry budget. Ask the operator/administrator to investigate. |
| 403 / `forbidden` | Role or approval requirement failed. Change to the appropriate authorized identity, not to a forged header. |
| 404 / `not_found` | Missing or out-of-scope record. Confirm the ticket and tenant. |
| 409 / `conflict` | Input replay conflict, stale source, expired proposal or changed approval context. Review fresh data. |

In the recorded recovery, the simulator commits one note but delays its response, and the first read-back fails. The receipt is `unknown`; a later verify proves it exists. Replaying execute returns the same operation. Failure injection exists only in the disposable demonstration harness and is not an operator command against ConnectWise.

## Administrator and support

Use `docker compose run --rm -e DEMO_USERNAME=admin-a client --automation status` or `jobs`. Pause/resume and explicit retry are documented in [scheduled synchronization](PHASE-5-AUTOMATION.md). Check `local/monitor` during local use and follow the [runbook](OPERATIONS-RUNBOOK.md) for outages, backup or rollback. Give support the correlation ID, operation ID, time and sanitized status; never send passwords/API keys or unnecessary ticket content.
