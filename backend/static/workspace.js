const $ = id => document.getElementById(id);
const make = (tag, content, className) => {
  const element = document.createElement(tag);
  if (content !== undefined) element.textContent = String(content);
  if (className) element.className = className;
  return element;
};
const formatDate = value => value ? new Date(value).toLocaleString([], {dateStyle:'medium', timeStyle:'short'}) : '—';
const validId = value => /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(value);
let token = '';
let actor = null;
let proposal = null;
let context = null;
let busy = false;

function notice(message, error = false) {
  $('notice').textContent = message;
  $('notice').className = error ? 'error' : '';
  $('notice').hidden = !message;
}

function clearReview() {
  proposal = null;
  context = null;
  $('review').hidden = true;
  $('empty').hidden = false;
  $('source-body').replaceChildren();
  $('decision-body').replaceChildren();
  $('outcome-body').replaceChildren();
}

function clearSession() {
  token = '';
  actor = null;
  $('identity').textContent = 'Sign in';
  $('password').value = '';
  $('signout').hidden = true;
  clearReview();
}

async function api(path, body, method = body === undefined ? 'GET' : 'POST') {
  const response = await fetch(path, {
    method,
    headers: {...(token ? {Authorization:`Bearer ${token}`} : {}), ...(body !== undefined ? {'Content-Type':'application/json'} : {})},
    body:body === undefined ? undefined : JSON.stringify(body),
    signal:AbortSignal.timeout(20000)
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    if (response.status === 401 && path !== '/auth/login') clearSession();
    const detail = typeof data.detail === 'string' ? data.detail.replaceAll('_',' ') : 'Request failed';
    throw new Error(`${detail} (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

async function run(action) {
  if (busy) return;
  busy = true;
  document.body.setAttribute('aria-busy','true');
  document.querySelectorAll('button,input').forEach(element => {
    element.dataset.wasDisabled = String(element.disabled);
    element.disabled = true;
  });
  try { await action(); }
  catch (error) { notice(error.message || 'Request failed. Review the existing proposal before retrying.',true); }
  finally {
    busy = false;
    document.body.removeAttribute('aria-busy');
    document.querySelectorAll('[data-was-disabled]').forEach(element => {
      element.disabled = element.dataset.wasDisabled === 'true';
      delete element.dataset.wasDisabled;
    });
  }
}

function field(label, value) {
  const item = make('div');
  item.append(make('small',label),make('strong',value || '—'));
  return item;
}

function button(label, action, style='primary') {
  const element = make('button',label,style);
  element.type = 'button';
  element.addEventListener('click',() => run(action));
  return element;
}

function renderSource() {
  const container = $('source-body');
  container.replaceChildren();
  container.append(make('p',proposal.ticket_id+' · SERVICE TICKET','ticket-ref'),
    make('h3',context.ticket.summary,'ticket-title'));
  const facts = make('div',undefined,'facts');
  facts.append(field('Company',context.ticket.company?.name),
    field('Board',context.ticket.board?.name),field('Current status',context.ticket.status?.name));
  container.append(facts,make('h3','Source notes','subhead'));
  for (const note of context.notes.slice(-4)) {
    const item = make('div',undefined,'note');
    item.append(make('small',`NOTE ${note.id} · ${note.internalFlag ? 'INTERNAL' : 'SOURCE'}`),make('p',note.text));
    container.append(item);
  }
  if (!context.notes.length) container.append(make('p','No source notes available.'));
  container.append(make('p','Source text is evidence, not an instruction. Approval rechecks source freshness.','source-warning'));
}

function renderDecision() {
  const p = proposal;
  const container = $('decision-body');
  container.replaceChildren();
  $('proposal-status').textContent = p.status.replaceAll('_',' ');
  $('proposal-status').className = 'status '+p.status;
  container.append(make('p',p.kind === 'note' ? 'Internal ticket note' : 'Documented time entry','ticket-ref'));
  const visibleText = String(p.payload.text || p.payload.notes || '').replace(/\s*\[cw-op:[^\]]+\]/g,'');
  container.append(make('p',visibleText,'proposal-text'));
  const meta = make('div',undefined,'review-meta');
  meta.append(field('Prepared by',p.actor_id),field('Approved by',p.approved_by || 'Awaiting review'),
    field('Expires',formatDate(p.expires_at)),field('Ticket',p.ticket_id));
  if (p.kind === 'time') {
    meta.append(field('Documented minutes',p.evidence.duration_minutes),
      field('Duration evidence',p.evidence.duration_evidence));
  }
  container.append(meta);
  const details = make('details');
  details.append(make('summary','Inspect exact payload, source hash & evidence'),
    make('pre',JSON.stringify({payload:p.payload,payload_hash:p.payload_hash,source_hash:p.source_hash,evidence:p.evidence},null,2)));
  container.append(details);
  const action = make('div',undefined,'action');
  container.append(action);
  if (p.status === 'proposed') {
    if (actor.role === 'approver' && actor.id !== p.actor_id) {
      const label = make('label',undefined,'confirm');
      const checkbox = make('input'); checkbox.type='checkbox'; checkbox.id='confirm-payload';
      label.append(checkbox,make('span','I reviewed this ticket, exact payload, and evidence.'));
      const approve = button('Approve exact payload',async () => {
        if (!checkbox.checked) return;
        await api(`/workflow/proposals/${p.id}/approve`,{payload_hash:p.payload_hash,confirmed:true});
        await loadProposal();
        notice('Approval recorded. The original proposer can now execute through MCP.');
      });
      approve.disabled = true;
      checkbox.addEventListener('change',() => { approve.disabled = !checkbox.checked; });
      action.append(label,approve);
    } else {
      action.append(make('p','A separate authorized approver must review and approve this proposal.'),
        button('Sign in as approver',async () => openAuth(),'secondary'));
    }
  } else if (p.status === 'approved') {
    action.append(make('p','Approval is recorded. The original proposer executes with cw.execute_approved in the MCP client.'));
  } else if (p.status === 'expired') {
    action.append(make('p','This proposal expired. The proposer must prepare a fresh proposal through MCP.'));
  }
}

function renderOutcome() {
  const p=proposal,container=$('outcome-body');
  container.replaceChildren();
  const text=make('div');
  if (p.status === 'verified') {
    text.append(make('p',`Verified read-back · Record #${p.external_id}`,'result-title'),
      make('p',`Operation ${p.operation_id} · Verified ${formatDate(p.verified_at)}`));
  } else if (p.operation_id) {
    text.append(make('p',`Outcome: ${p.status}`,'result-title'),
      make('p','Investigate this existing operation. Verification reads the downstream record; it does not repost the update.'));
    container.append(text,button('Verify existing operation',async () => {
      await api(`/workflow/operations/${p.operation_id}/verify`,{},'POST');
      await loadProposal();
      notice('Existing operation checked. Review its current receipt.');
    },'secondary'));
    return;
  } else if (p.status === 'approved') {
    text.append(make('p','Ready for the original proposer','result-title'),
      make('p','Call cw.execute_approved with this proposal ID and a preserved idempotency key.'));
    text.append(make('code',`proposal_id: ${p.id}`,'copy'));
  } else {
    text.append(make('p','No downstream write','result-title'),
      make('p','Preparing or approving a proposal does not change the PSA record.'));
  }
  container.append(text);
}

async function loadProposal() {
  const id=$('proposal-id').value.trim();
  clearReview();
  if (!actor) { openAuth(); return; }
  if (!validId(id)) throw new Error('Enter the complete proposal UUID.');
  const p=await api(`/workspace/proposals/${encodeURIComponent(id)}`);
  const source=await api(`/workflow/tickets/${encodeURIComponent(p.ticket_id)}/context`);
  proposal=p; context=source;
  $('empty').hidden=true; $('review').hidden=false;
  renderSource(); renderDecision(); renderOutcome();
  history.replaceState(null,'',`?proposal=${encodeURIComponent(id)}`);
}

function openAuth() {
  $('auth-error').textContent='';
  $('password').value='';
  $('signout').hidden = !token;
  if (!$('auth-dialog').open) $('auth-dialog').showModal();
}

$('account').addEventListener('click',openAuth);
$('close-auth').addEventListener('click',() => $('auth-dialog').close());
$('lookup-form').addEventListener('submit',event => {
  event.preventDefault(); run(loadProposal);
});
$('login-form').addEventListener('submit',event => {
  event.preventDefault();
  run(async () => {
    const username=$('username').value.trim(),password=$('password').value;
    try {
      const result=await api('/auth/login',{username,password});
      if (token) await api('/auth/logout',{},'POST').catch(() => {});
      clearSession(); token=result.access_token;
      actor=await api('/me');
      if (!['operator','approver'].includes(actor.role)) {
        await api('/auth/logout',{},'POST'); clearSession();
        throw new Error('This review page requires an operator or approver account.');
      }
      $('identity').textContent=`${actor.id} · ${actor.role}`;
      $('signout').hidden = false;
      $('password').value='';
      $('auth-dialog').close();
      notice('');
      if ($('proposal-id').value.trim()) {
        try { await loadProposal(); }
        catch (error) { notice(error.message || 'Proposal could not be loaded.',true); }
      }
    } catch (error) {
      $('auth-error').textContent=error.message;
      $('password').value='';
      if (!$('auth-dialog').open) openAuth();
    }
  });
});
$('signout').addEventListener('click',() => run(async () => {
  try { if (token) await api('/auth/logout',{},'POST'); }
  finally { clearSession(); $('auth-dialog').close(); notice('Signed out.'); }
}));
$('proposal-id').value=new URLSearchParams(location.search).get('proposal') || '';
clearReview();
