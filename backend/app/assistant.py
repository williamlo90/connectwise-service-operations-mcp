"""Evidence-selecting AI with server-rendered claims and explicit domain handoff."""
from datetime import datetime,timedelta,timezone
import json
import os
import re
import time
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field,AwareDatetime,ValidationError
from psycopg.types.json import Jsonb
from .db import connection
from .main import Actor,allow,audit
from . import ai_providers as providers
from .workflows import scoped,read_context,digest,Prepare,prepare_proposal,verify_operation

router=APIRouter(tags=['assistant-v1'])
SKILLS=('summarize_service_ticket','prepare_internal_note','prepare_time_entry','verify_ticket_write')
SKILL_VERSION='1.0.0'


class RunInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_id:UUID
    skill:Literal['summarize_service_ticket','prepare_internal_note','prepare_time_entry','verify_ticket_write']
    ticket_id:str=Field(min_length=1,max_length=100)
    provider:Literal['ollama','openai','anthropic','xai']='ollama'
    local_only:bool=True
    technician_notes:str=Field(default='',max_length=2000)
    duration_minutes:int|None=Field(default=None,strict=True,ge=1,le=1440)
    duration_evidence:str|None=Field(default=None,max_length=1000)
    time_start:AwareDatetime|None=None
    operation_id:UUID|None=None


