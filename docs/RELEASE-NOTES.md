# Local simulator workspace release candidate 2

**Delivered:** scoped service context, internal note/time proposals, separate-user approval, idempotent execution/read-back, stdio MCP, optional source-selecting AI, scheduled read-only sync, local monitoring and tested recovery. The operator entry point is [LOCAL-SETUP.md](LOCAL-SETUP.md), followed by [USER-GUIDE.md](USER-GUIDE.md). See [acceptance](ACCEPTANCE-CHECKLIST.md), [handover](HANDOVER.md) and the [manifest](evidence/release-manifest.json).

The current candidate adds a responsive browser workspace and a scoped read-only activity endpoint to the Phase 8 delivery. Workspace regression passed 62 tests and 11 MCP scenarios; eight browser checks and a fresh 11-step installation passed. The Phase 7 workload and recovery reports remain evidence for that qualification. Database migration stays `004_automation.sql`; there is no destructive schema change. Existing users should preserve `.env` and volumes, take a backup, build candidate images, apply checksum-verified migrations through Compose dependencies, then run smoke/readiness checks. Do not edit previously applied migrations or re-seed to reset an existing user.

Rollback to Phase 6 was tested with the same schema. Retain the current images and a verified data snapshot before future changes; image recreation alone cannot reverse a destructive migration. The [operations runbook](OPERATIONS-RUNBOOK.md) covers the tested rollback/restore boundary.

## Version and license inventory

Python and npm dependency versions are locked in `backend/requirements.lock` and `client/package-lock.json`; base images use SHA-256 digests. [Phase 8 dependency metadata](evidence/release-dependencies.json) records the installed Python distributions, npm lock entries and image IDs at that checkpoint. The workspace adds no package dependency; rebuilding it changes application image IDs. Locally built image IDs are not published registry digests. This inventory excludes operating-system packages and does not claim a security scan or comprehensive license clearance.

The local model is pinned Qwen3 0.6B Q4_K_M with the manifest/layer identities in `contracts/local-model.json`. Its Apache-2.0 license is archived verbatim from the pinned model's own license layer at [QWEN3-APACHE-2.0.txt](licenses/QWEN3-APACHE-2.0.txt), with a matching hash in the dependency record. The upstream [Qwen license source](https://huggingface.co/Qwen/Qwen3-0.6B/blob/main/LICENSE) was checked on 2026-10-08. Third-party terms remain with their respective packages/images; original project materials are covered by the restrictive root [LICENSE](../LICENSE); [third-party licenses](../THIRD-PARTY-NOTICES.md) remain unchanged. The repository is public; its restrictive license remains in effect.

The selected hosted model is `gpt-4.1-mini-2025-04-14`; no hosted model weights are included. Anthropic/xAI have contract-tested optional adapters but no live validation. Prompt `evidence-selector-1.1.0`, selection schema `selection-1.0.0`, skills `1.0.0`, consumer contract `1.0.0`, SDK `1.32.1` and negotiated MCP `2025-11-25` remain unchanged.

## Boundaries and next gates

This candidate is local/simulator-ready. ConnectWise access, exact official tenant contracts and real write acceptance are pending Phase 8A. Azure provisioning and cloud-runtime acceptance are pending Phase 9. The [Azure plan](../deploy/AZURE-PLAN.md) creates no resources and identifies code/configuration work that is still needed. Synthetic account provisioning and the local filesystem alert inbox are not production identity/paging solutions.

Phase 6 evidence describes eight frozen cases per provider. Phase 7's two-minute soak is deliberately small; neither is a general production guarantee. Human productivity savings and complete operating costs have not been measured. Reproduce prior frozen evaluations from their tagged checkpoint; regenerate affected evidence after runtime/policy/model changes.
