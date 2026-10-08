"""Frozen synthetic evaluation through production HTTP routes; isolated fixtures only."""
import hashlib
import json
import os
from pathlib import Path
import time
from datetime import datetime, timezone
from uuid import uuid4
import httpx
from psycopg.types.json import Jsonb
from app.config import settings
from app.db import connection
from .scoring import score, draft, verify_fields

ROOT=Path(__file__).parent
OUT=Path('/evidence/report.json')


def fixture(case):
    tenant=case['tenant']
    with connection() as conn:
        row=conn.execute("SELECT payload FROM simulator_records WHERE tenant_id=%s AND kind='ticket' AND id=100",(tenant,)).fetchone()['payload']
        row['summary']=case['summary'];row['status']={'id':1,'name':'New'}
        row['_info']['lastUpdated']='2026-10-08T00:00:00Z'
        conn.execute("UPDATE simulator_records SET payload=%s WHERE tenant_id=%s AND kind='ticket' AND id=100",(Jsonb(row),tenant))
        conn.execute("DELETE FROM simulator_records WHERE tenant_id=%s AND (kind='time' OR (kind='note' AND id NOT IN (1,2)))",(tenant,))
        for index,text in enumerate(case['notes'],1):
            note=conn.execute("SELECT payload FROM simulator_records WHERE tenant_id=%s AND kind='note' AND id=%s",(tenant,index)).fetchone()['payload']
            note['text']=text
            conn.execute("UPDATE simulator_records SET payload=%s WHERE tenant_id=%s AND kind='note' AND id=%s",(Jsonb(note),tenant,index))


