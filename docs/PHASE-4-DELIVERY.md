# Phase 4 — MCP service operations

Status: **complete for local stdio and the PSA simulator**. A separate TypeScript MCP server and SDK reference client now implement the six service-operation tools. Python remains authoritative for sessions, tenant/company/board scope, human approval, freshness, idempotency and downstream verification.

The reference assistant can read ticket context, prepare an internal note or explicit-duration time entry, execute after separate-user approval, and verify the resulting simulator record through MCP. Existing Project 01/08 consumer functions work through either HTTP or MCP. Approval remains a human CLI action outside the model tool catalog. Phase 3 AI skills are unchanged; Phase 4 verifies the service-operation transport, without a new autonomous model loop or paid inference.

| Validation | Result |
| --- | --- |
| Existing domain/assistant/provider regression | 41 tests passed |
| MCP client/server over real subprocess stdio | 11 scenarios passed |
| Interactive CLI | HTTP and MCP prepare, decline, approve, execute, verify and time input passed |
| Verified writes | Internal note and time entry read-back passed in the simulator |
| Replay and recovery | Concurrent execution, ambiguous downstream outcome and lost MCP receipt recovered without duplicate writes |
| Access and input boundaries | Tenant/record/role denial, expired credentials, strict arguments, unknown/malformed tools, source injection, cancellation, timeout and output caps passed |
| Traceability | MCP correlation UUID observed in domain audit; propagated by the PSA adapter |

[Machine-readable evidence](evidence/phase-4-run.json) records case names, protocol/SDK identity, source fingerprints and regression results. The test stack uses isolated PostgreSQL tmpfs and synthetic users. SQL fault/expiry fixtures exist only in the acceptance harness; MCP has no database access. Timeout/cancellation/oversized-response transport tests use a local HTTP fixture; interrupted-write recovery forwards to the real domain service and checks simulator records.

MCP SDK 1.32.1 and Zod 4.3.6 are pinned. Acceptance negotiates protocol 2025-11-25. The maintained v1 compatibility line is intentional; newer MCP protocol migration is not claimed. The server has a 32 KiB input buffer, 64 KiB response cap, four-call concurrency limit and no automatic request replay. Local application sessions supply identity; remote HTTP/OAuth transport is outside this checkpoint.

See [setup and recovery](PHASE-4-MCP.md). Checkpoint: **phase-4**. Previous phase tags remain unchanged. ConnectWise connected validation is still Phase 8A; scheduling/automation is Phase 5.
