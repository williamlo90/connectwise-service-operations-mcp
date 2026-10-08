# Evaluation protocol

The evaluation compares the pinned Ollama/Qwen3 local profile with OpenAI `gpt-4.1-mini-2025-04-14` on the same synthetic source packets. It measures evidence selection, draft fields, verified simulator writes, software latency and token-based cost estimates. It does not measure human productivity or claim real ConnectWise compatibility.

## Frozen inputs and gates

[Cases](../evaluation/cases-v2.json), [rubric and budget](../evaluation/protocol-v2.json), the independent evaluator and the runner are hashed in [the freeze manifest](../evaluation/freeze-v2.json) before real provider outputs are inspected. Four development families cover VPN, DNS, printing and Wi-Fi. Eight evaluation families cover calendar time zones, UPS battery inspection, file-share permissions, storage quota, certificate chains, offboarding sessions, clock reconciliation and monitoring enrollment. Business families do not cross the split; the application schema is shared.

This is a prospectively frozen synthetic split held back from prompt tuning, not a blind external or randomly sampled benchmark. One observation per provider/case cannot establish a production error rate. If evaluation cases are used to change a prompt/model, retire that split into regression and freeze new cases before making a fresh generalization claim.

Each provider must complete at least **7 of 8 evaluation cases correctly**. Critical acceptance requires no unsupported facts, wrong tenant/visibility, invented duration, duplicate effects or false verified result. A successful summary must include the required evidence IDs and resolution-unknown flag; a successful draft must preserve technician input, ticket context and explicitly supplied time fields. Note/time drafts proceed through separate synthetic proposer/approver identities and the real API/HTTP-adapter/simulator path. An independent database read checks record fields, tenant and side-effect count. Unsafe/incorrect drafts are not executed.

Four additional cases per provider check missing duration, missing technician notes, cross-tenant context and an ungranted worker skill. These should be denied before inference. Existing critical domain, MCP and automation regressions are rerun separately, including the seven project-specific failure categories in the security plan. Forced OOM, sustained load, backups, alert delivery and release rollback remain Phase 7 reliability gates.

The 90-second inference ceiling is a per-request bound, not a p95 SLA. Results distinguish completed, abstained, rejected and failed outcomes. Failure is never retried to select a better result. Dataset, freeze hash, application revision, provider/model/prompt/schema, token usage, status and elapsed times accompany the report.

## Baseline and timing interpretation

Five evaluation draft cases also run as a scripted direct-API baseline using the same pre-supplied technician observations and the same independently specified expected draft. Both baseline and assisted paths use approval, execute and read-back. Provider order alternates between cases. Fixtures are restored before each path so one provider cannot see another provider's generated notes.

The baseline bypasses inference; it does not simulate how long a human takes to compose or review a note. Recorded values are software elapsed time, inference/HTTP wait and approval-to-verification duration. Human active time and human corrections remain null. Synthetic harness approval is not operator review. There is no claimed human time saving, labor reduction or customer ROI; a separately timed human study would be needed for those claims. Percentiles over five matched drafts are descriptive small-sample statistics, not tail-latency qualification.

## Cost, isolation and reproduction

The authorized API ceiling is **US$0.50** across development and final evaluation. Settled requests use metered uncached-price estimates; requests with unknown usage retain their full reservation. The runner reserves US$0.02 for each of at most 16 OpenAI assistant requests (12 intended generations and four pre-inference rejection checks), with no generation retries. Prompts are capped at 16,000 bytes and output at 512 tokens. Only synthetic case data leaves the isolated environment.

Token estimates use the [official GPT-4.1 mini model pricing](https://developers.openai.com/api/docs/models/gpt-4.1-mini), checked 2026-10-08: US$0.40 per million input tokens and US$1.60 per million output tokens. Input is priced as uncached; cached discounts, invoice adjustments and tax are not assumed. Missing usage stays unknown. Local hardware/electricity cost is not estimated.

```sh
python scripts/test_local.py
python scripts/run_evaluation.py
```

The first command runs deterministic regressions and evaluator mutation checks without paid inference. The second explicitly runs the bounded real-provider evaluation. It reads the ignored `.env` key, injects it only into the isolated API container, and creates `cw-ops-eval` with PostgreSQL tmpfs and no host ports. The local model uses the existing pinned artifact volume through a separate, bounded Ollama container; persistent project databases and worker schedules are untouched. No scheduler runs in the evaluation stack.

The runner saves progress in ignored `local/evaluation-output/`, refuses to overwrite an existing report, and removes only the evaluation containers/network at exit. The external model volume remains. It makes no claim of resumable paid calls after process interruption; inspect the saved request/run IDs before any deliberate rerun. Sanitized final reports are published under `docs/evidence/`.
