# Six-tool MCP contract

The TypeScript server exposes these tools over stdio. Its reference client is `client/src/index.ts` with `--mcp`; it starts an SDK client and a separate MCP server process. A short-lived application session is supplied to that process through its environment. The domain API derives identity and tenant from the session, then checks ticket company/board scope on every request. Tool arguments cannot grant a role or select another tenant.

| Tool | Input | Output | Enforced authority | Acceptance evidence |
| --- | --- | --- | --- | --- |
| `cw.ticket_search` | Optional query, limit, offset | Scoped page and next offset | Authenticated ticket scope; read only | [Protocol regression](evidence/workspace-regression.json) |
| `cw.ticket_context` | Ticket ID | Ticket, notes, source hash, attributed facts | Operator/approver scope; retrieved text is untrusted | [Captured context](showcase/mcp-context.png) |
| `cw.note_prepare` | Ticket ID, content, optional `internal` visibility | Proposal, exact payload/hash, evidence, expiry | Operator; server fixes internal visibility and notification flags; no PSA write | [Captured proposal](showcase/mcp-proposal.png) |
| `cw.time_entry_prepare` | Ticket ID, description, integer minutes, duration evidence, timezone-aware start | Proposal with calculated hours and mapping | Operator; no inferred duration; no PSA write | [Browser/MCP acceptance](evidence/workspace-browser.json) |
| `cw.execute_approved` | Proposal UUID and preserved idempotency UUID | Durable operation receipt and downstream ID when verified | Original proposer only, after another authorized user approves exact fresh payload | [Verified receipt](showcase/mcp-verified.png) |
| `cw.operation_verify` | Existing operation UUID | Reconciled receipt | Scoped operation; read-back only, no new PSA POST | [Recovery capture](showcase/mcp-recovered.png) |

Discovery publishes strict JSON input/output schemas and annotations; [the actual tool list](showcase/mcp-discovery.png) was captured from the SDK client. Tool success includes `data`, `correlation_id`, `source`, and `untrusted_content` in the MCP envelope. The CLI prints `data` for readability. Approval is intentionally a separate authenticated browser/domain action and is absent from the MCP catalog.

The [implementation guide](PHASE-4-MCP.md) documents response limits, errors, protocol version and retry behavior. All captures here use an isolated synthetic PSA simulator. A live ConnectWise tenant has not been validated.
