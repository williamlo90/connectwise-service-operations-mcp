# Service operations consumer contract 1.0.0

The six MCP tool names have a versioned TypeScript input/output contract in [service-operations-v1.ts](../client/src/service-operations-v1.ts). This version identifies the application contract, not an MCP protocol version. The Phase 2 HTTP bridge and Phase 4 MCP stdio bridge implement the same application contract. See [the MCP guide](../docs/PHASE-4-MCP.md) for protocol versions, output envelopes and recovery.

| Tool | Domain endpoint | Result |
| --- | --- | --- |
| `cw.ticket_search` | GET `/tickets?q=&limit=&offset=` | Scoped local ticket registry; items and pagination |
| `cw.ticket_context` | GET `/workflow/tickets/{ticket_id}/context` | Live simulator ticket, company/board, labeled notes, deterministic summary and source facts |
| `cw.note_prepare` | POST `/workflow/proposals` with kind note | Internal-only payload, hash, expiry and evidence |
| `cw.time_entry_prepare` | POST `/workflow/proposals` with kind time | Explicit-duration payload, hash, expiry and evidence |
| `cw.execute_approved` | POST `/workflow/proposals/{proposal_id}/execute` | Receipt; requires persisted separate-user approval and UUID idempotency key |
| `cw.operation_verify` | POST `/workflow/operations/{operation_id}/verify` | Reconciled receipt; no external write |

Only `status=verified` with an external ID and verified timestamp is success. `dispatched`, `unknown` and `review` are pending/unresolved outcomes. Repeating execution returns the existing operation; verify performs read-only reconciliation. Clients must preserve proposal IDs and idempotency keys across retries. No tenant, role, base URL, member or arbitrary payload override is accepted by these tools.

Approval is intentionally outside the consumer tool contract. A human approver reads `GET /workflow/proposals/{id}` and submits its `payload_hash` plus `confirmed=true` to `/approve`. Python enforces role, tenant, company/board, distinct proposer, expiry, source snapshot and current approver validity; TypeScript types alone are not authorization.

HTTP error categories: 401 invalid session; 403 role/approval/proposer restrictions; 404 inaccessible or missing record; 409 stale/expired/tampered proposal or idempotency conflict; 422 invalid fields; 502 downstream unavailable/invalid; 503 database/configuration unavailable. Errors include a correlation header and never echo credentials. The MCP error envelope uses `isError=true` with sanitized `error` and `correlation_id`; see the MCP guide for stable codes.

[consumer-examples.ts](../client/src/consumer-examples.ts) contains two reusable examples:

- Project 01: read a ticket's context and prepare a deterministic internal handoff note.
- Project 08: prepare a time entry from technician-supplied duration, start time and work-log evidence.

Both stop at proposal review. They neither manufacture human approval nor silently execute. The examples are compiled and exercised against the real local HTTP domain service with `--consumer-smoke`; add `--mcp` to use the protocol bridge. The isolated acceptance suite also invokes both examples over MCP. They have not been integrated into either separate project's codebase.