class Selection(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    decision:Literal['ready','abstain']
    selected_sources:list[str]=Field(max_length=8)
    missing_information:list[Literal['resolution_unknown','insufficient_evidence']]=Field(max_length=2)


def authorize(actor,skill):
    if actor['role']=='worker':
        with connection() as conn:
            granted=conn.execute('SELECT 1 FROM skill_grants WHERE tenant_id=%s AND actor_id=%s AND skill=%s',
                (actor['tenant_id'],actor['id'],skill)).fetchone()
        if not granted:raise HTTPException(403,'skill_not_granted')
    else:allow(actor,('operator','approver'))


def evidence_for(ctx,body):
    # Retrieval is scoped structured context, not an unfiltered vector search.
    t=ctx['ticket']
    evidence=[{'id':'ticket.summary','text':t['summary'],'source':f'service/tickets/{t["id"]}'},
        {'id':'ticket.status','text':t['status']['name'],'source':f'service/tickets/{t["id"]}'},
        {'id':'company.name','text':ctx['company']['name'],'source':f'company/companies/{ctx["company"]["id"]}'}]
    for n in ctx['notes'][-8:]:
        evidence.append({'id':f'note.{n["id"]}','text':n['text'],
            'source':f'service/tickets/{t["id"]}/notes/{n["id"]}','visibility':'internal' if n.get('internalFlag') else 'public'})
    if body.technician_notes.strip():evidence.append({'id':'technician.notes','text':body.technician_notes,'source':'authenticated_technician_input'})
    if any(len(e['text'])>4000 for e in evidence):raise providers.ProviderError('context_too_large')
    return evidence


def validate_selection(value,evidence,skill):
    try:choice=Selection.model_validate(value)
    except ValidationError:raise providers.ProviderError('invalid_model_output') from None
    index={e['id']:e for e in evidence}
    if len(set(choice.selected_sources))!=len(choice.selected_sources) or any(s not in index for s in choice.selected_sources):
        raise providers.ProviderError('unsupported_source_reference')
    if choice.decision=='ready':
        required={'ticket.summary','ticket.status'}
        if skill in ('prepare_internal_note','prepare_time_entry'):required.add('technician.notes')
        if not required.issubset(choice.selected_sources):raise providers.ProviderError('insufficient_source_coverage')
    return choice,[index[s] for s in choice.selected_sources]


def view(row):
    keys=('id','skill','status','provider','model','prompt_version','schema_version','skill_version','result',
          'proposal_id','latency_ms','usage','cost_usd','error_code','created_at','finished_at')
    return {k:row[k] for k in keys}


def get_run(conn,actor,rid,lock=False):
    row=conn.execute('SELECT * FROM assistant_runs WHERE tenant_id=%s AND actor_id=%s AND id=%s'+(' FOR UPDATE' if lock else ''),
        (actor['tenant_id'],actor['id'],rid)).fetchone()
    if not row:raise HTTPException(404,'run_not_found')
    authorize(actor,row['skill']);scoped(actor,row['ticket_id'],conn)
    return row


@router.post('/assistant/runs')
def run(body:RunInput,actor:Actor,request:Request):
    return run_skill(body,actor,request)


@router.post('/skills/{skill}/runs')
def skill_run(skill:str,body:RunInput,actor:Actor,request:Request):
    if skill!=body.skill:raise HTTPException(422,'skill_mismatch')
    return run_skill(body,actor,request)


def run_skill(body,actor,request):
    authorize(actor,body.skill);scoped(actor,body.ticket_id)
    data=body.model_dump(mode='json');rh=digest(data)
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(str(body.request_id),))
        existing=conn.execute('SELECT * FROM assistant_runs WHERE id=%s',(body.request_id,)).fetchone()
        if existing:
            if existing['tenant_id']!=actor['tenant_id'] or existing['actor_id']!=actor['id']:raise HTTPException(404,'run_not_found')
            if existing['request_hash']!=rh:raise HTTPException(409,'request_id_conflict')
            return view(existing)
        # Global single inference slot across API workers. No unbounded in-process queues.
        conn.execute("SELECT pg_advisory_xact_lock(31003)")
        conn.execute("UPDATE assistant_runs SET status='failed',inference_active=false,error_code='interrupted_run',finished_at=now() WHERE inference_active AND created_at<now()-interval '3 minutes'")
        if conn.execute("SELECT 1 FROM assistant_runs WHERE inference_active LIMIT 1").fetchone():raise HTTPException(429,'assistant_busy')
        conn.execute('''INSERT INTO assistant_runs(id,tenant_id,actor_id,request_hash,skill,ticket_id,operation_id,
            provider,prompt_version,schema_version,skill_version,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'running')''',
            (body.request_id,actor['tenant_id'],actor['id'],rh,body.skill,body.ticket_id,body.operation_id,
             body.provider,providers.PROMPT_VERSION,providers.SCHEMA_VERSION,SKILL_VERSION))
        audit(conn,actor,'assistant_started',request)
    start=time.monotonic();result=None;error=None;usage=None;model=None;source_hash=None;input_hash=None
    try:
        if body.skill=='verify_ticket_write':
            if body.operation_id is None:raise providers.ProviderError('operation_id_required')
            with connection() as conn:
                op=conn.execute('''SELECT p.ticket_id FROM operations o JOIN proposals p ON p.id=o.proposal_id
                    WHERE o.id=%s AND o.tenant_id=%s''',(body.operation_id,actor['tenant_id'])).fetchone()
                if not op or op['ticket_id']!=body.ticket_id:raise HTTPException(404,'operation_not_found')
            result={'receipt':verify_operation(body.operation_id,actor,request),'proposed_actions':[]};status='completed'
        else:
            if body.operation_id is not None:raise providers.ProviderError('unexpected_operation_id')
            if body.skill!='prepare_time_entry' and any(v is not None for v in (body.duration_minutes,body.duration_evidence,body.time_start)):
                raise providers.ProviderError('unexpected_duration')
            if body.skill in ('prepare_internal_note','prepare_time_entry') and not body.technician_notes.strip():
                raise providers.ProviderError('technician_notes_required')
            if body.skill=='prepare_time_entry':
                if body.duration_minutes is None or not body.duration_evidence or not body.duration_evidence.strip() or body.time_start is None:
                    raise providers.ProviderError('documented_duration_required')
            ctx=read_context(body.ticket_id,actor);evidence=evidence_for(ctx,body)
            source_hash=digest(ctx);input_hash=digest(evidence)
            generation=providers.generate(body.provider,evidence,body.skill,body.local_only)
            usage=generation.usage;model=generation.model
            choice,facts=validate_selection(generation.value,evidence,body.skill)
            status='abstained' if choice.decision=='abstain' else 'completed'
            result={'facts':facts,'missing_information':choice.missing_information,'reason':'source_selection_validated',
                'summary':'\n'.join(f'{e["id"]}: {e["text"]}' for e in facts),
                'proposed_actions':[],'source_hash':source_hash,'claim_policy':'extractive; source text is not independently verified'}
            if status=='completed' and body.skill!='summarize_service_ticket':
                content='Technician report: '+body.technician_notes
                # All prose comes from user/source evidence, never unchecked model text.
                content+='\nTicket context: '+ctx['ticket']['summary']+'; status '+ctx['ticket']['status']['name']
                values={'kind':'time' if body.skill=='prepare_time_entry' else 'note','ticket_id':body.ticket_id,'content':content}
                if body.skill=='prepare_time_entry':values.update(duration_minutes=body.duration_minutes,duration_evidence=body.duration_evidence,time_start=body.time_start)
                prepared=Prepare(**values)
                result['proposal_input']=prepared.model_dump(mode='json')
                result['proposed_actions']=[{'action':'create_internal_proposal','requires_human_approval':True}]
    except providers.ProviderError as exc:
        error=exc.code;status='rejected' if error in ('invalid_model_output','unsupported_source_reference','insufficient_source_coverage','context_too_large') else 'failed'
    except ValidationError:status='rejected';error='invalid_draft'
    except HTTPException as exc:status='failed';error=str(exc.detail)
    except Exception:status='failed';error='assistant_internal_error'
    with connection() as conn:
        row=get_run(conn,actor,body.request_id,True)
        if row['status']=='cancelled':
            conn.execute('UPDATE assistant_runs SET inference_active=false WHERE id=%s',(body.request_id,))
            return view(row)
        row=conn.execute('''UPDATE assistant_runs SET inference_active=false,status=%s,result=%s,error_code=%s,latency_ms=%s,usage=%s,
           model=%s,source_hash=%s,input_hash=%s,finished_at=now() WHERE id=%s RETURNING *''',
           (status,Jsonb(json.loads(json.dumps(result,default=str))),error,round((time.monotonic()-start)*1000),Jsonb(usage),model,
            source_hash,input_hash,body.request_id)).fetchone()
        audit(conn,actor,'assistant_'+status,request)
    return view(row)


