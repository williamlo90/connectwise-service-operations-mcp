"""Bounded real-provider canary through the local API, using synthetic seed data only."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import urllib.request
import urllib.error
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]


def config():
    values={}
    for line in (ROOT/'.env').read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key,value=line.split('=',1);values[key.strip()]=value.strip()
    return values


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--provider',choices=['ollama','openai','anthropic','xai'],required=True)
    parser.add_argument('--workflow',action='store_true',help='Local-only synthetic note approval/write canary')
    args=parser.parse_args();cfg=config()
    if args.workflow and args.provider!='ollama':raise SystemExit('Workflow canary is local-only; hosted canary sends one summary request.')
    if args.provider!='ollama' and cfg.get('AI_HOSTED_ENABLED','false').lower()!='true':raise SystemExit('Set AI_HOSTED_ENABLED=true only when ready for the small hosted canary.')
    base='http://127.0.0.1:'+cfg.get('API_PORT','8030')
    tokens=[]
    def call(path,body=None,token=None):
        request=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})})
        try:
            with urllib.request.urlopen(request,timeout=115) as response:
                data=response.read();return json.loads(data) if data else None
        except urllib.error.HTTPError as exc:raise RuntimeError(f'HTTP {exc.code} on {path.split("/")[1]}') from None
    def login(user):
        token=call('/auth/login',{'username':user,'password':cfg['DEMO_PASSWORD']})['access_token'];tokens.append(token);return token
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'provider':args.provider,'dataset':'synthetic A-100 seed',
            'hosted_request_limit':1,'connectwise':'simulator only','status':'failed'}
    try:
        op=login('op-a')
        body={'request_id':str(uuid4()),'skill':'prepare_internal_note' if args.workflow else 'summarize_service_ticket',
              'ticket_id':'A-100','provider':args.provider,'local_only':args.provider=='ollama'}
        if args.workflow:body['technician_notes']='Technician checked VPN settings; customer retest is pending.'
        run=call('/assistant/runs',body,op)
        report['run']=run
        if run['status']!='completed':raise RuntimeError('Assistant outcome: '+run['status']+' / '+str(run['error_code']))
        if args.workflow:
            proposal=call('/assistant/runs/'+run['id']+'/prepare',{},op)
            approver=login('approver-a')
            call('/workflow/proposals/'+proposal['id']+'/approve',{'payload_hash':proposal['payload_hash'],'confirmed':True},approver)
            receipt=call('/workflow/proposals/'+proposal['id']+'/execute',{'idempotency_key':str(uuid4())},op)
            report['receipt']=receipt
            if receipt['status']!='verified':raise RuntimeError('Synthetic write not verified')
        report['status']='passed'
    except Exception as exc:
        report['error']=str(exc)
    finally:
        for token in tokens:
            try:call('/auth/logout',{},token)
            except Exception:pass
        path=ROOT/'docs/evidence'/f'phase-3-{args.provider}{"-workflow" if args.workflow else "-canary"}.json'
        path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'provider':args.provider,'status':report['status'],'error':report.get('error'),'evidence':str(path.relative_to(ROOT))}))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
