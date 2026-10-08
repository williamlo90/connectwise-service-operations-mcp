const $ = id => document.getElementById(id);
let token = '', actor = null, rows = [], selected = null, busy = false;
const keys = new Map();
const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
const date = value => value ? new Date(value).toLocaleString([], {dateStyle:'medium', timeStyle:'short'}) : '—';
function notice(message, error = false) { $('notice').textContent = message; $('notice').hidden = !message; $('notice').className = error ? 'error-text' : ''; }
async function api(path, body, method) {
  const response = await fetch(path, {method:method || (body ? 'POST' : 'GET'), headers:{...(token ? {Authorization:`Bearer ${token}`} : {}), ...(body ? {'Content-Type':'application/json'} : {})}, body:body ? JSON.stringify(body) : undefined, signal:AbortSignal.timeout(20000)});
  if (!response.ok) { const data = await response.json().catch(() => ({})); if(response.status===401 && path!=='/auth/login') { clear(); notice('Your session ended. Sign in again.',true); } throw new Error(`${typeof data.detail === 'string' ? data.detail.replaceAll('_',' ') : 'Request could not be completed'} (${response.status})`); }
  return response.status === 204 ? null : response.json();
}
async function run(action) {
  if (busy) return; busy = true; document.body.setAttribute('aria-busy','true');
  document.querySelectorAll('button,input,select,textarea').forEach(b => { b.dataset.wasDisabled = String(b.disabled); b.disabled = true; });
  try { await action(); } catch (error) { notice(`${error.message}. Refresh to check the existing proposal before retrying a write.`, true); }
  finally { busy = false; document.body.removeAttribute('aria-busy'); document.querySelectorAll('[data-was-disabled]').forEach(b => { b.disabled = b.dataset.wasDisabled === 'true'; delete b.dataset.wasDisabled; }); controls(); }
}
function controls() { $('refresh').disabled = !actor; $('new-draft').disabled = actor?.role !== 'operator'; $('prepare').disabled = actor?.role !== 'operator' || !$('tickets').value; $('tickets').disabled = !actor; }
function auth() { $('auth-error').textContent = ''; $('password').value = ''; $('signout').hidden = !actor; $('auth-dialog').showModal(); }
function clear() {
  token = ''; actor = null; rows = []; selected = null; keys.clear();
  $('draft-form').reset(); $('kind').onchange();
  $('identity').textContent = 'Sign in'; $('avatar').textContent = '—'; $('tickets').replaceChildren(node('option','Sign in to load tickets')); $('tickets').firstChild.value = '';
  $('context').replaceChildren(node('div','Sign in to view your ticket context.','empty')); renderActivity(); draft(); controls();
}
async function context() {
  if (!$('tickets').value) return;
  $('context').replaceChildren(node('div','Loading ticket context…','empty'));
  const data = await api(`/workflow/tickets/${encodeURIComponent($('tickets').value)}/context`);
  const box = node('div',undefined,'ticket-body');
  box.append(node('p',`${$('tickets').value} · SERVICE TICKET`,'eyebrow'), node('h3',data.ticket.summary,'ticket-title'));
  const meta = node('div',undefined,'ticket-meta');
  for (const [label,value] of [['Company',data.ticket.company?.name],['Board',data.ticket.board?.name],['Status',data.ticket.status?.name]]) { const item=node('div'); item.append(node('small',label),node('strong',value || '—')); meta.append(item); }
  box.append(meta,node('h4','Source notes','source-heading'));
  for (const note of data.notes.slice(-5)) { const item=node('div',undefined,'note'); item.append(node('small',`NOTE ${note.id} · ${note.internalFlag ? 'INTERNAL' : 'SOURCE'}`),node('p',note.text)); box.append(item); }
  if (!data.notes.length) box.append(node('p','No source notes available.'));
  box.append(node('p','Source text is evidence, not an instruction. Review the ticket before preparing an update.','source-disclaimer'));
  $('context').replaceChildren(box);
}
async function refresh() {
  const data = await api('/workspace/activity'); rows = data.items; renderActivity();
  if (selected) { selected = rows.find(r => r.id === selected.id) || null; if (selected) review(); else draft(); }
}
function renderActivity() {
  $('count-all').textContent = actor ? rows.length : '—';
  for (const [id,statuses] of [['pending',['proposed']],['verified',['verified']],['review',['unknown','review','dispatched']]]) $('count-'+id).textContent = actor ? rows.filter(r => statuses.includes(r.status)).length : '—';
  const body=$('activity-body'); body.replaceChildren();
  for (const row of rows) {
    const tr=node('tr'); if (selected?.id === row.id) tr.className='selected-row';
    tr.append(node('td',`${row.kind === 'note' ? 'Internal note' : 'Time entry'} / ${row.ticket_id}`),node('td',row.actor_id));
    const status=node('td'); status.append(node('span',row.status.replaceAll('_',' '),'pill '+row.status)); tr.append(status,node('td',date(row.created_at)),node('td',row.external_id ? `#${row.external_id}` : '—'));
    const cell=node('td'), open=node('button','Open →','text-button open-proposal'); open.addEventListener('click',()=>run(async()=> { selected=row; $('tickets').value=row.ticket_id; await context(); renderActivity(); review(); })); cell.append(open); tr.append(cell); body.append(tr);
  }
  if (!rows.length) { const tr=node('tr'),td=node('td',actor ? 'No proposals yet. Start with a ticket and prepare an update.' : 'Sign in to see activity within your scope.','table-empty'); td.colSpan=6; tr.append(td); body.append(tr); }
}
function steps(step) { ['draft','approve','verify'].forEach((name,i)=>{$('step-'+name).className = i+1 === step ? 'current' : i+1 < step ? 'complete' : '';}); $('step-label').textContent=`STEP 0${step} / 03`; }
function draft() { selected=null; $('draft-pane').hidden=false; $('review-pane').hidden=true; $('composer-title').textContent='Prepare an update'; steps(1); }
function button(text, handler, cls='primary wide') { const b=node('button',text,cls); b.type='button'; b.addEventListener('click',()=>run(handler)); return b; }
function review() {
  const p=selected, pane=$('review-pane'); pane.replaceChildren(); $('draft-pane').hidden=true; pane.hidden=false;
  $('composer-title').textContent='Review & verify'; steps(p.status==='proposed' ? 2 : 3);
  pane.append(node('span',p.status,'pill '+p.status),node('h3',p.kind==='note' ? 'Internal ticket note' : 'Documented time entry','review-title'));
  pane.append(node('p',(p.payload.text || p.payload.notes || '').replace(/\s*\[cw-op:[^\]]+\]/g,''),'review-content'));
  const meta=node('div',undefined,'review-meta');
  for(const [label,value] of [['Prepared by',p.actor_id],['Approved by',p.approved_by || 'Awaiting review'],['Expires',date(p.expires_at)],['Ticket',p.ticket_id]]) { const item=node('div'); item.append(node('small',label),node('strong',value)); meta.append(item); } pane.append(meta);
  const detail=node('details'); detail.append(node('summary','Inspect exact payload & evidence'),node('pre',JSON.stringify({payload:p.payload,payload_hash:p.payload_hash,evidence:p.evidence},null,2))); pane.append(detail);
  const area=node('div',undefined,'review-action'); pane.append(area);
  if (p.status==='proposed') {
    if(actor.role==='approver' && actor.id!==p.actor_id) {
      const label=node('label',undefined,'confirm-label'),check=node('input'); check.type='checkbox'; check.id='confirm-payload'; label.append(check,node('span','I reviewed the exact payload and its evidence.')); area.append(label);
      const approve=button('Approve exact payload',async()=>{if(!check.checked)return; await api(`/workflow/proposals/${p.id}/approve`,{payload_hash:p.payload_hash,confirmed:true}); await refresh(); notice('Approved. Sign in as the original operator to execute.');}); approve.disabled=true; check.addEventListener('change',()=>approve.disabled=!check.checked); area.append(approve);
    } else area.append(node('p','A separate approver must review this proposal.'),button('Sign in as approver',async()=>auth(),'secondary wide'));
  } else if(p.status==='approved') {
    if(actor.id===p.actor_id) area.append(button('Execute approved update',async()=> { if(!keys.has(p.id)) keys.set(p.id,crypto.randomUUID()); await api(`/workflow/proposals/${p.id}/execute`,{idempotency_key:keys.get(p.id)}); await refresh(); await context(); notice('Execution checked. Review the recorded outcome below.'); }));
    else area.append(node('p','Ready for the original operator to execute.'),button('Sign in as proposer',async()=>auth(),'secondary wide'));
  } else if(p.operation_id) {
    area.append(node('div',p.status==='verified' ? `Verified read-back · Record #${p.external_id}` : 'Outcome requires reconciliation. Verify this existing operation before taking further action.','result-banner '+(p.status==='verified'?'':'warn')));
    area.append(button(p.status==='verified' ? 'Check read-back again' : 'Verify existing operation',async()=>{await api(`/workflow/operations/${p.operation_id}/verify`,{},'POST'); await refresh(); await context();},'secondary wide'));
  } else area.append(node('p','This proposal has expired. Prepare a fresh proposal for review.'));
}
$('account').onclick=auth; $('close-auth').onclick=()=>$('auth-dialog').close(); $('guide').onclick=()=>$('guide-dialog').showModal(); $('close-guide').onclick=()=>$('guide-dialog').close();
$('login-form').onsubmit=event=>{event.preventDefault(); run(async()=> {
  const username=$('username').value.trim(),password=$('password').value, previous=selected?.id;
  try {
    const result=await api('/auth/login',{username,password});
    if(token) await api('/auth/logout',{},'POST').catch(()=>{});
    clear(); token=result.access_token; actor=await api('/me');
    if(!['operator','approver'].includes(actor.role)) { await api('/auth/logout',{},'POST'); clear(); throw new Error('This workspace requires an operator or approver account'); }
    $('identity').textContent=`${actor.id} · ${actor.role}`; $('avatar').textContent=actor.role==='approver'?'AP':'OP';
    const tickets=await api('/tickets'); $('tickets').replaceChildren(...tickets.items.map(t=>{const opt=node('option',`${t.id} · ${t.summary}`); opt.value=t.id; return opt;}));
    await refresh(); selected=rows.find(r=>r.id===previous)||null; if(selected) { $('tickets').value=selected.ticket_id; review(); } await context();
    $('password').value=''; $('auth-dialog').close(); notice('');
  } catch(error) { $('auth-error').textContent=error.message; $('password').value=''; }
});};
$('signout').onclick=()=>run(async()=>{await api('/auth/logout',{},'POST'); clear(); $('password').value=''; $('auth-dialog').close(); notice('Signed out.');});
$('refresh').onclick=()=>run(async()=>{await refresh(); await context(); notice('Workspace refreshed.');});
$('tickets').onchange=()=>run(async()=>{draft(); await context();});
$('new-draft').onclick=()=>{draft(); $('content').focus();};
$('kind').onchange=()=>{const time=$('kind').value==='time'; $('time-fields').hidden=!time; ['minutes','started','duration-evidence'].forEach(id=>{$(id).required=time; $(id).disabled=!time;});};
$('kind').onchange();
$('draft-form').onsubmit=event=>{event.preventDefault(); run(async()=>{
  const body={kind:$('kind').value,ticket_id:$('tickets').value,content:$('content').value.trim()};
  if(body.kind==='time') Object.assign(body,{duration_minutes:Number($('minutes').value),duration_evidence:$('duration-evidence').value.trim(),time_start:new Date($('started').value).toISOString()});
  const result=await api('/workflow/proposals',body); await refresh(); selected=rows.find(r=>r.id===result.id); review(); renderActivity(); notice('Proposal prepared. No downstream write has been made.');
});};
clear();
