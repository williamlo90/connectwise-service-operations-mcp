# Browser workspace

The local Service Ops workspace is served by FastAPI at `/`. It uses native HTML, CSS and JavaScript without a separate frontend runtime or CDN. Docker serves the bundled assets alongside the existing API. No additional service or paid inference is required.

## Design and behavior

The workspace pairs ticket evidence with a three-step prepare/approve/verify flow. A forest-green navigation rail, restrained teal actions, readable metadata and explicit outcome banners keep the demo focused on operations. Desktop uses two panels; mobile stacks them and confines activity-table scrolling to the table.

The browser signs into real local demo identities. Approval still requires a distinct authorized approver, execution still belongs to the proposer, and the server validates the payload/source state. The read-only `/workspace/activity` endpoint limits results to 40 and filters by current tenant/company/board scope. It exposes no new write authority.

Source notes and payloads are rendered as text. Credentials are never embedded or saved in browser storage; bearer tokens remain in page memory. A restrictive content-security policy allows same-origin assets, blocks framing and forbids inline scripts. Switching accounts clears previous context and draft input. HTTP errors remain visible and direct users to inspect the existing operation before retrying a write.

## Validation

- [Regression](evidence/workspace-regression.json): 62 backend/domain/evaluator tests and 11 real-protocol MCP scenarios.
- [Browser acceptance](evidence/workspace-browser.json): eight checks against a disposable PostgreSQL/simulator stack, including real form interactions and separate-user login.
- [Installation](evidence/workspace-installation.json): fresh Git archive and generated credentials; restart persistence and worker/monitor readiness.
- Desktop 1440px and mobile 390px screenshots were visually inspected. [Draft](showcase/workspace-draft.png), [approval](showcase/workspace-approval.png), [verified](showcase/workspace-verified.png), [mobile](showcase/workspace-mobile.png).

The browser recovery test injects a lost write response and unavailable read-back in the isolated simulator. The UI first displays `unknown`, then reconciles the existing operation to `verified`. A direct simulator count confirms one downstream effect. The test makes zero hosted model requests.

The broader Phase 7 workload/restore/OOM results remain the evidence for that earlier qualification; this UI increment does not claim a new load test. Azure and connected ConnectWise acceptance are separate pending work.

## Reproduce browser acceptance

Install Playwright with Chromium in your development environment. Run `python scripts/test_local.py` first to build the isolated test image and verify the domain suite. Create an ignored `local/workspace-test.yaml` overlay:

```yaml
services:
  api:
    image: cw-ops-test-api
    ports: ['127.0.0.1:8031:8000']
  migrate:
    image: cw-ops-test-api
  seed:
    image: cw-ops-test-api
  simulator:
    image: cw-ops-test-api
```

```sh
docker compose --env-file .env.example -p cw-ops-ui-test -f compose.test.yaml -f local/workspace-test.yaml up -d --no-build --wait api
node scripts/check_workspace.cjs
docker compose --env-file .env.example -p cw-ops-ui-test -f compose.test.yaml -f local/workspace-test.yaml down --remove-orphans
```

Use a fresh test stack for each run. The script deliberately targets only `cw-ops-ui-test` and fixed synthetic test credentials, and regenerates browser evidence/screenshots. Set `PLAYWRIGHT_MODULE` to the installed module path if it is not on Node's normal search path. The production demo's data and credentials are not used.
