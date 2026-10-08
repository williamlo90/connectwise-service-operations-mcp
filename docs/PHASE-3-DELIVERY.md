# Phase 3 — local AI implementation and provider adapters

Status: **Phase 3 complete: Ollama workflow and OpenAI canary validated**. This is an extractive service assistant over the PSA simulator. It does not claim real ConnectWise integration, MCP protocol acceptance or production model quality.

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

## Provider validation

| Provider | Contract tests | Real inference |
| --- | --- | --- |
| Ollama / pinned Qwen3 | Passed | Local workflow and sanity cases passed |
| OpenAI (required hosted provider) | Passed with controlled HTTP responses | Real summary canary passed; [evidence](evidence/phase-3-openai-canary.json) |
| Claude / Anthropic (optional) | Passed with controlled HTTP responses | Not live-validated |
| Grok / xAI (optional) | Passed with controlled HTTP responses | Not live-validated |

One real OpenAI summary request passed using `gpt-4.1-mini-2025-04-14`: 5,228 ms, 564 input tokens and 41 output tokens, with a 512-token output cap. Only synthetic simulator ticket context was sent; no downstream write was requested. Cost remains null because billing was not calculated. This establishes a bounded integration canary, not a quality benchmark. OpenAI is the only required hosted provider; Claude/Grok keys and live canaries are optional. See [setup](PHASE-3-ASSISTANT.md).

Phase 3 is complete for the selected OpenAI + Ollama scope, recorded by the **phase-3** checkpoint. The earlier **phase-3-local** tag remains available for learning. Phase 0A/8A ConnectWise access and Phase 4 MCP transport remain separate work; model comparison and reliability qualification continue in Phases 6 and 7.
