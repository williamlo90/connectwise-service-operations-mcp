"""Small development sanity set, not a held-out quality benchmark or load test."""
import json
import time
import urllib.request
from datetime import datetime,timezone
from uuid import uuid4
from ai_canary import ROOT,config

cfg=config();base='http://127.0.0.1:'+cfg.get('API_PORT','8030')


def call(path,body,token=None):
    req=urllib.request.Request(base+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json',
        **({'Authorization':'Bearer '+token} if token else {})})
    with urllib.request.urlopen(req,timeout=115) as response:
        raw=response.read();return json.loads(raw) if raw else None


def main():
    cases=[('a_summary','op-a','A-100','summarize_service_ticket',{},'VPN'),
        ('b_summary','op-b','B-100','summarize_service_ticket',{},'Printer'),
        ('a_note','op-a','A-100','prepare_internal_note',{'technician_notes':'Technician checked DNS; customer retest pending.'},'VPN'),
        ('b_time','op-b','B-100','prepare_time_entry',{'technician_notes':'Technician checked printer queue.',
            'duration_minutes':35,'duration_evidence':'Work timer: 35 minutes','time_start':'2026-10-08T10:00:00+07:00'},'Printer'),
        ('worker_summary','worker-a','A-100','summarize_service_ticket',{},'VPN')]
    results=[]
    for name,user,tid,skill,extra,expected in cases:
        token=call('/auth/login',{'username':user,'password':cfg['DEMO_PASSWORD']})['access_token']
        started=time.monotonic()
        try:
            path='/skills/'+skill+'/runs' if user=='worker-a' else '/assistant/runs'
            run=call(path,{'request_id':str(uuid4()),'skill':skill,'ticket_id':tid,'provider':'ollama','local_only':True,**extra},token)
            passed=run['status']=='completed' and expected in run['result']['summary']
            if skill=='prepare_time_entry':passed=passed and run['result']['proposal_input']['duration_minutes']==35
            results.append({'case':name,'passed':passed,'status':run['status'],'error_code':run['error_code'],'model':run['model'],
                'latency_ms':run['latency_ms'],'usage':run['usage'],'cost_usd':run['cost_usd'],'run_id':run['id'],
                'wall_ms':round((time.monotonic()-started)*1000)})
        finally:call('/auth/logout',{},token)
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'dataset':'five synthetic development sanity cases; no held-out claim',
        'runtime':'Ollama 0.12.3 / CPU only / 2 CPU cap / 1536 MiB cap','quantization':'see local-model-runtime.json',
        'context_tokens':4096,'concurrency':1,'pass_count':sum(r['passed'] for r in results),'case_count':len(results),
        'cases':results,'cost_note':'Cost unknown; no hosted comparison without configured keys and a measured run.'}
    path=ROOT/'docs/evidence/phase-3-local-evaluation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['pass_count'],'total':len(results),'evidence':str(path.relative_to(ROOT))}))
    return 0 if all(r['passed'] for r in results) else 1


if __name__=='__main__':raise SystemExit(main())