@router.get('/assistant/runs/{rid}')
def read_run(rid:UUID,actor:Actor):
    with connection() as conn:return view(get_run(conn,actor,rid))


@router.post('/assistant/runs/{rid}/cancel')
def cancel(rid:UUID,actor:Actor,request:Request):
    with connection() as conn:
        row=get_run(conn,actor,rid,True)
        if row['status']=='running':
            row=conn.execute("UPDATE assistant_runs SET status='cancelled',finished_at=now() WHERE id=%s RETURNING *",(rid,)).fetchone()
            audit(conn,actor,'assistant_cancelled',request)
        return view(row)


@router.post('/assistant/runs/{rid}/prepare')
def materialize(rid:UUID,actor:Actor,request:Request):
    allow(actor,('operator','approver'))
    with connection() as conn:
        row=get_run(conn,actor,rid,True)
        if row['proposal_id']:
            p=conn.execute('SELECT id,payload,payload_hash,expires_at FROM proposals WHERE id=%s',(row['proposal_id'],)).fetchone()
            return p
        if row['status']!='completed' or 'proposal_input' not in (row['result'] or {}):raise HTTPException(409,'no_valid_draft')
        if datetime.now(timezone.utc)-row['created_at']>timedelta(minutes=30):raise HTTPException(409,'draft_expired')
        if digest(read_context(row['ticket_id'],actor))!=row['source_hash']:raise HTTPException(409,'stale_ai_context')
        proposal=prepare_proposal(Prepare(**row['result']['proposal_input']),actor,request,pid=rid,transaction=conn)
        conn.execute('UPDATE assistant_runs SET proposal_id=%s WHERE id=%s',(proposal['id'],rid))
        return proposal
