# One service update, from MCP to verified PSA record

These visuals format actual test-stack responses of the TypeScript reference client using stdio MCP, a separate approver using the browser, and a stateful **synthetic PSA simulator**. The test identities are `op-a` and `approver-a`; no live ConnectWise tenant or hosted model was used. [Browser acceptance](evidence/workspace-browser.json) runs this sequence and the recovery branch. The [offline evidence viewer](showcase/mcp-evidence.html) presents all seven stages with expandable original client output; clone or download the repository and open it locally.

| Step | Actor and interface | Server check and resulting state | Capture |
| --- | --- | --- | --- |
| 1. Discover | `op-a` reference client negotiates stdio MCP and lists tools | Six bounded tools and their schemas are returned | [Tool discovery](showcase/mcp-discovery.png) |
| 2. Read | `op-a` calls `cw.ticket_context` for `A-100` | Session, tenant, company and board scope checked; source hash and ticket evidence returned | [Synthetic source context](showcase/mcp-context.png) |
| 3. Prepare | `op-a` calls `cw.note_prepare` with technician text | Server creates a proposal with fixed `internalFlag=true`, `externalFlag=false`, payload hash, evidence and expiry. No downstream note exists | [Exact MCP proposal](showcase/mcp-proposal.png) |
| 4. Approve | `approver-a` signs in to `/?proposal=PROPOSAL_ID`, inspects source and payload, confirms and clicks **Approve exact payload** | Domain API checks separate identity, current scope, payload hash and source freshness; proposal becomes `approved` | [Human review](showcase/review-approval.png) |
| 5. Execute | Original proposer calls `cw.execute_approved` with proposal ID and preserved idempotency UUID | Dispatch is persisted before the downstream POST; matching read-back marks it `verified` | [MCP receipt](showcase/mcp-verified.png) |
| 6. Inspect | `op-a` calls `cw.operation_verify` and the reviewer reloads the same proposal URL | Existing operation and external record ID remain visible; no second write is made | [Browser receipt](showcase/review-verified.png) |

Documented time uses `cw.time_entry_prepare` with **25 explicit minutes**, a technician timer reference and an aware start timestamp. See the [actual MCP time proposal](showcase/mcp-time.png) and [browser test report](evidence/workspace-browser.json). The same separate review and execution boundary applies.

## Lost response and recovery

The isolated simulator accepts a note write but withholds the response and first read-back. The original MCP execute call returns `unknown`: [captured MCP response](showcase/mcp-unknown.png) and [browser state](showcase/review-unknown.png). The operator uses **Verify existing operation** to read downstream state; [the same receipt becomes verified](showcase/review-recovered.png). The acceptance script independently counts one matching simulator record. It does not submit a replacement write.

The [operator guide](USER-GUIDE.md) gives commands for a local run. The [full scripted CLI/MCP replay](demo/demo.html) is an older, complementary protocol recording whose approval step uses the CLI; this walkthrough records the current browser approval boundary. Both operate solely on synthetic data.
