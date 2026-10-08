"""Disposable qualification commands; never allowed against the local demo DB."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from uuid import uuid4
import httpx
from psycopg import sql
from app.config import settings
from app.db import connection


def guard():
    allowed = {'cw_ops_test', 'cw_ops_restore_test'} if sys.argv[1:2] == ['digest'] else {'cw_ops_test'}
    if settings().app_environment != 'test' or settings().db_name not in allowed:
        raise RuntimeError('Only disposable test database is permitted')


def distribution(values):
    values=sorted(values)
    return {'n':len(values), **{f'p{p}_ms':round(values[max(0,math.ceil(len(values)*p/100)-1)],3)
            if values else None for p in (50,90,95,99)}}


def database_digest():
    result={}
    with connection() as conn:
        tables=conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
        for row in tables:
            name=row['tablename']
            records=conn.execute(sql.SQL('SELECT to_jsonb(t)::text value FROM {} t ORDER BY to_jsonb(t)::text').format(sql.Identifier(name))).fetchall()
            result[name]={'rows':len(records),'sha256':hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest()}
        # Sequence state must survive restore too, or a later write may collide.
        sequences=conn.execute("SELECT sequencename,last_value FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename").fetchall()
    return {'tables':result,'sequences':sequences}


def backlog():
    from app import main
    from app.automation import enqueue_due, process_one, tick
    from app.monitor import poll
    with connection() as conn:
        conn.execute('DELETE FROM automation_jobs')
        conn.execute('UPDATE automation_schedules SET enabled=true,next_due=now()')
    enqueue_due()
    with connection() as conn:
        conn.execute("UPDATE automation_jobs SET created_at=now()-interval '90 seconds'")
    firing=poll('/tmp/qualification-inbox')
    assert any(e['code']=='queue_backlog' and e['state']=='firing' for e in firing)
    elapsed=[]
    while True:
        start=time.monotonic(); result=process_one()
        if result is None: break
        elapsed.append((time.monotonic()-start)*1000)
        assert len(elapsed)<=10
    tick()
    with connection() as conn:
        jobs=conn.execute('SELECT status,pages,extract(epoch FROM finished_at-created_at)*1000 completion_ms FROM automation_jobs').fetchall()
    assert len(jobs)==2 and all(r['status']=='completed' and r['pages']==2 for r in jobs)
    resolved=poll('/tmp/qualification-inbox')
    assert any(e['code']=='queue_backlog' and e['state']=='resolved' for e in resolved)
    return {'status':'passed','jobs':jobs,'page_processing':distribution(elapsed),
            'injected_queue_age_ms':90000,'alerts_received':firing+resolved}


def load():
    protocol=json.loads(Path('evaluation/reliability-protocol.json').read_text())
    clients={u:httpx.Client(base_url='http://api:8000',timeout=15) for u in ('op-a','op-b','approver-a','approver-b')}
    headers={}
    for user,client in clients.items():
        response=client.post('/auth/login',json={'username':user,'password':os.environ['DEMO_PASSWORD']})
        response.raise_for_status(); headers[user]={'Authorization':'Bearer '+response.json()['access_token']}
    operations=[]
    def request(user,method,path,body=None):
        start=time.monotonic()
        response=clients[user].request(method,path,json=body,headers=headers[user])
        response.raise_for_status()
        return response.json(),(time.monotonic()-start)*1000
    def task(index):
        tenant='a' if (index//4)%2==0 else 'b'; user='op-'+tenant
        ticket=tenant.upper()+'-100'; start=time.monotonic(); segments={}
        context,segments['context']=request(user,'GET',f'/workflow/tickets/{ticket}/context')
        assert context['ticket']['id']==100
        expected_company=10 if tenant=='a' else 20
        assert context['ticket']['company']['id']==expected_company
        kind='read'
        if index%4==3:
            kind='note' if (index//8)%2==0 else 'time'
            body={'kind':kind,'ticket_id':ticket,'content':'Synthetic qualification: checked connection; follow-up pending.'}
            if kind=='time': body.update(duration_minutes=17,duration_evidence='Synthetic technician timer: 17 minutes',time_start='2026-10-08T09:00:00Z')
            p,segments['prepare']=request(user,'POST','/workflow/proposals',body)
            _,segments['approve']=request('approver-'+tenant,'POST',f'/workflow/proposals/{p["id"]}/approve',{'payload_hash':p['payload_hash'],'confirmed':True})
            op,segments['execute_and_readback']=request(user,'POST',f'/workflow/proposals/{p["id"]}/execute',{'idempotency_key':str(uuid4())})
            assert op['status']=='verified'
            verified,segments['verify_receipt']=request(user,'POST',f'/workflow/operations/{op["id"]}/verify')
            assert verified['status']=='verified' and verified['id']==op['id']
            with connection() as conn:
                row=conn.execute('SELECT expected,observed FROM operations WHERE id=%s',(op['id'],)).fetchone()
                assert all(row['observed'].get(k)==v for k,v in row['expected'].items())
                observed=row['observed']
                if kind=='note':
                    assert observed['ticketId']==100 and observed['internalFlag'] is True and observed['externalFlag'] is False
                    assert observed['processNotifications'] is False
                    assert observed['text'].startswith(body['content'])
                else:
                    assert observed['chargeToId']==100 and observed['chargeToType']=='ServiceTicket'
                    assert abs(observed['actualHours']-17/60)<0.00001
                    assert observed['member']['id']==(7 if tenant=='a' else 9)
                    assert observed['workType']['id']==(1 if tenant=='a' else 2)
                    assert observed['billableOption']=='DoNotBill' and observed['emailContactFlag'] is False
                    assert observed['notes'].startswith(body['content'])
                field='text' if kind=='note' else 'notes'
                n=conn.execute("SELECT count(*) n FROM simulator_records WHERE tenant_id=%s AND kind=%s AND payload->>%s LIKE %s",(tenant,kind,field,'%[cw-op:'+p['id']+']%')).fetchone()['n']
                assert n==1
            operations.append(op['id'])
        return {'kind':kind,'tenant':tenant,'elapsed_ms':(time.monotonic()-start)*1000,'segments_ms':segments,'correct':True}
    profiles=[]; sequence=0
    try:
        for profile in protocol['profiles']:
            rows=[]; pending=[]; dropped=0; start=time.monotonic()
            count=round(profile['seconds']*profile['arrival_rate_per_second'])
            with ThreadPoolExecutor(protocol['maximum_in_flight']) as pool:
                for i in range(count):
                    due=start+i/profile['arrival_rate_per_second']; time.sleep(max(0,due-time.monotonic()))
                    done=[f for f in pending if f.done()]
                    for f in done: rows.append(f.result()); pending.remove(f)
                    if len(pending)>=protocol['maximum_in_flight']: dropped+=1; continue
                    pending.append(pool.submit(task,sequence)); sequence+=1
                for f in pending: rows.append(f.result())
                time.sleep(max(0,start+profile['seconds']-time.monotonic()))
            seconds=time.monotonic()-start
            per_kind={k:distribution([r['elapsed_ms'] for r in rows if r['kind']==k]) for k in ('read','note','time')}
            segments={k:distribution([r['segments_ms'][k] for r in rows if k in r['segments_ms']]) for k in ('context','prepare','approve','execute_and_readback','verify_receipt')}
            assert dropped==0 and len(rows)==count
            assert per_kind['read']['p95_ms']<=protocol['gates']['read_p95_ms']
            assert all(per_kind[k]['p95_ms'] is None or per_kind[k]['p95_ms']<=protocol['gates']['workflow_p95_ms'] for k in ('note','time'))
            profiles.append({**profile,'offered':count,'completed':len(rows),'dropped':dropped,'errors':0,
                             'achieved_per_second':len(rows)/seconds,'elapsed_seconds':seconds,
                             'per_operation':per_kind,'segments':segments,'samples':rows})
            print('Completed '+profile['name'],file=sys.stderr,flush=True)
    finally:
        for user,client in clients.items(): client.post('/auth/logout',headers=headers[user]); client.close()
    return {'status':'passed','protocol':protocol,'profiles':profiles,'verified_writes':len(operations),
            'inference_ms':None,'human_approval_wait_ms':None,
            'timing_note':'Synchronous HTTP responses include processing. Execute includes downstream dispatch and read-back; not measured as a separate acknowledgement. Approval is synthetic, not human wait.'}


def model_exhaustion():
    with connection() as conn: before=conn.execute('SELECT count(*) n FROM proposals').fetchone()['n']
    with httpx.Client(base_url='http://api:8000',timeout=100) as client:
        response=client.post('/auth/login',json={'username':'op-a','password':os.environ['DEMO_PASSWORD']})
        response.raise_for_status(); headers={'Authorization':'Bearer '+response.json()['access_token']}
        try:
            response=client.post('/assistant/runs',headers=headers,json={'request_id':str(uuid4()),
                'skill':'summarize_service_ticket','ticket_id':'A-100','provider':'ollama','local_only':True})
            response.raise_for_status(); run=response.json()
            assert run['status']=='failed' and run['proposal_id'] is None
            assert run['error_code'] in ('provider_unavailable','provider_timeout')
            with connection() as conn: assert conn.execute('SELECT count(*) n FROM proposals').fetchone()['n']==before
            return {'status':'passed','assistant_status':run['status'],'error_code':run['error_code'],
                    'proposal_created':False,'hosted_fallback':False,'latency_ms':run['latency_ms']}
        finally: client.post('/auth/logout',headers=headers)


def main():
    guard()
    mode=sys.argv[1]
    result={'digest':database_digest,'backlog':backlog,'load':load,'model-exhaustion':model_exhaustion}[mode]()
    print(json.dumps(result,default=str))


if __name__=='__main__': main()
