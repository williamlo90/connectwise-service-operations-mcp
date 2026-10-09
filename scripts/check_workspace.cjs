// Browser acceptance uses the real TypeScript MCP client against cw-ops-ui-test.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {mkdirSync,writeFileSync}=require('node:fs');
const {spawnSync,execFileSync}=require('node:child_process');
const {randomUUID}=require('node:crypto');
const assert=require('node:assert/strict');
const compose=['compose','--env-file','.env.example','-p','cw-ops-ui-test','-f','compose.test.yaml','-f','local/workspace-test.yaml'];
const cases=[];
const sql=query=>execFileSync('docker',['exec','cw-ops-ui-test-db-1','psql','-U','cw_test','-d','cw_ops_test','-tAc',query],{encoding:'utf8'}).trim();
function cli(command,id,input='',key){
 const args=[...compose,'run','--rm','--no-deps','-T','-e','DEMO_USERNAME=op-a','client','--mcp','--workflow',command,id,...(key?[key]:[])];
 const result=spawnSync('docker',args,{input,encoding:'utf8',maxBuffer:1024*1024,timeout:120000});
 if(result.status!==0)throw new Error(`MCP ${command} failed: ${(result.stderr||'').slice(-500)}`);
 const start=result.stdout.indexOf('{\n');if(start<0)throw new Error(`MCP ${command} produced no JSON`);
 return {data:JSON.parse(result.stdout.slice(start)),stdout:result.stdout};
}
function discover(){
 const result=spawnSync('docker',[...compose,'run','--rm','--no-deps','-T','-e','DEMO_USERNAME=op-a','client','--mcp','--tools'],{encoding:'utf8',maxBuffer:1024*1024,timeout:120000});
 if(result.status!==0)throw new Error(`MCP discovery failed: ${(result.stderr||'').slice(-500)}`);
 const start=result.stdout.indexOf('{\n');return JSON.parse(result.stdout.slice(start));
}
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 mkdirSync('docs/showcase',{recursive:true});
 async function settled(){await page.waitForFunction(()=>!document.body.hasAttribute('aria-busy'));}
 async function login(user){await page.locator('#account').click();await page.locator('#username').fill(user);await page.locator('#password').fill('synthetic-test-user-password-only');await page.locator('#signin').click();await page.locator('#auth-dialog').waitFor({state:'hidden'});await settled();}
 async function load(id){await page.locator('#proposal-id').fill(id);await page.locator('#load-proposal').click();await settled();}
 async function approve(id,captureBefore=false){await login('approver-a');await load(id);assert.equal(await page.getByRole('button',{name:'Approve exact payload'}).isDisabled(),true);await page.locator('#confirm-payload').check();if(captureBefore){await page.locator('details summary').click();await capture('review-approval');}await page.getByRole('button',{name:'Approve exact payload'}).click();await settled();assert.equal(await page.locator('#proposal-status').innerText(),'approved');}
 async function capture(name){await page.screenshot({path:`docs/showcase/${name}.png`,fullPage:true});}
 async function terminal(name,title,body){
  const tab=await browser.newPage({viewport:{width:1440,height:950}});
  await tab.setContent('<!doctype html><html lang="en"><meta charset="utf-8"><title>MCP evidence</title><style>body{margin:0;background:#101b19;color:#f1f5ee;font:15px system-ui}.head{padding:34px 44px;border-bottom:1px solid #35514a}small{color:#9ed7bd;letter-spacing:.12em}h1{font-size:26px;margin:8px 0}p{color:#c4d1cb;margin:0}pre{margin:0;padding:36px 44px;white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.5 Consolas,monospace}</style><div class="head"><small>ACTUAL TYPECRIPT REFERENCE CLIENT · STDIO MCP</small><h1 id="title"></h1><p>Isolated synthetic PSA simulator · captured tool response · no live ConnectWise tenant</p></div><pre id="output"></pre>');
  await tab.locator('#title').evaluate((el,value)=>el.textContent=value,title);
  await tab.locator('#output').evaluate((el,value)=>el.textContent=value,body);
  await tab.screenshot({path:`docs/showcase/${name}.png`,fullPage:true});await tab.close();
 }
 try{
  const listed=discover();assert.equal(listed.tools.length,6);
  await terminal('mcp-discovery','Six bounded MCP tools',JSON.stringify({protocol:listed.protocol,server:listed.server,tools:listed.tools.map(t=>({name:t.name,description:t.description}))},null,2));
  cases.push('Real stdio MCP tool discovery returns six tools');
  const source=cli('context','A-100');assert.equal(source.data.ticket.id,100);cases.push('Scoped context returned through real stdio MCP');
  await terminal('mcp-context','Scoped ticket context',source.stdout);
  const note=cli('note','A-100','Checked VPN connectivity and reviewed gateway logs. Customer retest is pending.\n');
  assert.equal(note.data.payload.internalFlag,true);assert.equal(note.data.payload.externalFlag,false);
  await terminal('mcp-proposal','Internal note proposed through MCP',note.stdout);
  await page.goto(`http://127.0.0.1:8031/?proposal=${note.data.id}`);await login('op-a');
  assert.equal(await page.locator('#proposal-status').innerText(),'proposed');
  assert.equal(await page.getByRole('button',{name:'Approve exact payload'}).count(),0);cases.push('Proposer cannot approve own proposal');
  await approve(note.data.id,true);
  const write=cli('execute',note.data.id,'',randomUUID());assert.equal(write.data.status,'verified');
  assert.equal(cli('verify',write.data.id).data.external_id,write.data.external_id);
  await terminal('mcp-verified','Verified downstream read-back',write.stdout);
  await load(note.data.id);assert.equal(await page.locator('#proposal-status').innerText(),'verified');await capture('review-verified');
  cases.push('Separate browser approval and proposer MCP execution with read-back');
  await page.setViewportSize({width:390,height:844});await capture('review-mobile');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);cases.push('390px review layout has no horizontal overflow');
  await page.setViewportSize({width:1440,height:1050});
  const time=cli('time','A-100','Inspected gateway session logs\n25\nSynthetic technician timer: 25 minutes\n2026-10-08T09:00:00+07:00\n');
  await terminal('mcp-time','Documented time proposed through MCP',time.stdout);
  assert.equal(time.data.payload.actualHours,25/60);await approve(time.data.id);
  assert.equal(cli('execute',time.data.id,'',randomUUID()).data.status,'verified');cases.push('Documented time through MCP and browser approval');
  const recovery=cli('note','A-100','Gateway logs collected; network technician assigned to follow up.\n');await approve(recovery.data.id);
  sql("INSERT INTO simulator_faults VALUES ('a','write','timeout_after_write',1),('a','notes','unavailable',3) ON CONFLICT(tenant_id,route) DO UPDATE SET mode=excluded.mode,remaining=excluded.remaining");
  const uncertain=cli('execute',recovery.data.id,'',randomUUID());assert.equal(uncertain.data.status,'unknown');
  await terminal('mcp-unknown','Lost response · unknown outcome',uncertain.stdout);
  await load(recovery.data.id);assert.equal(await page.locator('#proposal-status').innerText(),'unknown');await capture('review-unknown');
  sql('DELETE FROM simulator_faults');await page.getByRole('button',{name:'Verify existing operation'}).click();await settled();
  assert.equal(await page.locator('#proposal-status').innerText(),'verified');await capture('review-recovered');
  await terminal('mcp-recovered','Existing operation recovered',cli('verify',uncertain.data.id).stdout);
  assert.equal(sql(`SELECT count(*) FROM simulator_records WHERE tenant_id='a' AND kind='note' AND payload->>'text' LIKE '%[cw-op:${recovery.data.id}]%'`),'1');
  cases.push('Unknown outcome reconciled with one independent downstream effect');
  await login('op-b');assert.equal(await page.locator('#review').isVisible(),false);await load(note.data.id);
  assert.equal(await page.locator('#review').isVisible(),false);assert.match(await page.locator('#notice').innerText(),/not found/i);
  cases.push('Identity switch clears review and cross-tenant lookup returns no proposal');
  assert.deepEqual(await page.evaluate(()=>({local:localStorage.length,session:sessionStorage.length})),{local:0,session:0});cases.push('No browser storage of tokens or credentials');
  await page.locator('#account').click();await page.locator('#signout').click();await settled();
  assert.equal(await page.locator('#identity').innerText(),'Sign in');assert.equal(await page.locator('#review').isVisible(),false);cases.push('Sign-out clears the review');
  assert.deepEqual(errors,[]);cases.push('No browser JavaScript errors');
  writeFileSync('docs/evidence/workspace-browser.json',JSON.stringify({status:'passed',timestamp_utc:new Date().toISOString(),environment:'Headless Chromium; isolated synthetic Docker stack; TypeScript reference client over stdio MCP',hosted_requests:0,cases},null,2)+'\n');
  console.log(JSON.stringify({status:'passed',cases}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
