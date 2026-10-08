# Phase 3 — local AI implementation and provider adapters

Status: **local AI workflow validated; hosted canaries pending keys**. This is an extractive service assistant over the PSA simulator. It does not claim real ConnectWise integration, MCP protocol acceptance or production model quality.

## Implemented behavior

- Four versioned application skills: summarize a ticket, prepare an internal note, prepare documented work time, and verify a ticket write. Packages include SKILL.md, JSON schemas and Python bindings. Interactive assistant and explicitly granted worker requests share the same handler.
- Scoped retrieval of ticket facts, company and up to eight recent notes. The model selects source IDs; the server validates those IDs and renders attributed text. Unsupported source IDs, extra model fields and insufficient source coverage are rejected. The model cannot supply tools, credentials, permissions, duration, approval or execution.
- Real Ollama inference with a pinned Qwen3 0.6B manifest, Q4_K_M weights, 4096-token context and one active call. CPU-only deployment caps inference at two CPUs / 1.5 GiB and unloads the model after a response. Runtime/model metadata are in [the manifest](../contracts/local-model.json) and [observed runtime details](evidence/local-model-runtime.json).
- OpenAI Responses, Anthropic Messages and xAI Chat adapters with structured-output requests, sanitized errors, input/output limits, explicit refusal/truncation handling, reported usage and no automatic retries or provider fallback. Official references are linked in [the setup guide](PHASE-3-ASSISTANT.md).
- Durable run IDs, request-conflict detection, version/source hashes, a global inference slot, logical cancellation and explicit interrupted-run handling. Costs remain null when not calculated; missing usage is never reported as zero.
- Completed drafts materialize atomically into at most one Phase 2 proposal after freshness/expiry checks. Separate human approval and verified downstream execution remain mandatory. The AI CLI displays evidence, draft, run status and recovery IDs.

## Evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Isolated regression suite | 41 passed: 27 HTTP regression, 9 ASGI assistant integration, 4 provider wire contracts, 1 skill-package parity test | [phase-3-run.json](evidence/phase-3-run.json) |
| Compiled client | Foundation, workflow and consumer smoke passed | Same regression report |
| AI reference CLI | Real local inference completed | [CLI evidence](evidence/phase-3-ai-cli.json) |
| Real local AI → proposal → separate test approver → simulator write/read-back | Passed | [workflow canary](evidence/phase-3-ollama-workflow.json) |
| Real local AI development sanity set | 5/5: A/B summary, internal note, explicit-duration time draft, worker reuse | [local evaluation](evidence/phase-3-local-evaluation.json) |
| Runtime outage/restart | Unavailable runtime fails without fallback; restart allows real inference | [recovery](evidence/phase-3-runtime-recovery.json) |

The five local sanity cases took approximately 12.8–26.4 seconds per assistant run on this workstation with a two-CPU inference cap. This is a small synthetic development set, not a held-out benchmark, a throughput test or a hosted/local quality comparison. The separate note workflow canary produced a verified simulator record. Test harness approval uses synthetic identities and is not a substitute for real operator review.

Host context: Windows with approximately 16 GiB RAM and RTX 4050 6 GiB; the tested profile used CPU inference, not GPU. Other local containers remained in use. The system has not been qualified for sustained load or forced OOM recovery; those require additional isolated reliability work. Shared-machine contention remains possible despite per-container limits.

## Provider status and remaining gate

| Provider | Contract tests | Real inference |
| --- | --- | --- |
| Ollama / pinned Qwen3 | Passed | Local workflow and sanity cases passed |
| OpenAI | Passed with controlled HTTP responses | Pending `.env` key and enabled canary |
| Claude / Anthropic | Passed with controlled HTTP responses | Pending `.env` key and enabled canary |
| Grok / xAI | Passed with controlled HTTP responses | Pending `.env` key and enabled canary |

The root `.env` contains empty provider key fields and `AI_HOSTED_ENABLED=false`. No paid request was sent during this delivery. After keys are supplied, recreate the API container and run one summary-only canary per configured provider using [the guide](PHASE-3-ASSISTANT.md). Model availability, schema support, actual usage/cost and latency must be established from those runs. Do not interpret the mocked wire tests as live provider validation.

Phase 3 is recorded as a **local checkpoint**, with hosted validation still open. Phase 0A/8A ConnectWise access and Phase 4 MCP transport remain separate work. The previous phase tags stay unchanged.
