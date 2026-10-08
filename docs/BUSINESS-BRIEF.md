# Service operations with verifiable outcomes

**Owner:** William, portfolio/local-demo operator. **Users:** MSP technicians, service managers and approvers. A real tenant/business owner has not yet been assigned.

Technicians need accurate ticket context and a controlled way to record notes and time. The project puts scoped read/prepare/execute/verify tools behind a TypeScript MCP server and Python domain service. Every consequential write requires a separate authorized approver, fresh source context and read-back. The assistant is an optional evidence-selection layer; deterministic permissions and business rules remain authoritative.

V1 supports scoped ticket context, internal notes, explicit-duration time entries, status/assignment recommendations, scheduled read-only synchronization and recovery of uncertain writes. Recommendations do not change status/assignment. The project does not autonomously close tickets, guess working time, send public customer notes or infer access from natural-language instructions.

The current portfolio case study uses two synthetic tenants and an HTTP PSA simulator. Phase 6 achieved 8/8 held-out cases per provider on a small frozen set. Phase 7 completed 135 deterministic tasks including 33 verified writes, with no observed errors or duplicate effects on that suite. Backup/restore, local alerts, model OOM containment and rollback were exercised. These are engineering results, not measured customer ROI or evidence of live ConnectWise compatibility.

OpenAI's median response was 1.35 seconds versus 16.84 seconds for the local model in the recorded eight-case samples. The matched scripted direct-API baseline was faster than assisted workflows. Human effort and corrections were not measured. Use AI when its source-selection assistance is useful; retain the direct workflow where supplied inputs already suffice.

The [recorded demo](demo/demo.html) shows a normal note/time flow, rejected access/approval and recovery after a lost write response. The [release manifest](evidence/release-manifest.json) binds versions and evidence. Next external gate: obtain a permitted ConnectWise test tenant, reconcile the reference contract, validate read-only access and then approved writes in Phase 8A. Azure deployment remains Phase 9.