def main():
    if os.getenv('EVALUATION_RUN')!='true' or settings().app_environment!='test' or settings().db_name!='cw_ops_test':
        raise RuntimeError('Disposable evaluation environment required')
    if OUT.exists():raise RuntimeError('Existing report preserved; do not silently repeat paid evaluation')
    cases=json.loads((ROOT/'cases-v2.json').read_text())['cases']
    protocol=json.loads((ROOT/'protocol-v2.json').read_text())
    freeze=json.loads((ROOT/'freeze-v2.json').read_text())
    for name,expected in freeze['sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise RuntimeError('Frozen input mismatch')
    report={'started_utc':datetime.now(timezone.utc).isoformat(),'dataset_version':'2.0.0','freeze':freeze,
            'environment':'cw-ops-eval / real HTTP / PostgreSQL tmpfs / synthetic simulator',
            'cases':[],'baselines':[],'negative_cases':[],'hosted_reservations':0,'status':'running',
            'human_active_time_ms':None,'human_corrections':None,'timing_claim':'scripted software elapsed; no human ROI',
            'pricing':protocol['pricing'],'budget_usd':0.50,'prior_reserved_usd':float(os.getenv('EVALUATION_PRIOR_RESERVED_USD','0'))}
    def save():OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
    def reserve():
        if report['hosted_reservations']>=16 or report['prior_reserved_usd']+(report['hosted_reservations']+1)*0.02>report['budget_usd']:raise RuntimeError('Budget cap')
        report['hosted_reservations']+=1;save()
    client=httpx.Client(base_url='http://api:8000',timeout=115)
    tokens={}
    def call(path,user,body=None):
        started=time.perf_counter()
        response=client.request('GET' if body is None else 'POST',path,headers={'Authorization':'Bearer '+tokens[user]},json=body)
        elapsed=round((time.perf_counter()-started)*1000,3)
        if not response.is_success:raise RuntimeError(f'HTTP_{response.status_code}')
        return response.json() if response.content else None,elapsed
    def finish(case,proposal,user):
        t=time.perf_counter()
        call(f"/workflow/proposals/{proposal['id']}/approve",'approver-'+case['tenant'],{'payload_hash':proposal['payload_hash'],'confirmed':True})
        receipt,_=call(f"/workflow/proposals/{proposal['id']}/execute",user,{'idempotency_key':str(uuid4())})
        receipt,_=call(f"/workflow/operations/{receipt['id']}/verify",user,{})
        with connection() as conn:
            rows=conn.execute("SELECT tenant_id,payload FROM simulator_records WHERE kind=%s AND payload->>%s LIKE %s",
                (case['kind'],'text' if case['kind']=='note' else 'notes',f"%[cw-op:{proposal['id']}]%" )).fetchall()
        valid=receipt['status']=='verified' and bool(receipt['verified_at']) and len(rows)==1 and rows[0]['tenant_id']==case['tenant'] and verify_fields(case,proposal,rows[0]['payload'],len(rows))
        return {'verified_correct':valid,'side_effects':len(rows),'receipt':receipt,'approval_execute_verify_ms':round((time.perf_counter()-t)*1000,3)}
    save()
    try:
        for user in ('op-a','op-b','approver-a','approver-b','worker-a'):
            response=client.post('/auth/login',json={'username':user,'password':os.environ['DEMO_PASSWORD']});response.raise_for_status();tokens[user]=response.json()['access_token']
        for index,case in enumerate(cases):
            user='op-'+case['tenant'];tid=case['tenant'].upper()+'-100'
            if case['split']=='evaluation' and case['kind']!='summary':
                fixture(case);started=time.perf_counter()
                call(f'/workflow/tickets/{tid}/context',user)
                proposal,_=call('/workflow/proposals',user,draft(case));outcome=finish(case,proposal,user)
                report['baselines'].append({'case':case['id'],'elapsed_ms':round((time.perf_counter()-started)*1000,3),**outcome});save()
            for provider in (['ollama','openai'] if index%2==0 else ['openai','ollama']):
                fixture(case)
                body={'request_id':str(uuid4()),'skill':{'summary':'summarize_service_ticket','note':'prepare_internal_note','time':'prepare_time_entry'}[case['kind']],
                      'ticket_id':tid,'provider':provider,'local_only':provider=='ollama','technician_notes':case['technician_notes']}
                if case['kind']=='time':body.update({k:case[k] for k in ('duration_minutes','duration_evidence','time_start')})
                # A failed generation is an observation, never retried automatically.
                if provider=='openai':reserve()
                row={'case':case['id'],'split':case['split'],'provider':provider,'request_id':body['request_id'],'state':'running'}
                report['cases'].append(row);save();started=time.perf_counter()
                try:
                    run,elapsed=call('/assistant/runs',user,body)
                    assessed=score(case,run)
                    assessed['within_latency_ceiling']=elapsed<=protocol['latency_gate_ms'][provider]
                    assessed['correct']=assessed['correct'] and assessed['within_latency_ceiling']
                    row.update({'state':'observed','assessment':assessed,'run':run,'assistant_http_ms':elapsed,'workflow':None})
                    if assessed['correct'] and case['kind']!='summary':
                        proposal,_=call(f"/assistant/runs/{run['id']}/prepare",user,{})
                        row['workflow']=finish(case,proposal,user)
                    row['elapsed_ms']=round((time.perf_counter()-started)*1000,3)
                    usage=run.get('usage') or {}
                    row['estimated_cost_usd']=round((usage['input_tokens']*0.4+usage['output_tokens']*1.6)/1_000_000,8) if provider=='openai' and all(isinstance(usage.get(k),int) for k in ('input_tokens','output_tokens')) else None
                except Exception as error:
                    row.update({'state':'error','error':str(error) if str(error).startswith('HTTP_') else type(error).__name__,'elapsed_ms':round((time.perf_counter()-started)*1000,3)})
                save();print(json.dumps({'case':case['id'],'provider':provider,'correct':row.get('assessment',{}).get('correct',False),'status':row.get('run',{}).get('status',row['state'])}),flush=True)
        base={'skill':'prepare_time_entry','ticket_id':'A-100','technician_notes':'Checked supplied diagnostic logs.'}
        negatives=[('missing_duration','op-a',base,'documented_duration_required'),
                   ('missing_technician_notes','op-a',{'skill':'prepare_internal_note','ticket_id':'A-100'},'technician_notes_required'),
                   ('cross_tenant','op-a',{'skill':'summarize_service_ticket','ticket_id':'B-100'},404),
                   ('ungranted_worker_skill','worker-a',{'skill':'prepare_internal_note','ticket_id':'A-100','technician_notes':'test'},403)]
        for provider in ('ollama','openai'):
            for name,user,body,expected in negatives:
                if provider=='openai':reserve()
                response=client.post('/assistant/runs',headers={'Authorization':'Bearer '+tokens[user]},json={**body,'request_id':str(uuid4()),'provider':provider,'local_only':provider=='ollama'})
                data=response.json()
                correct=response.status_code==expected if isinstance(expected,int) else response.status_code==200 and data['status']=='failed' and data['error_code']==expected and data['usage'] is None
                report['negative_cases'].append({'case':name,'provider':provider,'passed':correct,'http_status':response.status_code,'error_code':data.get('error_code')});save()
        summary={}
        for provider in ('ollama','openai'):
            selected=[r for r in report['cases'] if r['split']=='evaluation' and r['provider']==provider]
            correct=sum(r.get('assessment',{}).get('correct',False) and (r.get('workflow') is None or r['workflow']['verified_correct']) for r in selected)
            safe=all(r.get('assessment',{}).get('safe',False) and (r.get('workflow') is None or r['workflow']['verified_correct']) for r in selected)
            summary[provider]={'correct':correct,'total':len(selected),'critical_safe':safe,'gate_passed':correct>=7 and safe,
                'estimated_cost_usd':round(sum(r.get('estimated_cost_usd') or 0 for r in report['cases'] if r['provider']==provider),8) if provider=='openai' and all(r.get('estimated_cost_usd') is not None for r in report['cases'] if r['provider']==provider) else None}
        report['summary']=summary
        report['status']='passed' if all(v['gate_passed'] for v in summary.values()) and all(r['passed'] for r in report['negative_cases']) and all(r['verified_correct'] for r in report['baselines']) else 'gate_failed'
    finally:
        report['finished_utc']=datetime.now(timezone.utc).isoformat();save()
        for token in tokens.values():
            try:client.post('/auth/logout',headers={'Authorization':'Bearer '+token})
            except Exception:pass
        client.close()
    print(json.dumps({'status':report['status'],'summary':report.get('summary')}),flush=True)
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
