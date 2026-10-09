# Delivery roadmap

The local application, browser workspace and portfolio delivery are complete. An optional final milestone is an end-to-end Azure deployment using synthetic service operations; it does not block the delivered local simulator scope. Live ConnectWise acceptance can follow when authorized tenant access is available.

## Completed milestones

| Phase | Delivered capability | Entry point |
| --- | --- | --- |
| 0 | Scope, business rules, dependencies and acceptance design | [Learning checkpoints](LEARNING-CHECKPOINTS.md) |
| 1 | Authentication, tenant scope, database and local runtime | [Foundation](PHASE-1-DELIVERY.md) |
| 2 | Stateful simulator, proposals, approval and verified writes | [Workflow](PHASE-2-DELIVERY.md) |
| 3 | Optional AI source selection and reusable skills | [AI assistance](PHASE-3-DELIVERY.md) |
| 4 | Real stdio MCP tools and consumer acceptance | [MCP delivery](PHASE-4-DELIVERY.md) |
| 5 | Scheduled synchronization and durable recovery | [Automation](PHASE-5-DELIVERY.md) |
| 6 | Frozen synthetic provider evaluation | [Quality](PHASE-6-DELIVERY.md) |
| 7 | Local workload, monitoring, restore, OOM and rollback qualification | [Reliability](PHASE-7-DELIVERY.md) |
| 8 | Operator guides, recorded demo and fresh installation | [Delivery](PHASE-8-DELIVERY.md) |
| Workspace | MCP-first browser review and portfolio evidence | [Browser validation](WORKSPACE-UI.md) |

Original phase tags remain available for the learning modules. The current branch adds the workspace and English product documentation to that sequence.

## Optional final extension: Azure validation

Deploy the actual service-operations workflow to Azure with the synthetic PSA simulator. Choose the subscription, region, budget and resource lifecycle before provisioning. Implement the cloud configuration, remote access controls, database TLS/roles, monitoring and reproducible infrastructure described in the [Azure plan](../deploy/AZURE-PLAN.md).

Acceptance must demonstrate the deployed workflow: authenticated scoped context, proposal, separate approval, execution, verified receipt and unknown-outcome recovery. Record cloud health, delivered alerts, restore/rollback, resource usage and teardown. Publish an Azure validation claim only after observing the deployed result.

No Azure resources have been provisioned for this project yet. This milestone does not depend on access to a real ConnectWise tenant.

## Separate milestone: connected ConnectWise acceptance

Obtain authorized PSA documentation and a test tenant, reconcile the pinned reference subset with the actual version and permissions, then run scoped reads and approved note/time writes. Verify read-back semantics and recovery against that tenant before enabling connected use. See [ConnectWise validation](CONNECTWISE-VALIDATION.md).

## Future changes driven by use

Longer workload qualification, broader ticket discovery, remote MCP transport and additional live model providers should follow an explicit use case and their own acceptance criteria. They are not required to run the current deterministic demo.

## Future execution policy

Develop and unit/contract-test changes before reserving a bounded Docker/connected session. Do not rerun or renumber completed phases solely to follow this policy. Local support is already a delivery responsibility; Azure support extends it only if that hosting option is selected.
