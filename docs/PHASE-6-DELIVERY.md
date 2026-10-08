# Phase 6 — evaluated service operations

Status: **complete for the frozen synthetic local/simulator evaluation**. Both provider profiles met the predeclared 7/8 completion gate with **8/8 correct evaluation cases** and no observed critical violation. The evaluated prompt is `evidence-selector-1.1.0`; the domain renderer always discloses that incident resolution is not independently verified.

| Metric | Ollama / pinned Qwen3 0.6B | OpenAI GPT-4.1 mini snapshot |
| --- | --- | --- |
| Frozen evaluation cases correct | 8/8 | 8/8 |
| Development cases correct | 3/4 | 4/4 |
| Median assistant response, N=8 | 16.841 s | 1.346 s |
| Median complete draft workflow, N=5 | 16.258 s | 1.693 s |
| p95 complete draft workflow, N=5 | 17.841 s | 1.756 s |
| Model cost estimate for 8 evaluation cases | Not estimated | US$0.0019884 |

OpenAI was faster on this workstation and dataset. The local profile completed all evaluation cases, while one development summary abstained; local abstention remains a visible outcome requiring review, not a successful draft. These small synthetic samples do not establish production accuracy or latency guarantees. The p95 values use nearest rank and equal the maximum for N=5.

The matched scripted direct-API baseline had a median of **0.346 s** across five draft tasks. It used the same supplied technician text and required fields, separate synthetic approver, execute and read-back. Inference increased software elapsed time. Human composition/review time and human corrections were not measured; there is no claimed labor saving or customer ROI. AI remains an optional evidence-selection layer over deterministic business controls.

All **8/8 negative checks** passed. The suite verified **19 simulator writes** across development/evaluation provider workflows and the five direct baselines, with matching tenant/ticket, visibility, content, member/work mappings and explicit duration fields; no duplicate effect was observed. Grounded facts retain source references. Separate API/MCP/worker regression passed **57 backend/evaluator tests plus 11 MCP scenarios**, including unknown outcomes, stale approval, cross-tenant denial and process interruption.

The final run made 12 real OpenAI generations; its four rejection checks failed before inference. The final-run model cost estimate was **US$0.0029676**, using reported usage and uncached list prices, not invoice totals. Total authorized evaluation spend remained below US$0.50. Ollama ran with a two-CPU / 1.5 GiB cap and no hosted fallback. The evaluation stack was removed; the project's scheduled sync worker remains separate.

Evidence: [case results and provenance](evidence/phase-6-quality.json), [metrics](evidence/phase-6-metrics.json), [persisted read-back records](evidence/phase-6-readbacks.json), [regression](evidence/phase-6-regression.json). See the [frozen protocol](PHASE-6-EVALUATION.md) and [critical-control coverage](PHASE-6-CONTROL-COVERAGE.md) for denominators, acceptance rules and scope. Pricing source: [official model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini), checked 2026-10-08.

Checkpoint: **phase-6**. Next: Phase 7 reliability, security and performance qualification. Real ConnectWise validation remains Phase 8A.
