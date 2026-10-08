# Learning checkpoints

Current checkpoint: **phase-3-local**, hosted validation pending.

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

Start Phase 0 with the scope and acceptance documents. For Phase 1 follow LOCAL-SETUP.md at its tag. At Phase 2 use [the workflow guide](PHASE-2-WORKFLOW.md) for prepare → approval → execute → verify. Phase 0A real-platform access remains pending across these local checkpoints.

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
| phase-3-local | AI source selection, four reusable skills, provider adapters and Ollama | 41 regression cases, 5 real local sanity cases and a verified simulator write; hosted canaries pending |
