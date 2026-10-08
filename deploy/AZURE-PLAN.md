# Azure deployment plan — not applied

No subscription, resource group, service, public endpoint or billable cloud resource is created by this document. This is the Phase 8 design appendix, not deployable IaC or a validated cloud architecture. Provisioning remains Phase 9 **after** real ConnectWise acceptance in Phase 8A. The current application rejects connected/production mode and uses local bootstrap credentials; deploying it unchanged would not satisfy those gates.

## Proposed topology and limits

| Component | Intended starting configuration / requirement |
| --- | --- |
| API | Azure Container Apps; one minimum replica, two maximum; initial 0.5 vCPU / 1 GiB per replica, requalify before changing. Authenticated HTTPS only; private/internal ingress until remote identity/access review passes. |
| Sync worker | Separate always-running Container App, one replica, no ingress; initial 0.25 vCPU / 0.5 GiB. Test scheduler locking and restart behavior in Azure. |
| PostgreSQL | Flexible Server on private networking; separate migrator and least-privilege runtime roles; TLS certificate verification and backed-up durable storage. Select region/SKU only after pricing and performance review. |
| Images and secrets | Private Container Registry with immutable digests. Managed identity for registry/Key Vault access, least-privilege grants per service. API alone receives model/platform secrets; worker receives only needed platform/DB access. |
| Monitoring | Structured logs and metrics to Azure Monitor; recipient-configured action group. Trigger and receive an actual test alert before acceptance. Replace the local filesystem inbox with durable cloud delivery. |
| Model | Default cloud pilot should use one explicitly selected approved hosted model, with token/concurrency caps and privacy classification. Do not infer automatic fallback permission. Ollama requires a separately budgeted, tested runtime; desktop CPU timing does not predict Azure timing. |
| MCP | Keep the current stdio host local and connect it to the authorized HTTPS API. A remote MCP listener/OAuth flow is a separate implementation; stdio is not an internet endpoint. |

These resource sizes and replica limits are proposed starting limits, not measured cloud capacity. Container Apps scaling is configured through its scaling rules; an always-on scheduled worker must not disappear at zero replicas. Managed identity grants service access and does not replace end-user authorization. See [scaling](https://learn.microsoft.com/en-us/azure/container-apps/scale-app) and [managed identity](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity), reviewed 2026-10-08.

## Required implementation before provisioning

1. Complete Phase 8A: tenant owner, exact API version/region, API credentials, company/board allowlists, field semantics, read-only canary, approved note/time writes and unknown-outcome recovery. Re-run affected regression/quality/qualification and rebuild the release manifest after adapter changes.
2. Add reviewed production configuration, explicit trusted platform origins, TLS database settings, runtime/migrator DB-role separation, and production user provisioning/session policy. Replace synthetic accounts and simulator with the validated adapter configuration.
3. Choose subscription, region, permitted data residency and approved budget. Generate scoped Bicep/Terraform only after these inputs exist. Use a read-only plan/what-if review before applying. Do not embed credentials in templates, CLI arguments or state exports.
4. Build immutable candidate images; export an SBOM and scan the actual images/dependencies. Assess critical findings before release. Pin migrations and define forward/backward compatibility. Restore a backup before relying on rollback.
5. Implement external alert delivery and storage for operational evidence, retention/deletion controls, readiness/liveness probes and any needed connection pooling. Requalify resource caps, session behavior and shutdown semantics under the real cloud topology.

## Cost, recovery and teardown

Cloud spend is not authorized or incurred by this plan. William must approve a monthly cap and per-provider cap before Phase 9. The deployment plan must enumerate API/worker compute, database/storage/backups, registry, secrets, networking/egress, monitoring ingestion/retention and model usage. Budget alerts at 50/80/100 percent are notifications, not a hard spending stop. Document a manual stop procedure and test enforceable model/request/replica limits. Do not quote desktop model costs as total operating cost.

Proposed initial backup retention is seven days, subject to business/data-residency approval. Define RPO/RTO with the tenant owner rather than borrowing the tiny local restore timing. Flexible Server provides managed backup/restore capabilities; test an isolated restore, table/sequence integrity, application acceptance and external-write reconciliation before cutover. See [Microsoft's backup/restore documentation](https://learn.microsoft.com/en-us/azure/postgresql/backup-restore/concepts-backup-restore), reviewed 2026-10-08. The local simulator backup does not validate Azure point-in-time recovery.

Tag every future resource with project/environment/owner and record immutable IDs. For teardown, pause ingress/writers, reconcile pending operations, preserve approved evidence/backups under retention policy, revoke identities/keys, then remove only the dedicated recorded resource group after owner confirmation. Explicitly list retained backups, registry images and shared resources; never delete shared infrastructure by name pattern.

**Phase 9 acceptance:** real authenticated user workflow, tenant isolation, cloud normal/peak/soak, delivered alert, restore and rollback, measured billing/resources, approved ownership and teardown record. All remain pending.
