---
name: verify_ticket_write
description: Reconcile an existing write through the authoritative Phase 2 read-back handler.
---

# verify_ticket_write

Application skill version 1.0.0. Owner: service-operations domain service. This is an application package, not an installed Codex skill.

Use when: Reconcile an existing write through the authoritative Phase 2 read-back handler. Do not use to discover credentials, change tenant scopes, bypass approval, or fabricate resolution/work duration.

Preconditions: authenticated operator/approver, permitted ticket/company/board. The demo worker has an explicit grant only for summarize_service_ticket. Tenant and actor come from the server session.

Binding: `app.assistant.run_skill`; execution sequence: `verify_operation`. Both `/assistant/runs` and `/skills/verify_ticket_write/runs` use this same implementation.

Action policy: read-only downstream; updates local receipt; never repost. The model can only select source IDs. Its JSON cannot invoke a tool or set business fields. Output text is rendered from attributed source data; it is not a claim that every source statement is true.

Request: use the versioned RunInput schema with skill `verify_ticket_write`, a UUID request_id and ticket_id. See schema.json. Note/time drafts require technician_notes; time additionally requires duration_minutes, duration_evidence and timezone-aware time_start. Verification requires operation_id matching the ticket.

Failure handling: invalid or unsupported model output is rejected; insufficient evidence abstains; missing credentials/runtime fails without provider fallback. One model call, at most 512 generated tokens, 90-second HTTP timeout, 16KB prompt and 64KB response limits. Cancellation discards late output; upstream compute may finish within its timeout. Durable request IDs replay the existing run. Interrupted runs are not automatically retried. A new run after an error is an explicit caller decision.

Draft materialization: POST /assistant/runs/{id}/prepare rechecks source freshness and expiry, then atomically links one Phase 2 proposal. This never approves or executes. After approval, execution and reconciliation follow the Phase 2 workflow. There is no automatic compensation for an uncertain external result.

Example: {"request_id": "11111111-1111-4111-8111-111111111111", "skill": "verify_ticket_write", "ticket_id": "A-100", "provider": "ollama", "local_only": true}. Add the required technician/operation fields for the selected skill.

Acceptance fixtures: tests/test_assistant.py covers success, role/tenant denial, invalid output, stale context, cancellation, replay, duration absence and runtime failure. tests/test_ai_providers.py covers wire contracts, refusal, truncation, response bounds and unknown usage. Run trace stores versions, source/input hashes, latency and reported usage. Cost remains null when no price calculation is configured.

Changelog: 1.0.0 initial extractive evidence workflow; no MCP transport or scheduled worker.
