# Human review page

FastAPI serves a small native HTML/CSS/JavaScript page at `/`. Its job is to let a separate authorized person inspect and approve a specific MCP proposal, then inspect or reconcile its receipt. It is not a ticket dashboard. Preparation and execution are performed through the TypeScript MCP reference client.

A direct link `/?proposal=PROPOSAL_ID` opens the lookup after login. The scoped `/workspace/proposals/{id}` endpoint returns the current proposal, approval and operation status; the existing domain context endpoint provides source notes. The page shows proposer, ticket, exact payload and hash, source hash, expiry, approver and resulting external ID. Approval still calls the domain API, which checks separate identity, payload hash, freshness and scope. The browser can verify an existing uncertain operation; this is read-back, never a second write. The older `/workspace/activity` endpoint remains available for clients that use it.

Source text is rendered with `textContent`. Bearer tokens live only in page memory and are cleared on sign-out or identity switch. A restrictive CSP prevents inline scripts and framing. The dialog and form have keyboard labels, errors remain visible, and the two review panels stack at mobile widths.

[Actual approval capture](showcase/review-approval.png) · [Verified receipt](showcase/review-verified.png) · [Unknown recovery](showcase/review-recovered.png) · [Mobile review](showcase/review-mobile.png)

## Acceptance

[Browser/MCP acceptance](evidence/workspace-browser.json) exercises actual stdio MCP tool discovery/context/proposal/execution/verification, the offline viewer and its mobile layout, browser approval, time entry, unknown recovery, tenant switch, sign-out and storage. The simulator count independently checks one downstream effect after recovery. [Domain regression](evidence/workspace-regression.json) covers direct endpoint roles/scopes, as well as the other workflow controls. No hosted model or live tenant is used.

To reproduce from a fresh clone, install Node.js 22, Python 3.12 and Docker Engine with Linux containers and Compose v2. The root [npm lockfile](../package-lock.json) pins Playwright; [the browser Compose overlay](../compose.browser.yaml) is committed. Port 8031 must be free on loopback. Run these commands from the repository root:

```sh
npm ci
npx playwright install chromium
python scripts/test_local.py
docker compose --env-file .env.example -p cw-ops-ui-test -f compose.test.yaml -f compose.browser.yaml up -d --no-build --wait api
npm run test:browser
docker compose --env-file .env.example -p cw-ops-ui-test -f compose.test.yaml -f compose.browser.yaml down --remove-orphans
```

Use `npx playwright install --with-deps chromium` on a fresh Linux machine when browser system libraries are missing. Always run the final `down` command, including after a test failure. The script uses only synthetic credentials and an isolated stack. It regenerates the [offline MCP evidence viewer](showcase/mcp-evidence.html), [screenshots](showcase/README.md), and its [JSON report](evidence/workspace-browser.json), which records the Playwright and Chromium versions. The viewer is a presentation of recorded tool responses, not a live MCP host. The Phase 7 workload/restore/OOM results are a separate prior qualification; Azure and connected ConnectWise acceptance remain pending.
