# Learning checkpoints

Completed phase checkpoint: **phase-8**. The current `main` branch also includes the responsive browser workspace, fresh workspace installation evidence and English portfolio documentation. See the [roadmap](ROADMAP.md) for the next milestone.

| Tag | Learning objective | Verification |
| --- | --- | --- |
| phase-0 | Define scope, dependencies, business rules and acceptance cases | Review planning documents; no application runtime |
| phase-1 | Build authentication, tenant scopes, database migrations and a reference CLI | 10 HTTP tests and TypeScript client smoke |
| phase-2 | Add HTTP simulator, proposals, separate-user approval, verified writes and recovery | 27 HTTP tests, workflow CLI and consumer examples |

Each phase builds on the previous commit. Tags identify completed learning checkpoints; later phases may still be planned in the documents.

```sh
git switch --detach phase-2
git switch -c learning/phase-2
```

Use a clean checkout and save your own work before switching. Return to the latest checkpoint with `git switch main`. For executable checkpoints, start with their own setup guide. Use `python scripts/test_local.py` for an isolated temporary test database. Do not run an older checkpoint against the newer persistent database; phase migrations are forward-only. Use a separate clone/environment when running different phases.

Inspect what each phase adds:

```sh
git log --oneline --decorate
git diff --stat phase-0..phase-1
git diff --stat phase-1..phase-2
```

At the `phase-0` tag, start with its original scope and acceptance documents. For the current English overview, use the [business brief](BUSINESS-BRIEF.md) and [acceptance checklist](ACCEPTANCE-CHECKLIST.md). For Phase 1 follow LOCAL-SETUP.md at its tag. At Phase 2 use [the workflow guide](PHASE-2-WORKFLOW.md) for prepare → approval → execute → verify. Phase 0A real-platform access remains pending across these local checkpoints.

## Get the repository

```sh
git clone https://github.com/williamlo90/connectwise-service-operations-mcp.git
cd connectwise-service-operations-mcp
git switch --detach phase-1
python scripts/test_local.py
```

The repository is private, so GitHub access is required. The test runner creates and removes its own temporary database; run only one checkpoint test runner at a time. For separate persistent demos, use a different Compose project name and API port per phase (for example, set `COMPOSE_PROJECT_NAME=cw-ops-phase-1` and `API_PORT=8031` in that clone's generated `.env`). Merely cloning into a different folder does not isolate the default Compose database volume.

| Additional tag | Scope | Verification |
| --- | --- | --- |
| phase-3-local | AI source selection, four reusable skills, provider adapters and Ollama | 41 regression cases, 5 real local sanity cases and a verified simulator write; hosted validation deferred in this snapshot |
| phase-3 | Required OpenAI + Ollama scope; Claude/Grok optional | Local validation plus one real OpenAI structured summary canary passed |
| phase-4 | Real MCP server/client, scoped tools, separate approval and recovery | 41 regression tests, 11 MCP protocol scenarios, HTTP/MCP CLI, verified note/time writes |
| phase-5 | Scheduled cache sync, durable jobs, bounded retries and review queue | 52 backend tests, 11 MCP scenarios, two-tenant worker runtime and process-crash recovery |
| phase-6 | Frozen quality rubric, family-separated cases and provider/baseline comparison | 8/8 evaluation cases per provider, 57 backend tests, 11 MCP scenarios and independent read-back fields |
| phase-7 | Local alert inbox, telemetry, bounded load, backup/restore and rollback | 60 backend tests, 11 MCP scenarios, 135 tasks / 33 verified writes, actual Ollama OOM safely handled |
| phase-8 | Operator delivery, recorded demo, clean installation and release manifest | 11 installation command steps; 5 CLI/MCP demo cases and 3 verified writes; runtime unchanged from Phase 7 |
