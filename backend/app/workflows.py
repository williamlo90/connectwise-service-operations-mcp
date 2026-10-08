"""Deterministic domain workflow; no LLM or MCP transport in Phase 2."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import hashlib
import json
from typing import Literal
from uuid import UUID,uuid4
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field,AwareDatetime,field_validator
from psycopg.types.json import Jsonb
from .db import connection
from .psa import PSA
from .main import Actor,allow,audit

router=APIRouter(prefix='/workflow',tags=['deterministic-workflow-v1'])


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


def scoped(actor,tid,conn=None):
    if conn is None:
        with connection() as c:return scoped(actor,tid,c)
    row=conn.execute('''SELECT t.* FROM tickets t JOIN actor_scopes s ON s.tenant_id=t.tenant_id
     AND s.company_id=t.company_id AND s.board_id=t.board_id
     WHERE t.tenant_id=%s AND t.id=%s AND s.actor_id=%s''',(actor['tenant_id'],tid,actor['id'])).fetchone()
    if not row:raise HTTPException(404,'ticket_not_found')
    return row


def external_id(tid):
    try:return int(tid.split('-',1)[1])
    except (ValueError,IndexError):raise HTTPException(422,'invalid_ticket_reference')


def fresh(psa,actor,tid):
    local=scoped(actor,tid)
    remote=psa.get(f'service/tickets/{external_id(tid)}')
    cfg=psa.config
    try:
        if remote['id']!=external_id(tid) or cfg['company_map'].get(str(remote['company']['id']))!=local['company_id'] or cfg['board_map'].get(str(remote['board']['id']))!=local['board_id']:
            raise HTTPException(409,'downstream_scope_changed')
        if not remote['_info']['lastUpdated']:raise KeyError()
    except (KeyError,TypeError):raise HTTPException(502,'invalid_downstream_schema')
    return remote


@router.get('/tickets/{tid}/context')
def context(tid:str,actor:Actor):
    allow(actor,('operator','approver'))
    return read_context(tid,actor)


def read_context(tid,actor):
    with PSA(actor['tenant_id']) as psa:
        ticket=fresh(psa,actor,tid)
        notes=psa.all(f'service/tickets/{ticket["id"]}/notes')
        company=psa.get(f'company/companies/{ticket["company"]["id"]}')
        board=psa.get(f'service/boards/{ticket["board"]["id"]}')
    # Evidence text is returned as data; no instructions in it are executed.
    return {'ticket':ticket,'company':company,'board':board,'notes':notes,'source_hash':digest(ticket),
        'summary':f'{ticket["summary"]} — {ticket["status"]["name"]}; {company["name"]}.',
        'facts':[{'field':k,'value':ticket[k],'source':f'service/tickets/{ticket["id"]}'} for k in ('summary','company','board','status')],
        'missing_information':['Resolution is not established by this summary.'],
        'mode':'simulator','contract_version':'1.0.0'}


class Strict(BaseModel):model_config=ConfigDict(extra='forbid')


class Prepare(Strict):
    kind:Literal['note','time']
    ticket_id:str=Field(max_length=100)
    content:str=Field(min_length=1,max_length=4000)
    visibility:Literal['internal']='internal'
    duration_minutes:int|None=Field(default=None,ge=1,le=1440,strict=True)
    duration_evidence:str|None=Field(default=None,min_length=1,max_length=1000)
    time_start:AwareDatetime|None=None

    @field_validator('content','duration_evidence')
    @classmethod
    def nonblank(cls,v):
        if v is not None and (not v.strip() or '[cw-op:' in v):raise ValueError('Invalid text')
        return v


@router.post('/proposals',status_code=201)
def prepare(body:Prepare,actor:Actor,request:Request):
    return prepare_proposal(body,actor,request)


def prepare_proposal(body,actor,request,pid=None,transaction=None):
    allow(actor,('operator','approver'))
    with PSA(actor['tenant_id']) as psa:
        ticket=fresh(psa,actor,body.ticket_id)
        if body.kind=='note':
            if any(v is not None for v in (body.duration_minutes,body.duration_evidence,body.time_start)):
                raise HTTPException(422,'note_cannot_contain_time_fields')
            payload={'ticketId':ticket['id'],'text':body.content,'internalAnalysisFlag':True,
                'detailDescriptionFlag':False,'resolutionFlag':False,'internalFlag':True,
                'externalFlag':False,'processNotifications':False}
        else:
            if body.duration_minutes is None or body.duration_evidence is None or body.time_start is None:
                raise HTTPException(422,'documented_duration_and_start_required')
            member=psa.config['member_map'].get(actor['id'])
            if not member:raise HTTPException(422,'member_mapping_required')
            psa.get(f'system/members/{member}')
            start=body.time_start.astimezone(timezone.utc)
            payload={'chargeToId':ticket['id'],'chargeToType':'ServiceTicket','member':{'id':member},
                'workType':{'id':psa.config['work_type_id']},'workRole':{'id':psa.config['work_role_id']},
                'timeStart':start.isoformat(),'timeEnd':(start+timedelta(minutes=body.duration_minutes)).isoformat(),
                'actualHours':float(Decimal(body.duration_minutes)/60),'billableOption':'DoNotBill','notes':body.content,
                'addToDetailDescriptionFlag':False,'addToInternalAnalysisFlag':True,'addToResolutionFlag':False,
                'emailResourceFlag':False,'emailContactFlag':False,'emailCcFlag':False}
        snapshot={'ticket':ticket,'mapping':mapping(psa)}
    pid=pid or uuid4()
    # Recovery marker is visible in the preview and covered by approval's hash.
    payload['text' if body.kind=='note' else 'notes']+=f'\n[cw-op:{pid}]'
    ph=digest(payload);expires=datetime.now(timezone.utc)+timedelta(minutes=30)
    evidence={'duration_minutes':body.duration_minutes,'duration_evidence':body.duration_evidence,
              'source':f'service/tickets/{ticket["id"]}','duration_source':'technician_input' if body.kind=='time' else None}
    from contextlib import nullcontext
    with (nullcontext(transaction) if transaction is not None else connection()) as conn:
        conn.execute('''INSERT INTO proposals (id,tenant_id,actor_id,ticket_id,external_ticket_id,kind,payload,payload_hash,
         source_hash,source_snapshot,evidence,expires_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
         (pid,actor['tenant_id'],actor['id'],body.ticket_id,ticket['id'],body.kind,Jsonb(payload),ph,digest(snapshot),Jsonb(snapshot),Jsonb(evidence),expires))
        audit(conn,actor,'proposal_prepared',request)
    return {'id':pid,'payload':payload,'payload_hash':ph,'evidence':evidence,'expires_at':expires,'status':'proposed'}


def mapping(psa):
    return {k:psa.config[k] for k in ('base_url','company_login','public_key','client_id','company_map','board_map','member_map','work_type_id','work_role_id','timezone')}


def proposal(conn,actor,pid):
    p=conn.execute('SELECT * FROM proposals WHERE tenant_id=%s AND id=%s FOR UPDATE',(actor['tenant_id'],pid)).fetchone()
    if not p:raise HTTPException(404,'proposal_not_found')
    scoped(actor,p['ticket_id'],conn)
    return p


def check_fresh(p,actor,psa):
    if p['expires_at']<=datetime.now(timezone.utc):raise HTTPException(409,'proposal_expired')
    if digest(p['payload'])!=p['payload_hash']:raise HTTPException(409,'proposal_tampered')
    snapshot={'ticket':fresh(psa,actor,p['ticket_id']),'mapping':mapping(psa)}
    if digest(snapshot)!=p['source_hash']:raise HTTPException(409,'stale_proposal')


class Approve(Strict):
    payload_hash:str=Field(pattern=r'^[a-f0-9]{64}$')
    confirmed:Literal[True]


@router.get('/proposals/{pid}')
def preview(pid:UUID,actor:Actor):
    allow(actor,('operator','approver'))
    with connection() as conn:
        p=proposal(conn,actor,pid)
    return {k:p[k] for k in ('id','ticket_id','kind','actor_id','payload','payload_hash','evidence','expires_at')}


@router.post('/proposals/{pid}/approve')
def approve(pid:UUID,body:Approve,actor:Actor,request:Request):
    allow(actor,('approver',))
    with PSA(actor['tenant_id']) as psa,connection() as conn:
        p=proposal(conn,actor,pid)
        if p['actor_id']==actor['id']:raise HTTPException(403,'self_approval_forbidden')
        if p['payload_hash']!=body.payload_hash:raise HTTPException(409,'payload_hash_mismatch')
        check_fresh(p,actor,psa)
        conn.execute('''INSERT INTO approvals (id,tenant_id,proposal_id,actor_id,payload_hash)
          VALUES (%s,%s,%s,%s,%s) ON CONFLICT (proposal_id) DO NOTHING''',(uuid4(),actor['tenant_id'],pid,actor['id'],body.payload_hash))
        audit(conn,actor,'proposal_approved',request)
    return {'proposal_id':pid,'status':'approved'}


class Execute(Strict):idempotency_key:UUID


def receipt(op):
    return {k:op[k] for k in ('id','proposal_id','status','external_id','error_code','created_at','verified_at')}


@router.post('/proposals/{pid}/execute')
def execute(pid:UUID,body:Execute,actor:Actor,request:Request):
    allow(actor,('operator','approver'))
    with PSA(actor['tenant_id']) as psa,connection() as conn:
        # Serialize key and proposal independently. A dispatched operation is never posted twice.
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(actor['tenant_id']+str(body.idempotency_key),))
        p=proposal(conn,actor,pid)
        if actor['id']!=p['actor_id']:raise HTTPException(403,'only_proposer_can_execute')
        existing=conn.execute('SELECT * FROM operations WHERE tenant_id=%s AND idempotency_key=%s',(actor['tenant_id'],body.idempotency_key)).fetchone()
        if existing and existing['proposal_id']!=pid:raise HTTPException(409,'idempotency_conflict')
        existing=existing or conn.execute('SELECT * FROM operations WHERE proposal_id=%s',(pid,)).fetchone()
        if existing:return receipt(existing)
        approval=conn.execute('''SELECT ap.*,a.active,a.role FROM approvals ap JOIN actors a ON a.id=ap.actor_id
            WHERE ap.proposal_id=%s''',(pid,)).fetchone()
        if not approval or not approval['active'] or approval['role']!='approver' or approval['payload_hash']!=p['payload_hash']:
            raise HTTPException(403,'valid_approval_required')
        scoped({'tenant_id':actor['tenant_id'],'id':approval['actor_id']},p['ticket_id'],conn)
        check_fresh(p,actor,psa)
        oid=p['id'];payload=dict(p['payload'])
        conn.execute('''INSERT INTO operations (id,tenant_id,proposal_id,idempotency_key,request_hash,status,expected)
            VALUES (%s,%s,%s,%s,%s,'dispatched',%s)''',(oid,actor['tenant_id'],pid,body.idempotency_key,p['payload_hash'],Jsonb(payload)))
        audit(conn,actor,'operation_dispatched',request)
        conn.commit()  # Durable BEFORE external request; crashes recover by read-only reconciliation.
        path=f'service/tickets/{p["external_ticket_id"]}/notes' if p['kind']=='note' else 'time/entries'
        response=psa.post(path,payload)
        conn.execute("UPDATE operations SET external_id=%s,status='unknown',error_code=%s WHERE id=%s",
            (response['id'] if response else None,None if response else 'dispatch_outcome_unknown',oid))
    return verify_operation(oid,actor,request)


def verify_operation(oid,actor,request):
    with connection() as conn:
        op=conn.execute('SELECT * FROM operations WHERE tenant_id=%s AND id=%s FOR UPDATE',(actor['tenant_id'],oid)).fetchone()
        if not op:raise HTTPException(404,'operation_not_found')
        p=proposal(conn,actor,op['proposal_id'])
        if op['status']=='verified':return receipt(op)
        with PSA(actor['tenant_id']) as psa:
            try:
                fresh(psa,actor,p['ticket_id'])
                if op['external_id'] is not None:
                    path=f'service/tickets/{p["external_ticket_id"]}/notes/{op["external_id"]}' if p['kind']=='note' else f'time/entries/{op["external_id"]}'
                    candidates=[psa.get(path)]
                else:
                    field='text' if p['kind']=='note' else 'notes'
                    path=f'service/tickets/{p["external_ticket_id"]}/notes' if p['kind']=='note' else 'time/entries'
                    params=None if p['kind']=='note' else {'conditions':f'chargeToId={p["external_ticket_id"]} AND chargeToType="ServiceTicket"'}
                    candidates=[r for r in psa.all(path,params) if f'[cw-op:{oid}]' in r.get(field,'')]
                if len(candidates)==1 and all(candidates[0].get(k)==v for k,v in op['expected'].items()):
                    state='verified';code=None;observed=candidates[0];eid=observed['id']
                else:
                    state='review' if candidates else 'unknown';code='readback_mismatch' if candidates else 'no_unique_evidence';observed=candidates;eid=op['external_id']
            except HTTPException as exc:
                # Preserve permission errors; never return inaccessible record evidence.
                if exc.status_code in (403,409):raise
                state='unknown';code='readback_unavailable';observed=None;eid=op['external_id']
        op=conn.execute('''UPDATE operations SET status=%s,error_code=%s,external_id=%s,observed=%s,
          verified_at=CASE WHEN %s='verified' THEN now() ELSE NULL END WHERE id=%s RETURNING *''',
          (state,code,eid,Jsonb(observed),state,oid)).fetchone()
        audit(conn,actor,'operation_'+state,request)
        return receipt(op)


@router.post('/operations/{oid}/verify')
def verify(oid:UUID,actor:Actor,request:Request):
    allow(actor,('operator','approver'))
    return verify_operation(oid,actor,request)


class Recommend(Strict):
    status_id:int|None=None
    member_id:int|None=None


@router.post('/tickets/{tid}/recommend')
def recommend(tid:str,body:Recommend,actor:Actor):
    allow(actor,('operator','approver'))
    with PSA(actor['tenant_id']) as psa:
        ticket=fresh(psa,actor,tid)
        statuses=psa.get(f'service/boards/{ticket["board"]["id"]}/statuses')
        if body.status_id is None and body.member_id is None:raise HTTPException(422,'recommendation_required')
        if body.status_id is not None and body.status_id not in [s['id'] for s in statuses]:raise HTTPException(422,'invalid_board_status')
        if body.member_id is not None and body.member_id not in psa.config['member_map'].values():raise HTTPException(422,'member_out_of_scope')
    return {'status':'recommendation_only','ticket_id':tid,'proposed':body.model_dump(exclude_none=True),
            'source':f'service/boards/{ticket["board"]["id"]}/statuses','executed':False}


def sync_page(tenant,conn):
    with PSA(tenant) as psa:
        cursor=conn.execute('SELECT * FROM sync_cursors WHERE tenant_id=%s FOR UPDATE',(tenant,)).fetchone()
        batch=psa.get('service/tickets',{'page':cursor['page'],'pageSize':2,'orderBy':'id asc'})
        if not isinstance(batch,list) or len(batch)>2:raise HTTPException(502,'invalid_downstream_schema')
        try:
            ids=[]
            for row in batch:
                if type(row['id']) is not int or row['id']<1:raise ValueError()
                if not all(type(row[k]['id']) is int for k in ('company','board','status')):raise ValueError()
                if not isinstance(row['summary'],str) or not isinstance(row['_info']['lastUpdated'],str):raise ValueError()
                ids.append(row['id'])
            if ids!=sorted(set(ids)):raise ValueError()
        except (KeyError,TypeError,ValueError):raise HTTPException(502,'invalid_downstream_schema')
        for row in batch:
            source_hash=digest(row)
            old=conn.execute('SELECT source_hash FROM ticket_source_cache WHERE tenant_id=%s AND external_id=%s',(tenant,row['id'])).fetchone()
            if not old or old['source_hash']!=source_hash:
                conn.execute('INSERT INTO ticket_change_events(id,tenant_id,external_id,generation,source_hash) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                    (uuid4(),tenant,row['id'],cursor['generation'],source_hash))
            conn.execute('''INSERT INTO ticket_source_cache VALUES (%s,%s,%s,%s,now(),%s)
                ON CONFLICT(tenant_id,external_id) DO UPDATE SET payload=excluded.payload,source_hash=excluded.source_hash,
                fetched_at=now(),generation=excluded.generation''',(tenant,row['id'],Jsonb(row),source_hash,cursor['generation']))
        completed=len(batch)<2
        if completed:
            conn.execute('UPDATE sync_cursors SET page=1,generation=generation+1,last_completed_at=now() WHERE tenant_id=%s',(tenant,))
        else:
            conn.execute('UPDATE sync_cursors SET page=page+1 WHERE tenant_id=%s',(tenant,))
        return {'processed':len(batch),'completed':completed,'next_page':1 if completed else cursor['page']+1,
            'generation':cursor['generation'],'strategy':'full_scan_refresh','deletion_policy':'retain_stale_until_confirmed'}


@router.post('/sync')
def sync(actor:Actor,request:Request):
    allow(actor,('administrator',))
    with connection() as conn:
        result=sync_page(actor['tenant_id'],conn)
        audit(conn,actor,'sync_page',request)
        return result


@router.get('/sync/status')
def sync_status(actor:Actor):
    allow(actor,('administrator',))
    with connection() as conn:
        row=conn.execute('SELECT * FROM sync_cursors WHERE tenant_id=%s',(actor['tenant_id'],)).fetchone()
    return {**row,'stale':row['last_completed_at'] is None or datetime.now(timezone.utc)-row['last_completed_at']>timedelta(minutes=5)}


@router.get('/tickets/{tid}/cached')
def cached(tid:str,actor:Actor):
    allow(actor,('operator','approver'))
    local=scoped(actor,tid)
    with connection() as conn:
        row=conn.execute('''SELECT c.*,s.generation AS current_generation FROM ticket_source_cache c
          JOIN sync_cursors s USING(tenant_id) WHERE c.tenant_id=%s AND c.external_id=%s''',
          (actor['tenant_id'],external_id(tid))).fetchone()
    if not row:raise HTTPException(404,'cache_not_populated')
    with PSA(actor['tenant_id']) as psa:
        remote=row['payload']
        if psa.config['company_map'].get(str(remote['company']['id']))!=local['company_id'] or psa.config['board_map'].get(str(remote['board']['id']))!=local['board_id']:
            raise HTTPException(404,'cache_not_in_scope')
    stale=datetime.now(timezone.utc)-row['fetched_at']>timedelta(minutes=5) or row['generation']<row['current_generation']-1
    return {'ticket':remote,'source_hash':row['source_hash'],'fetched_at':row['fetched_at'],
            'stale':stale,'authoritative_for_write':False}
