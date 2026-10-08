# Ownership and maintenance

William is the current local-demo owner, credential/config custodian, incident responder and release approver. These are individual portfolio responsibilities, not a staffed support agreement. A ConnectWise tenant owner and cloud account/budget owner must be confirmed before their respective phases. No external recipient or support channel has been configured.

| Cadence / trigger | Required action |
| --- | --- |
| During each local demo session | Check readiness, worker heartbeat, stale sync, queue review and local alert inbox. Investigate unknown writes by operation ID before repeating any action. |
| Weekly while actively developing | Review failure/status clusters and usage, inspect ignored diagnostic files, and keep only useful local logs/dumps. Review dependencies for applicable updates; do not silently move pinned versions. |
| After an incident | Preserve sanitized correlation/operation evidence; identify cause, add a meaningful regression case, test recovery, then update the runbook. |
| After business-rule, permission or adapter changes | Re-run affected API/MCP/worker and reliability checks, review scope, and regenerate the release manifest. |
| After prompt/model/skill changes | Run regression, use development cases, freeze a suitable independent evaluation set before final claims, and record provider/model/prompt versions and cost. |
| Before release / material migration | Take and verify a backup, freeze source/images/dependencies, test upgrade/rollback, and update operator documentation and acceptance evidence. |

Credentials stay in ignored `.env` for this local release. Only the API receives hosted-provider credentials. Do not send credentials through issue descriptions, chat, terminal arguments or demo recordings. Rotating a database password requires updating the database role as well as configuration. Revoke affected sessions/keys after compromise; review external operation outcomes before resuming writes.

The current monitor retains two roughly 5 MiB alert segments plus current metrics/state, with host-operator filesystem access. Database audit/business records have no automatic purge in V1; this is acceptable for the synthetic demo but a documented tenant retention/deletion policy is a prerequisite to real data. Local backups are sensitive, ignored and kept on the operator's disk; they are not off-host disaster recovery. The public evidence set contains only synthetic data, source hashes and measurements.

Local electricity, hardware, support time and full operating cost are unmeasured. Phase 6's final OpenAI evaluation estimate was US$0.0029676 from reported tokens/list prices, not total project cost or an invoice. Running the default deterministic demo/test suite incurs no model API request. Live canaries and assistant commands can incur charges when hosted mode is explicitly enabled.

Open backlog: ConnectWise access and exact contract validation (8A); production identities, trusted platform origins and DB-role/TLS configuration; remote/cloud monitoring; cloud budget/region and Azure acceptance (9); longer workload qualification if actual usage warrants it. No n8n extension is required for this release.
