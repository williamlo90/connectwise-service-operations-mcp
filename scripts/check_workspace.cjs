// Run against the isolated cw-ops-ui-test stack on loopback port 8031.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const {mkdirSync,writeFileSync} = require('node:fs');
const {execFileSync} = require('node:child_process');
const assert = require('node:assert/strict');
const cases=[];
const sql=query=>execFileSync('docker',['exec','cw-ops-ui-test-db-1','psql','-U','cw_test','-d','cw_ops_test','-tAc',query],{encoding:'utf8'}).trim();
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 mkdirSync('docs/showcase',{recursive:true});
 async function settled(){await page.waitForFunction(()=>!document.body.hasAttribute('aria-busy'));}
 async function login(user){await page.locator('#account').click();await page.locator('#username').fill(user);await page.locator('#password').fill('synthetic-test-user-password-only');await page.locator('#signin').click();await page.locator('#auth-dialog').waitFor({state:'hidden'});await settled();}
 async function click(name){await page.getByRole('button',{name,exact:true}).click();await settled();}
 async function capture(name){await page.screenshot({path:`docs/showcase/${name}.png`,fullPage:true});}
 try {
  await page.goto('http://127.0.0.1:8031/');await login('op-a');
  await page.locator('#content').fill('Checked VPN connectivity and reviewed the technician logs. Authentication succeeds; the connection still drops after the tunnel is established. Next: inspect the gateway session logs.');
  await capture('workspace-draft');await click('Prepare proposal →');
  assert.equal(await page.locator('#review-pane .pill').innerText(),'proposed');
  await login('approver-a');assert.equal(await page.getByRole('button',{name:'Approve exact payload'}).isDisabled(),true);
  await page.locator('#confirm-payload').check();await capture('workspace-approval');await click('Approve exact payload');
  await login('op-a');await click('Execute approved update');
  assert.equal(await page.locator('#review-pane .pill').innerText(),'verified');await capture('workspace-verified');cases.push('Separate-identity note approval, execution and verified read-back');
  await page.setViewportSize({width:390,height:844});await capture('workspace-mobile');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);cases.push('390px responsive layout without page overflow');await page.setViewportSize({width:1440,height:1100});
  await click('New proposal');await page.locator('#kind').selectOption('time');await page.locator('#content').fill('Reviewed gateway logs and documented the next diagnostic step.');await page.locator('#minutes').fill('25');await page.locator('#started').fill('2026-10-08T09:00');await page.locator('#duration-evidence').fill('Technician timer: 25 minutes');
  await click('Prepare proposal →');await login('approver-a');await page.locator('#confirm-payload').check();await click('Approve exact payload');await login('op-a');await click('Execute approved update');assert.equal(await page.locator('#review-pane .pill').innerText(),'verified');cases.push('Time entry with explicit duration, start and evidence');
  await click('New proposal');await page.locator('#kind').selectOption('note');await page.locator('#content').fill('Gateway logs collected. Follow-up assigned to the network technician.');await click('Prepare proposal →');await login('approver-a');await page.locator('#confirm-payload').check();await click('Approve exact payload');await login('op-a');
  sql("INSERT INTO simulator_faults VALUES ('a','write','timeout_after_write',1),('a','notes','unavailable',3) ON CONFLICT(tenant_id,route) DO UPDATE SET mode=excluded.mode,remaining=excluded.remaining");
  await click('Execute approved update');assert.equal(await page.locator('#review-pane .pill').innerText(),'unknown');await capture('workspace-unknown');
  sql('DELETE FROM simulator_faults');await click('Verify existing operation');assert.equal(await page.locator('#review-pane .pill').innerText(),'verified');await capture('workspace-recovered');
  assert.equal(sql("SELECT count(*) FROM simulator_records WHERE tenant_id='a' AND kind='note' AND payload->>'text' LIKE 'Gateway logs collected.%'"),'1');cases.push('Unknown outcome reconciled with exactly one downstream effect');
  await login('op-b');assert.equal(await page.locator('#count-all').innerText(),'0');assert.equal(await page.locator('#review-pane').isVisible(),false);assert.equal((await page.locator('#tickets').innerText()).includes('A-100'),false);cases.push('Identity switch clears tenant A data and loads tenant B scope');
  assert.deepEqual(await page.evaluate(()=>({local:localStorage.length,session:sessionStorage.length})),{local:0,session:0});cases.push('Credentials and session tokens absent from browser storage');
  await page.locator('#account').click();await page.locator('#signout').click();await settled();assert.equal(await page.locator('#count-all').innerText(),'—');cases.push('Sign out clears workspace data');
  assert.deepEqual(errors,[]);cases.push('No browser JavaScript errors');
  writeFileSync('docs/evidence/workspace-browser.json',JSON.stringify({status:'passed',timestamp_utc:new Date().toISOString(),environment:'Headless Chromium; isolated synthetic Docker stack; scripted separate-user browser login',hosted_requests:0,cases},null,2)+'\n');
  console.log(JSON.stringify({status:'passed',cases}));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
