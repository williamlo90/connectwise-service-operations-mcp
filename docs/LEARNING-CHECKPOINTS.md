# Learning checkpoints

Current checkpoint: **phase-0**.

| Tag | Learning objective | Verification |
| --- | --- | --- |
| phase-0 | Define scope, dependencies, business rules and acceptance cases | Review planning documents; no application runtime |
| phase-1 | Build authentication, tenant scopes, database migrations and a reference CLI | 10 HTTP tests and TypeScript client smoke |
| phase-2 | Add HTTP simulator, proposals, separate-user approval, verified writes and recovery | 27 HTTP tests, workflow CLI and consumer examples |

Each phase builds on the previous commit. Tags identify completed learning checkpoints; later phases may still be planned in the documents.

```sh
git switch --detach phase-0
git switch -c learning/phase-0
```

Use a clean checkout and save your own work before switching. Return to the latest checkpoint with `git switch main`. For executable checkpoints, start with their own setup guide. Use `python scripts/test_local.py` for an isolated temporary test database. Do not run an older checkpoint against the newer persistent database; phase migrations are forward-only. Use a separate clone/environment when running different phases.
