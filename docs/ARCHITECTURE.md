# Architecture and control boundaries

Service Ops separates the user interface, model assistance and protocol transport from the authority to change a service record. FastAPI enforces the same rules for the browser, reference CLI and MCP consumers.

## Components

| Component | Implementation | Responsibility |
| --- | --- | --- |
| Browser workspace | Native HTML, CSS and JavaScript served by FastAPI | Scoped ticket context, proposals, separate-account approval and receipts |
| MCP and reference CLI | TypeScript, stdio MCP | Six bounded tools and interactive domain workflows |
| Domain API | Python/FastAPI | Authentication, tenant scope, payload/source checks, approval, dispatch and verification |
| Durable state | PostgreSQL, checksum-verified migrations | Sessions, scopes, proposals, approvals, operations, audit events and worker checkpoints |
| PSA adapter | Bounded HTTP requests | Server-owned routes/mappings, read retries, single write dispatch and read-back |
| Simulator | Stateful HTTP service | Synthetic tickets, notes and time records with isolated test fault injection |
| Optional AI | OpenAI or Ollama | Structured selection of attributed source evidence |
| Sync worker | Python/PostgreSQL scheduler | Read-only source synchronization, atomic page checkpoints and bounded retries |
| Monitor | Local monitoring process | Health metrics, worker status and durable local alert records |

Runtime definitions are in `compose.yaml`, `compose.ai.yaml` and `compose.ops.yaml`. The browser adds no separate frontend service. The deterministic stack requires no model credential, vendor tenant or n8n instance.

## Authority model

| Actor or layer | Can do | Boundary |
| --- | --- | --- |
| Operator | Read scoped tickets, prepare updates and execute own approved proposals | Cannot approve its own work |
| Approver | Inspect scoped proposals and approve an exact payload | Approval does not transfer proposer ownership |
| Administrator | Manage tenant configuration and sync recovery | No automatic business approval privilege |
| Auditor | Read sanitized tenant audit events | No write authority |
| AI provider | Select evidence and support a draft | No approval or execution tool |
| Worker | Synchronize source records | No downstream business writes |

The server derives actor and tenant from the authenticated session. Client role/tenant claims cannot replace it. Scope checks apply to direct record access and the browser activity list, as well as MCP calls.

## Write lifecycle

1. Fetch scoped source context and configured field mappings.
2. Prepare a proposal with its payload hash, source snapshot, evidence and expiry.
3. Require another authorized approver to accept the exact payload while its source remains fresh.
4. Allow the original proposer to execute. Persist dispatch state before sending the downstream POST.
5. Compare returned/read-back fields with the expected payload. Preserve the operation and external record IDs.
6. On uncertainty, reconcile the existing operation through reads. Do not automatically repeat the POST.

Proposal replay returns the existing operation. The approved correlation marker supports reconciliation after a lost response. A single matching record with the expected fields is required for verification. This does not imply distributed exactly-once delivery: a crash before dispatch can leave an unresolved operation, and a vendor can change state between the final read and write.

## Evidence and model boundaries

Source text is untrusted data. Browser rendering uses text nodes; model source selection is constrained by schemas, permitted evidence IDs and policy checks. Time entries require explicit technician duration and a timezone-aware start, with server-owned work/member mappings. Internal visibility and notification flags are fixed by the domain policy.

OpenAI and Ollama are the validated provider paths. Anthropic/xAI adapters have contract coverage but no live acceptance. There is no automatic hosted fallback. Model/prompt changes require the relevant regression and quality evaluation before publishing new claims.

## Deployment boundary

The current application runs locally against the synthetic simulator. The API binds to loopback; PostgreSQL and the simulator have no published host ports. Secrets are generated into ignored `.env`, and browser tokens stay in page memory.

Azure validation is the next deployment milestone. Remote identity, TLS, database roles, cloud monitoring and cloud recovery must be implemented and tested for that environment. Live ConnectWise validation is a separate milestone described in [ConnectWise validation](CONNECTWISE-VALIDATION.md).

Further detail: [PSA contract](../contracts/PSA-SUBSET.md), [MCP guide](PHASE-4-MCP.md), [operations runbook](OPERATIONS-RUNBOOK.md), [acceptance evidence](ACCEPTANCE-CHECKLIST.md).
