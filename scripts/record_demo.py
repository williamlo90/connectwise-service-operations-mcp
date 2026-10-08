"""Record real CLI/MCP output in a disposable simulator; no model requests."""
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import subprocess
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
COMMAND=['docker','compose','--env-file','.env.example','-p','cw-ops-demo','-f','compose.test.yaml']


def main():
    started=time.monotonic(); events=[]; cases=[]
    target=ROOT/'docs/demo'; target.mkdir(parents=True,exist_ok=True)
    def emit(value): events.append([round(time.monotonic()-started,3),'o',value.replace('\n','\r\n')])
    def run(args,stdin=None,check=True):
        r=subprocess.run(COMMAND+args,cwd=ROOT,input=stdin,text=True,encoding='utf-8',capture_output=True)
        if check and r.returncode: raise RuntimeError(r.stderr[-1500:])
        return r
    def cli(args,stdin=None,user='op-a',denied=False):
        emit(f'\n$ client ({user}) --mcp --workflow '+ ' '.join(args)+'\n')
        if stdin: emit('Synthetic supplied input: '+stdin.replace('\n',' | ').rstrip(' |')+'\n')
        r=run(['run','--rm','--no-deps','-T','-e','DEMO_USERNAME='+user,'client','--mcp','--workflow',*args],stdin,check=False)
        emit(r.stdout)
        if r.returncode:
            # CLI emits a sanitized application error; omit Docker progress noise.
            error='\n'.join(x for x in r.stderr.splitlines() if 'Error' in x or 'failed' in x or 'forbidden' in x or 'not_found' in x)
            emit(error+'\n')
        assert (r.returncode!=0)==denied, 'Unexpected CLI exit status'
        return r.stdout
    def payload(value): return json.loads(value[value.index('{\n'):])
    def approve(p):
        result=cli(['approve',p['id']],'APPROVE\n','approver-a')
        assert '"status": "approved"' in result
    def sql(statement):
        return run(['exec','-T','db','psql','-U','cw_test','-d','cw_ops_test','-At','-v','ON_ERROR_STOP=1','-c',statement]).stdout
    report={'status':'failed','scope':'single-operator synthetic simulator; scripted separate-user approval',
            'recorded_at':datetime.now(timezone.utc).isoformat(),'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'paid_requests':0,'model_requests':0}
    try:
        run(['down','--remove-orphans']); run(['build']); run(['up','-d','--wait','api'])
        emit('SERVICE OPERATIONS — RECORDED LOCAL DEMO\nActual CLI/MCP outputs, synthetic data. No ConnectWise tenant or model call.\nApprovals below are scripted test identities, not unattended approval for real work.\n')
        context=payload(cli(['context','A-100'])); assert context['ticket']['id']==100
        cli(['context','B-100'],denied=True); cases.append('cross_tenant_denied')
        p=payload(cli(['note','A-100'],'Checked VPN settings; customer retest is pending.\n'))
        cli(['execute',p['id']],denied=True); cases.append('unapproved_write_denied')
        approve(p); note=payload(cli(['execute',p['id']])); assert note['status']=='verified'
        assert payload(cli(['verify',note['id']]))['external_id']==note['external_id']; cases.append('internal_note_verified')
        p=payload(cli(['time','A-100'],'Checked VPN connection\n25\nTechnician timer recorded 25 minutes\n2026-10-08T09:00:00+07:00\n'))
        assert p['payload']['actualHours']==25/60
        approve(p); timed=payload(cli(['execute',p['id']])); assert timed['status']=='verified'; cases.append('explicit_time_verified')
        p=payload(cli(['note','A-100'],'Recovery demo: awaiting customer confirmation.\n')); approve(p)
        emit('\n[Isolated simulator fixture: write commits, response is delayed; first read-back is unavailable.]\n')
        sql("INSERT INTO simulator_faults VALUES ('a','write','timeout_after_write',1),('a','notes','unavailable',3)")
        key=str(uuid4()); unknown=payload(cli(['execute',p['id'],key])); assert unknown['status']=='unknown'
        verified=payload(cli(['verify',unknown['id']])); assert verified['status']=='verified'
        replay=payload(cli(['execute',p['id'],key])); assert replay['id']==unknown['id']
        count=int(sql("SELECT count(*) FROM simulator_records WHERE kind='note' AND payload->>'text' LIKE '%[cw-op:"+p['id']+"]%'"))
        assert count==1; cases.append('unknown_to_verified_without_duplicate')
        emit('\nIndependent simulator check: exactly ONE effect for the recovered operation.\nDEMO PASSED: normal note/time, denied access/approval, unknown outcome recovery.\n')
        rows=json.loads(sql("SELECT json_agg(x) FROM (SELECT id,tenant_id,status,external_id,expected,observed FROM operations ORDER BY created_at) x"))
        assert len(rows)==3 and all(r['status']=='verified' and all(r['observed'].get(k)==v for k,v in r['expected'].items()) for r in rows)
        report.update(status='passed',cases=cases,verified_operations=rows,duplicate_effects=0)
    finally:
        run(['down','--remove-orphans'],check=False)
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        report['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for directory in ('backend','client') for p in sorted((ROOT/directory).rglob('*'))
            if p.is_file() and not any(x in p.parts for x in ('__pycache__','node_modules','dist'))}
        report['source_sha256']['scripts/record_demo.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        (ROOT/'docs/evidence/phase-8-demo.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    header={'version':2,'width':120,'height':36,'timestamp':int(time.time()),'title':'Synthetic service operations: verified writes and recovery'}
    (target/'service-operations.cast').write_text('\n'.join(json.dumps(x) for x in [header,*events])+'\n',encoding='utf-8')
    transcript=''.join(e[2] for e in events)
    (target/'transcript.txt').write_bytes(transcript.encode('utf-8'))
    # Standalone replay: embed inert JSON and use textContent, never HTML from outputs.
    data=json.dumps(events).replace('<','\\u003c')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Recorded service operations demo</title>
<style>body{margin:32px auto;padding:0 20px;max-width:1100px;font:16px system-ui;color:#172b3b;background:#f3f6f8}h1{font-size:27px}button{padding:9px 16px;cursor:pointer}pre{background:#102131;color:#e8f0f6;padding:22px;overflow:auto;height:62vh;font:13px/1.5 monospace;white-space:pre-wrap}input{width:65%;vertical-align:middle}small{display:block;margin:12px 0}</style>
<h1>Service operations · recorded terminal demo</h1><p>Actual CLI and MCP output · synthetic simulator · scripted separate-user approval · no hosted inference</p>
<button id="play">Play</button> <button id="all">Show all</button> <input id="seek" type="range" min="0" value="0" aria-label="Recording position"><small id="clock"></small><pre id="terminal" aria-label="Recorded terminal output"></pre>
<p>Each command's output appears when that command finished. Setup is omitted; elapsed timing is preserved. Replay runs entirely offline.</p>
<script id="data" type="application/json">DATA</script><script>
const events=JSON.parse(document.getElementById('data').textContent), terminal=document.getElementById('terminal'),seek=document.getElementById('seek'),clock=document.getElementById('clock');
const first=events[0][0],end=events.at(-1)[0]-first;seek.max=end;seek.step=.1;let timer=null;
function show(t){terminal.textContent=events.filter(e=>e[0]-first<=t).map(e=>e[2]).join('');terminal.scrollTop=terminal.scrollHeight;seek.value=t;clock.textContent=t.toFixed(1)+' / '+end.toFixed(1)+' seconds';}
document.getElementById('all').onclick=()=>{clearInterval(timer);timer=null;show(end)};seek.oninput=()=>{clearInterval(timer);timer=null;show(Number(seek.value))};
document.getElementById('play').onclick=()=>{if(timer){clearInterval(timer);timer=null;return}if(Number(seek.value)>=end)show(0);timer=setInterval(()=>{let t=Math.min(end,Number(seek.value)+.1);show(t);if(t>=end){clearInterval(timer);timer=null}},100)};show(0);
</script></html>'''.replace('DATA',data)
    (target/'demo.html').write_text(page,encoding='utf-8')
    print(json.dumps({'status':report['status'],'cases':cases,'recording':'docs/demo/demo.html'}))


if __name__=='__main__': main()
