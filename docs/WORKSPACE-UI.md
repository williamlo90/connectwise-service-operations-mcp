# Human review page

FastAPI serves a small native HTML/CSS/JavaScript page at `/`. Its job is to let a separate authorized person inspect and approve a specific MCP proposal, then inspect or reconcile its receipt. It is not a ticket dashboard. Preparation and execution are performed through the TypeScript MCP reference client.

A direct link `/?proposal=PROPOSAL_ID` opens the lookup after login. The scoped `/workspace/proposals/{id}` endpoint returns the current proposal, approval and operation status; the existing domain context endpoint provides source notes. The page shows proposer, ticket, exact payload and hash, source hash, expiry, approver and resulting external ID. Approval still calls the domain API, which checks separate identity, payload hash, freshness and scope. The browser can verify an existing uncertain operation; this is read-back, never a second write. The older `/workspace/activity` endpoint remains available for clients that use it.

Source text is rendered with `textContent`. Bearer tokens live only in page memory and are cleared on sign-out or identity switch. A restrictive CSP prevents inline scripts and framing. The dialog and form have keyboard labels, errors remain visible, and the two review panels stack at mobile widths.

[Actual approval capture](showcase/review-approval.png) · [Verified receipt](showcase/review-verified.png) · [Unknown recovery](showcase/review-recovered.png) · [Mobile review](showcase/review-mobile.png)

## Acceptance

[Browser/MCP acceptance](evidence/workspace-browser.json) exercises actual stdio MCP tool discovery/context/proposal/execution/verification, the offline viewer and its mobile layout, browser approval, time entry, unknown recovery, tenant switch, sign-out and storage. The simulator count independently checks one downstream effect after recovery. [Domain regression](evidence/workspace-regression.json) covers direct endpoint roles/scopes, as well as the other workflow controls. No hosted model or live tenant is used.

To reproduce the browser run, install Playwright with Chromium and run `python scripts/test_local.py` first to build the isolated images. Create an ignored `local/workspace-test.yaml`:

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

Set `PLAYWRIGHT_MODULE` to your installed Playwright module path if it is not discoverable by Node. The script uses only synthetic credentials and an isolated stack. It regenerates the [offline MCP evidence viewer](showcase/mcp-evidence.html), [screenshots](showcase/README.md), and its JSON report. The viewer is a presentation of recorded tool responses, not a live MCP host. The Phase 7 workload/restore/OOM results are a separate prior qualification; Azure and connected ConnectWise acceptance remain pending.
