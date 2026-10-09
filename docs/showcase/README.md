# Service Ops: MCP to human approval to verified record

These are captures from the actual TypeScript reference client over stdio MCP and the working human-review page against an isolated **synthetic PSA simulator**. They do not show a live ConnectWise tenant. The [canonical walkthrough](../MCP-WALKTHROUGH.md) identifies each actor, tool, check and state; [browser acceptance](../evidence/workspace-browser.json) reproduces the sequence.

## 1. Discover and read the source

The SDK client lists the six tool schemas, then `op-a` reads scoped ticket `A-100`. The screenshot shows the simulator response and source references, not a ConnectWise PSA screen.

[![Six actual MCP tools](mcp-discovery.png)](mcp-discovery.png)

[![Scoped synthetic ticket context](mcp-context.png)](mcp-context.png)

## 2. Prepare an internal-only update through MCP

`cw.note_prepare` returns a proposal, exact payload, hash, evidence and expiry. Its `internalFlag=true` and `externalFlag=false` are server-owned. No downstream note exists yet.

[![MCP note proposal](mcp-proposal.png)](mcp-proposal.png)

## 3. Review as another person

`approver-a` opens the proposal URL, sees ticket evidence and the exact payload, and explicitly confirms it. The browser has no preparation or execution form.

[![Separate-user human approval](review-approval.png)](review-approval.png)

## 4. Execute and verify through MCP

The original proposer executes the approved update, preserving the idempotency key. The receipt includes the operation and downstream external ID after matching read-back.

| MCP receipt | Review page receipt |
| --- | --- |
| [![Verified MCP response](mcp-verified.png)](mcp-verified.png) | [![Verified browser receipt](review-verified.png)](review-verified.png) |

## 5. Recover an uncertain write

The simulator writes one note but loses its response; the first read-back is unavailable. The original MCP call and browser both show `unknown`. Verifying the **existing** operation resolves it to `verified`; the acceptance script independently counts one matching downstream effect.

| Unknown outcome | Reconciled receipt |
| --- | --- |
| [![Unknown browser outcome](review-unknown.png)](review-unknown.png) | [![Verified recovery](review-recovered.png)](review-recovered.png) |

The [actual MCP unknown response](mcp-unknown.png) and [MCP verification response](mcp-recovered.png) are also captured. The [390px mobile review](review-mobile.png) keeps the human decision usable on a narrow screen.

The [older full CLI/MCP replay](../demo/demo.html) remains available as additional protocol evidence; its approval step uses scripted CLI input. This current walkthrough uses the separate browser review surface. All data is synthetic.
