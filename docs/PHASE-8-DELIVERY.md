# Phase 8 — local delivery pack

Snapshot: **phase-8**. For the current browser release, see [release notes](RELEASE-NOTES.md) and [workspace validation](WORKSPACE-UI.md).

Status: **local/simulator release candidate ready**. Installation, operator instructions, recorded demonstration, acceptance checklist, support ownership and a release manifest are packaged. No real ConnectWise tenant or Azure deployment is claimed.

The fresh-install check used committed source `e3541f19dde89dec6c0b07ff4609662267f60b0f`, generated new credentials, allocated new named volumes and a dynamic loopback port, and followed the documented start/seed/CLI/MCP/worker/monitor steps. Eleven command steps passed; re-seeding retained seven identities, stop/restart retained data, and the isolated project/volumes were removed. Existing Docker downloads/build cache were reused; this was not a newly provisioned physical machine.

The [recorded demo](demo/demo.html) captures actual CLI/MCP output for five acceptance scenarios: tenant denial, unapproved-write denial, verified internal note, verified explicit-duration time entry and unknown-outcome recovery without duplication. Three simulator writes were verified. No model requests or paid API calls were made. The recording preserves command-completion timing and labels its synthetic scripted approvers.

The [manifest](evidence/release-manifest.json) binds the source snapshot, locked dependency/model/schema/prompt identities and file hashes. Its installation revision and current source revision can differ only without runtime changes. The generator checks that runtime files still match Phase 7 regression and the installed snapshot. It excludes itself and this final explanatory report to avoid a self-reference cycle. Verify with `python scripts/release_manifest.py --verify` from the tagged release checkout.

The application remains the Phase 7 implementation: 60 regression tests, 11 real-protocol MCP cases, 135 bounded-load tasks, backup/restore, alerts, OOM handling and rollback evidence are retained for unchanged runtime behavior. The eight-case provider evaluation remains the frozen Phase 6 result. Delivery scripts were exercised directly; no new business logic, schema migration or model behavior was introduced in Phase 8.

| Deliverable | Location |
| --- | --- |
| Business brief / case study | [BUSINESS-BRIEF.md](BUSINESS-BRIEF.md) |
| Current installation and daily use | [LOCAL-SETUP.md](LOCAL-SETUP.md), [USER-GUIDE.md](USER-GUIDE.md) |
| Replay and raw terminal capture | [HTML](demo/demo.html), [asciicast](demo/service-operations.cast), [transcript](demo/transcript.txt) |
| Acceptance / installation results | [Checklist](ACCEPTANCE-CHECKLIST.md), [installation](evidence/phase-8-installation.json), [demo](evidence/phase-8-demo.json) |
| Recovery / release / model license | [Runbook](OPERATIONS-RUNBOOK.md), [release notes](RELEASE-NOTES.md), [dependency inventory](evidence/release-dependencies.json) |
| Ownership, retention and maintenance | [HANDOVER.md](HANDOVER.md) |
| Azure architecture, limits, secrets, recovery and teardown plan | [AZURE-PLAN.md](../deploy/AZURE-PLAN.md), design only; not applied |

Checkpoint: **phase-8**. Next: Phase 8A requires access to a permitted ConnectWise test tenant and official tenant-specific documentation/credentials. The local demo remains usable while that dependency is pending. Cloud implementation/provisioning stays in Phase 9 after connected acceptance and renewed release qualification.
