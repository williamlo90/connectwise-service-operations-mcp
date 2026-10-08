# Phase 7 — local reliability qualification

**60 backend/evaluator tests and 11 MCP protocol scenarios passed.** The synthetic local release candidate passed the declared desktop workload and recovery checks. The application now emits sanitized downstream timings and provides an optional durable local alert inbox. Business authorization, evidence selection and approval rules remain unchanged; the schema remains at migration `004_automation.sql`.

## Workload and measured results

The [predeclared workload](../evaluation/reliability-protocol.json) used two tenants, three context reads followed by one separately approved note/time write, at most four concurrent tasks, no model inference, and no external platform. All **135/135 tasks** completed correctly with **zero errors and zero dropped work**, including **33 verified writes** with exactly one matching simulator effect each.

| Profile | Duration | Offered / completed | Achieved tasks/s |
| --- | --- | --- | --- |
| Normal | 30 s | 15 / 15 | 0.500 |
| Peak | 30 s | 60 / 60 | 2.000 |
| Short soak | 120 s | 60 / 60 | 0.500 |

The following aggregate distribution combines those three declared profiles. The evidence retains per-profile distributions and individual samples.

| Completed operation | N | p50 | p90 | p95 | p99 |
| --- | --- | --- | --- | --- | --- |
| Context read | 102 | 84.905 ms | 99.682 ms | 112.901 ms | 128.288 ms |
| Internal-note workflow | 17 | 338.751 ms | 388.191 ms | 396.109 ms | 396.109 ms |
| Time-entry workflow | 16 | 351.750 ms | 376.307 ms | 386.250 ms | 386.250 ms |

Nearest-rank percentiles with small samples are descriptive, not a production tail-latency guarantee. Each write workflow includes context, preparation, synthetic separate-user approval, execute/read-back and receipt verification. The report measures those segments separately and records 754 downstream requests linked by correlation ID. HTTP endpoints are synchronous: response time is not a separate fast acknowledgement. Inference and human approval wait are not part of this load test. The backlog test separately injected a 90-second queue age and recorded page-processing and completion timing.

The frozen gates were zero errors/drops/incorrect or duplicate effects, read p95 under 3 seconds and workflow p95 under 10 seconds. The observed result passed these gates. This short desktop soak demonstrates this workload only; it does not establish maximum capacity, long-duration stability or production traffic performance.

## Recovery and security evidence

| Check | Observed result |
| --- | --- |
| Backlog | Two tenant jobs drained through two pages each; local backlog alert firing and resolution persisted. |
| Backup/restore | Real PostgreSQL archive restored into a separate database; all 24 public tables and sequence state matched. Restore plus verification took 1.82 s for the 64,852-byte synthetic archive. |
| Database outage | Readiness returned 503 during a controlled pause; recovered to 200 after resume. Database incident firing and resolved events reached the local inbox. |
| Process OOM containment | Disposable 64 MiB process exited 137 with Docker `OOMKilled=true`; API remained ready. |
| Actual local-model OOM | Pinned Ollama/Qwen runtime under a deliberately insufficient 256 MiB cap was OOM-killed. Assistant returned `failed/provider_unavailable`, created no proposal and used no hosted fallback. |
| Release rollback | Exact `phase-6` source rebuilt, previous API installed against unchanged schema, verified note/replay and permission tests passed; candidate API restored. |
| Permission and recovery regression | API, stdio MCP and worker scope; separate approval; expired identities; unsafe model output/injection; interruption; unknown writes; retries and duplicate prevention run through their existing acceptance paths. New checks cover PII/error redaction and alert delivery/deduplication/resolution. |

There is no V1 browser UI or callback consumer. Delayed/lost HTTP responses and cancelled MCP calls are covered instead. The local alert inbox is the tested notification destination; external pager delivery and whole-host availability are not claimed. No paid model requests were made in Phase 7. The real-provider quality and latency runs remain separately recorded in [Phase 6](PHASE-6-DELIVERY.md); reproduce that frozen evaluation from the `phase-6` checkpoint.

## Environment and reproducibility

Windows host, Intel Core i7-13620H; Docker Desktop Linux engine 29.8.2, 16 visible CPUs and 7.61 GiB engine memory. Other local projects remained running. Qualification containers had no host ports and used a separate tmpfs PostgreSQL database. API/simulator limits were 384 MiB / one CPU each and DB 256 MiB / one CPU. Sampled service memory maxima were approximately 111.4 MiB API, 95.04 MiB DB and 55.6 MiB simulator; these are periodic samples, not continuous peak instrumentation. Model-pressure and process-OOM tests used their separate lower caps.

Run `python scripts/test_local.py` for regression and `python scripts/qualify_local.py` for bounded workload/recovery qualification. The latter removes only its named disposable stack and requires the locally installed pinned model volume. See the [operator runbook](OPERATIONS-RUNBOOK.md) for monitoring, incident response, backup and rollback. Raw local dumps/logs remain ignored; public artifacts contain synthetic measurements, hashes and aggregate metadata.

Evidence: [qualification](evidence/phase-7-qualification.json), [regression](evidence/phase-7-regression.json), [running local monitor](evidence/phase-7-monitor-runtime.json). The local API/worker/monitor are running; the recorded inbox has no active incidents. Checkpoint: **phase-7**. Next: Phase 8 delivery pack. ConnectWise tenant validation remains Phase 8A; cloud deployment remains Phase 9.
