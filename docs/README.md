# Documentation

Start with the product and its measured results, then follow the implementation or operating guides as needed.

## Product and portfolio

| Guide | Purpose |
| --- | --- |
| [Product walkthrough](showcase/README.md) | Follow real MCP preparation and execution, browser approval, and recovery |
| [Engineering case study](CASE-STUDY.md) | Understand the problem, contribution and design decisions |
| [Business brief](BUSINESS-BRIEF.md) | Review users, scope and expected operational value |
| [Portfolio copy](PORTFOLIO-COPY.md) | English CV, LinkedIn and interview material |
| [Roadmap](ROADMAP.md) | Completed milestones and the next Azure/vendor validation steps |

## Run and operate

| Guide | Purpose |
| --- | --- |
| [Local setup](LOCAL-SETUP.md) | Install, configure, start and stop the stack |
| [Operator guide](USER-GUIDE.md) | Use the browser, CLI and approval/recovery workflow |
| [Operations runbook](OPERATIONS-RUNBOOK.md) | Monitor, diagnose, back up, restore and roll back |
| [Ownership and maintenance](HANDOVER.md) | Manage credentials, retention and ongoing operation |
| [Release notes](RELEASE-NOTES.md) | Identify current behavior and version boundaries |

## Implementation and integration

| Guide | Purpose |
| --- | --- |
| [Architecture](ARCHITECTURE.md) | Map components, authority and failure handling |
| [Human review page](WORKSPACE-UI.md) | Understand the narrow UI and reproduce browser checks |
| [Six-tool map](MCP-TOOL-MAP.md) | Inputs, outputs, authorization and evidence for each tool |
| [MCP-first walkthrough](MCP-WALKTHROUGH.md) | Follow one recorded synthetic operation end to end |
| [Deterministic workflow](PHASE-2-WORKFLOW.md) | Inspect proposal, approval, execution and verification behavior |
| [MCP server](PHASE-4-MCP.md) | Inspect the tool catalog and stdio protocol contract |
| [Consumer contract](../contracts/MCP-CONSUMERS-V1.md) | Integrate bounded service operations with another consumer |
| [PSA reference subset](../contracts/PSA-SUBSET.md) | Inspect routes, fields, policies and vendor assumptions |
| [AI assistance](PHASE-3-ASSISTANT.md) | Configure optional OpenAI/Ollama source selection |
| [Scheduled synchronization](PHASE-5-AUTOMATION.md) | Understand durable jobs, checkpoints and retries |
| [ConnectWise validation](CONNECTWISE-VALIDATION.md) | Prepare vendor access and connected acceptance |
| [Azure deployment plan](../deploy/AZURE-PLAN.md) | Review the proposed cloud topology and validation requirements |

## Evidence and learning

[Acceptance checklist](ACCEPTANCE-CHECKLIST.md) is the starting point for current results. [Learning checkpoints](LEARNING-CHECKPOINTS.md) maps the preserved Git tags to incremental modules.

- Current workspace: [regression](evidence/workspace-regression.json), [browser acceptance](evidence/workspace-browser.json), [fresh installation](evidence/workspace-installation.json).
- Quality: [evaluation design](PHASE-6-EVALUATION.md), [results](PHASE-6-DELIVERY.md), [control coverage](PHASE-6-CONTROL-COVERAGE.md).
- Reliability: [qualification report](PHASE-7-DELIVERY.md), including workload, backup/restore, alerts, OOM and rollback.
- Delivery: [Phase 8 report](PHASE-8-DELIVERY.md), [CLI/MCP transcript](demo/transcript.txt), [release manifest](evidence/release-manifest.json).

Phase delivery reports describe their tagged snapshots. Current behavior is documented in the guides above; phase tags retain the original learning sequence.
