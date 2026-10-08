"""Public-reference PSA subset. No native idempotency or compare-and-swap support."""
import os
import secrets
import time
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from psycopg.types.json import Jsonb
from .db import connection
from .config import settings

app=FastAPI(title='Synthetic PSA HTTP simulator',version='0.2.0',docs_url=None,redoc_url=None)
basic=HTTPBasic()
BASE='/v4_6_release/apis/3.0'


def tenant(request: Request, auth: Annotated[HTTPBasicCredentials,Depends(basic)]):
    secret=os.environ.get('SIMULATOR_SECRET','')
    if len(secret)<24 or not secrets.compare_digest(auth.password,secret) or request.headers.get('clientId')!='synthetic-client':
        raise HTTPException(401,'invalid_credentials')
    users={'demo-a+synthetic-public':'a','demo-b+synthetic-public':'b'}
    if auth.username not in users: raise HTTPException(401,'invalid_credentials')
    return users[auth.username]


Tenant=Annotated[str,Depends(tenant)]


def fault(t,route):
    with connection() as conn:
        row=conn.execute('SELECT * FROM simulator_faults WHERE tenant_id=%s AND route=%s FOR UPDATE',(t,route)).fetchone()
        if not row or row['remaining']<=0:return None
        conn.execute('UPDATE simulator_faults SET remaining=remaining-1 WHERE tenant_id=%s AND route=%s',(t,route))
    if row['mode']=='rate_limit': raise HTTPException(429,'rate_limit',headers={'Retry-After':'0'})
    if row['mode']=='unauthorized': raise HTTPException(401,'expired_credentials')
    if row['mode']=='unavailable': raise HTTPException(503,'unavailable')
    return row['mode']


def get(t,kind,rid):
    with connection() as conn:
        row=conn.execute('SELECT payload FROM simulator_records WHERE tenant_id=%s AND kind=%s AND id=%s',(t,kind,rid)).fetchone()
    if not row:raise HTTPException(404,'record_not_found')
    return row['payload']


def listing(t,kind,page,page_size,ticket=None):
    with connection() as conn:
        rows=conn.execute('''SELECT payload FROM simulator_records WHERE tenant_id=%s AND kind=%s
         AND (%s::integer IS NULL OR COALESCE(payload->>'ticketId',payload->>'chargeToId')=%s)
         ORDER BY id LIMIT %s OFFSET %s''',(t,kind,ticket,str(ticket),page_size,(page-1)*page_size)).fetchall()
    return [r['payload'] for r in rows]


@app.get('/health/ready')
def health():
    with connection() as conn:conn.execute('SELECT 1 FROM simulator_records LIMIT 1')
    return {'status':'ready','mode':'simulator'}


@app.get(BASE+'/service/tickets')
def tickets(t:Tenant,page:int=Query(1,ge=1),pageSize:int=Query(100,ge=1,le=100),orderBy:str='id asc'):
    fault(t,'tickets')
    if orderBy!='id asc':raise HTTPException(400,'unsupported_order')
    return listing(t,'ticket',page,pageSize)


@app.get(BASE+'/service/tickets/{rid}')
def ticket(rid:int,t:Tenant):
    fault(t,'ticket')
    return get(t,'ticket',rid)


@app.get(BASE+'/company/companies/{rid}')
def company(rid:int,t:Tenant):return get(t,'company',rid)


@app.get(BASE+'/service/boards/{rid}')
def board(rid:int,t:Tenant):return get(t,'board',rid)


@app.get(BASE+'/service/boards/{rid}/statuses')
def statuses(rid:int,t:Tenant):
    get(t,'board',rid)
    return [{'id':1,'name':'New'},{'id':2 if t=='a' else 3,'name':'In Progress' if t=='a' else 'Scheduled'}]


@app.get(BASE+'/system/members/{rid}')
def member(rid:int,t:Tenant):return get(t,'member',rid)


@app.get(BASE+'/service/tickets/{rid}/notes')
def notes(rid:int,t:Tenant,page:int=Query(1,ge=1),pageSize:int=Query(100,ge=1,le=100)):
    get(t,'ticket',rid);fault(t,'notes')
    return listing(t,'note',page,pageSize,rid)


@app.get(BASE+'/service/tickets/{rid}/notes/{nid}')
def note(rid:int,nid:int,t:Tenant):
    row=get(t,'note',nid)
    if row['ticketId']!=rid:raise HTTPException(404,'record_not_found')
    return row


class Note(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    ticketId:int
    text:str=Field(min_length=1,max_length=5000)
    internalAnalysisFlag:bool
    detailDescriptionFlag:bool
    resolutionFlag:bool
    internalFlag:bool
    externalFlag:bool
    processNotifications:bool


class Ref(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    id:int


class TimeEntry(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    chargeToId:int
    chargeToType:str
    member:Ref
    workType:Ref
    workRole:Ref
    timeStart:str
    timeEnd:str
    actualHours:float=Field(gt=0,le=24)
    billableOption:str
    notes:str=Field(min_length=1,max_length=5000)
    addToDetailDescriptionFlag:bool
    addToInternalAnalysisFlag:bool
    addToResolutionFlag:bool
    emailResourceFlag:bool
    emailContactFlag:bool
    emailCcFlag:bool


def create(t,kind,payload,mode):
    with connection() as conn:
        rid=conn.execute("SELECT nextval('simulator_write_id') AS id").fetchone()['id']
        row={**payload,'id':rid}
        if mode=='mismatch':row['notes' if kind=='time' else 'text']='unexpected downstream content'
        conn.execute('INSERT INTO simulator_records VALUES (%s,%s,%s,%s)',(t,kind,rid,Jsonb(row)))
    if mode=='timeout_after_write':time.sleep(2)
    return JSONResponse(status_code=201,content=row)


@app.post(BASE+'/service/tickets/{rid}/notes')
def create_note(rid:int,body:Note,t:Tenant):
    get(t,'ticket',rid)
    if body.ticketId!=rid:raise HTTPException(400,'ticket_mismatch')
    mode=fault(t,'write')
    return create(t,'note',body.model_dump(),mode)


@app.get(BASE+'/time/entries')
def times(t:Tenant,conditions:str,page:int=Query(1,ge=1),pageSize:int=Query(100,ge=1,le=100)):
    import re
    match=re.fullmatch(r'chargeToId=(\d+) AND chargeToType="ServiceTicket"',conditions)
    if not match:raise HTTPException(400,'unsupported_conditions')
    fault(t,'times')
    return listing(t,'time',page,pageSize,int(match[1]))


@app.get(BASE+'/time/entries/{rid}')
def time_entry(rid:int,t:Tenant):return get(t,'time',rid)


@app.post(BASE+'/time/entries')
def create_time(body:TimeEntry,t:Tenant):
    get(t,'ticket',body.chargeToId);get(t,'member',body.member.id)
    if body.chargeToType!='ServiceTicket' or body.billableOption!='DoNotBill':raise HTTPException(400,'unsupported_time_policy')
    mode=fault(t,'write')
    return create(t,'time',body.model_dump(),mode)
