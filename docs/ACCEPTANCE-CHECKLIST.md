# Local release acceptance

Single-operator synthetic/simulator scope. Results link to executable evidence; they do not establish customer ROI or connected compatibility.

| Task | Expected outcome | Result / evidence |
| --- | --- | --- |
| Install from committed source with new credentials/data | Migrations, seed, CLI, MCP, worker/monitor succeed; restart retains records | [Fresh installation record](evidence/phase-8-installation.json) |
| Read tenant A ticket; request tenant B ticket as A | A context available, B denied | [Recorded CLI/MCP demo](evidence/phase-8-demo.json) |
| Execute before approval | Denied, no downstream effect | [Demo](evidence/phase-8-demo.json) |
| Separate-user approval and internal note | Exact private payload, verified external ID | [Demo](evidence/phase-8-demo.json) |
| Explicit 25-minute time entry | Supplied duration preserved, configured mapping and verified read-back | [Demo](evidence/phase-8-demo.json) |
| Lost write response / unavailable first read-back | Unknown status; verify recovers same operation; one effect | [Demo](evidence/phase-8-demo.json) |
| Permission, malicious source, stale approval and interrupted execution | Denial or explicit non-success; no bypass/duplicate on finite suite | [60 regression tests and 11 MCP cases](evidence/phase-7-regression.json) |
| Model evidence selection | Predeclared quality gate met on stated small synthetic set | [8/8 cases per provider, Phase 6](evidence/phase-6-quality.json) |
| Normal/peak/short soak and backlog | Declared latency/error/correctness gates pass | [135 tasks / 33 writes](evidence/phase-7-qualification.json) |
| Backup, DB outage, model OOM and rollback | Restore matches, alerts received, fail closed, previous release works | [Qualification](evidence/phase-7-qualification.json) |
| Immutable delivery inventory | File hashes match candidate/evidence | Run `python scripts/release_manifest.py --verify` |
| Real ConnectWise tenant | Required vendor fields, permissions and outcomes validated | **Pending Phase 8A** |
| Azure deployment | Cloud runtime/access/restore/alert/billing qualification | **Pending Phase 9; nothing provisioned** |

The installation and demo reports state their source revisions. The release manifest also records prior evidence versions; older evidence is retained only for unchanged behavior. Application/schema/model changes must trigger the relevant checks before this checklist is reused for another release.
