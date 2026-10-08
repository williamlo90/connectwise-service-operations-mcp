# Portfolio copy — current validated implementation

## CV entry

**ConnectWise Service Operations MCP Server — Individual Portfolio Project**

TypeScript · MCP · Python/FastAPI · PostgreSQL · Docker · OpenAI · Ollama

- Built a six-tool MCP service-operations server with tenant-scoped access, separate-user approval, payload/source validation, and verified downstream writes against a PSA HTTP simulator.
- Implemented durable synchronization, bounded retries, audit records, and unknown-outcome reconciliation; validated 62 backend/evaluator tests and 11 real-protocol MCP scenarios.
- Qualified 135 synthetic tasks, including 33 verified writes, with zero observed errors or duplicate effects on the declared local workload; tested PostgreSQL restore, model OOM handling, and application rollback.

## Short CV version

Built and locally validated a TypeScript/Python MCP service-operations system with tenant isolation, human approval, and verified writes; passed 62 backend tests and 11 MCP scenarios against a synthetic PSA simulator.

## LinkedIn project description

I built a service-operations MCP server focused on a practical question: how can an assistant help with ticket work while keeping authorization and proof of completion explicit?

The system uses TypeScript MCP tools, a Python/FastAPI domain service and PostgreSQL to enforce tenant scope, separate-user approval, exact payload checks and downstream read-back. Optional OpenAI/Ollama assistance selects source evidence; it cannot approve or execute actions. A scheduled worker handles read-only synchronization and recovery queues.

Local validation passed 62 backend/evaluator tests and 11 MCP protocol scenarios. A declared synthetic workload completed 135 tasks, including 33 verified writes, with no observed errors or duplicate effects. The demo also shows recovery after a lost write response, and reliability checks cover backup restore, model OOM and rollback.

Current scope: a two-tenant synthetic PSA simulator. Azure end-to-end validation and real ConnectWise tenant validation are separate next steps.

## Featured-project caption

Service-ticket automation with explicit approval and proof of completion. Watch a lost write response recover to a verified receipt without posting twice. Built with MCP, TypeScript, FastAPI and PostgreSQL; validated locally against a synthetic PSA simulator.

## Thirty-second interview introduction

“I built an MCP server for service-ticket operations, focusing on the boundaries around AI. The model can select evidence, but the domain service enforces tenant access, a separate approver, and exact write verification. One interesting case is a timeout after a note has already been created: the system keeps an unknown outcome and reconciles it instead of retrying the write. I tested that through the real MCP protocol and a stateful HTTP simulator, alongside backup recovery, OOM handling and rollback.”

Repository: https://github.com/williamlo90/connectwise-service-operations-mcp. The repository is public; original materials remain All Rights Reserved. Use the included current-scope wording until cloud/vendor acceptance has actually passed; no Azure, live-ConnectWise or customer-ROI claim is included here.
