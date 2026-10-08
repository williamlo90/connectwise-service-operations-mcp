# Local MCP server

The TypeScript MCP process exposes service operations over stdio and forwards authorized requests to the Python domain API. PostgreSQL, approval checks, idempotency and PSA simulator access remain owned by Python. Each process uses one existing application session supplied through `MCP_ACCESS_TOKEN`; credentials, tenant IDs and approval authority are never tool arguments.

## Run the reference assistant

Build the client image after updating the checkout:

```sh
docker compose --profile tools build client
docker compose run --rm client --mcp --workflow context A-100
docker compose run --rm client --mcp --workflow note A-100
docker compose run --rm client --mcp --workflow time A-100
```

The CLI logs in, launches a separate MCP child process, negotiates capabilities and calls tools through the SDK client. It prints the proposal for review. Run approval as a separate user using the existing human confirmation prompt:

```sh
docker compose run --rm -e DEMO_USERNAME=approver-a client --workflow approve PROPOSAL_ID
docker compose run --rm client --mcp --workflow execute PROPOSAL_ID IDEMPOTENCY_KEY
docker compose run --rm client --mcp --workflow verify OPERATION_ID
docker compose run --rm client --mcp --consumer-smoke
```

Use a UUID for the idempotency key and retain it before execution. The CLI generates and prints one when omitted. Approval is deliberately outside the tool catalog. Consumer examples prepare proposals only. CLI login, identity display and human approval use HTTP; the six service operations use MCP when `--mcp` is selected. Phase 3 AI skill commands remain available through `--ai`; this transport does not add an autonomous model loop.

For another trusted local MCP host, compile `client` and launch `node client/dist/mcp-server.js`, supplying `API_URL` and `MCP_ACCESS_TOKEN` through the process environment. Use an existing short-lived application session. Do not put tokens in command arguments or committed host configuration. The server never logs in or renews a session automatically; expired/revoked sessions fail on subsequent domain requests. The reference client logs out at exit. No HTTP MCP listener is exposed in this phase.

## Contract and recovery

| Tool | Behavior |
| --- | --- |
| `cw.ticket_search` | Scoped local registry search; `limit` and `offset`, with `next_offset` |
| `cw.ticket_context` | Scoped simulator context, source references and evidence text |
| `cw.note_prepare` | Internal-only note proposal; no downstream write |
| `cw.time_entry_prepare` | Proposal using explicit integer minutes, evidence and aware timestamp |
| `cw.execute_approved` | Execute a fresh proposal approved by another active, authorized user |
| `cw.operation_verify` | Reconcile downstream evidence without creating another record |

Discovery publishes strict argument schemas and output envelope schemas. Success returns `structuredContent` plus matching JSON text: `data`, `correlation_id`, `source` and `untrusted_content`. Domain payload/source records retain their field maps; the envelope and operation arguments reject unknown properties. Retrieved content is data, not authority. There is no arbitrary URL, SQL, shell, credential or approval tool.

Tool failures use `isError=true` and sanitized JSON containing `error` and `correlation_id`. Stable codes are `unknown_tool`, `invalid_arguments`, `busy`, `cancelled`, `timeout`, `output_limit`, `unauthenticated`, `forbidden`, `not_found`, `conflict`, `invalid_request`, `rate_limited`, `downstream_error`, `invalid_response` and `unavailable`. Malformed protocol messages follow SDK JSON-RPC error handling. Upstream error bodies are never forwarded.

The process caps concurrent calls at four, incoming message buffers at 32 KiB and response reads at 64 KiB. Default backend timeout is ten seconds. MCP cancellation aborts the HTTP wait; a domain operation already dispatched can still finish. After interrupted execution, use the same proposal/key to obtain the existing receipt, then verify its operation ID. Never automatically create a replacement proposal. Prepare has no client replay key: if its response is lost, review the domain record before preparing again. Neither MCP nor the HTTP bridge retries calls automatically; bounded read retries within the PSA adapter remain unchanged.

Correlation UUIDs propagate from MCP to Python audit/log records and PSA request headers. Source text, tokens and request bodies are excluded from MCP logs. The trusted local process owner controls its environment; this is not remote OAuth authentication. Remote authenticated transport remains deployment work.

## Versions and verification

The lockfile pins `@modelcontextprotocol/sdk` 1.32.1 and Zod 4.3.6. The acceptance client negotiates MCP `2025-11-25`; older negotiation versions inherited from the SDK are not independently qualified. This intentionally uses the maintained v1 compatibility line. The [official SDK documentation](https://github.com/modelcontextprotocol/typescript-sdk/tree/v1.x) identifies v2 and MCP 2026-07-28 as the newer line; migration requires a separate compatibility review. Tool behavior follows the [2025-11-25 tool specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).

```sh
python scripts/test_local.py
```

The runner rebuilds an isolated `cw-ops-test` stack, runs Python/domain regression and existing CLI checks, then starts actual SDK client/server subprocesses for MCP acceptance. Test-only SQL fixtures manipulate expiry and simulator faults in the disposable database; the MCP child receives no database or demo-password environment. Transport timing/size cases use a controlled local HTTP fixture. No hosted-model request is made. The runner writes [Phase 4 evidence](evidence/phase-4-run.json) and removes only its test stack.
