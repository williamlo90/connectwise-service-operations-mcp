"""Bounded local reliability qualification; only cw-ops-qualify is disrupted."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
PROJECT='cw-ops-qualify'
COMMAND=['docker','compose','--env-file','.env.example','-p',PROJECT,'-f','compose.test.yaml']
OUT=ROOT/'local'/'qualification'


def shell(args, *, data=None, check=True):
    r=subprocess.run(args,cwd=ROOT,input=data,capture_output=True)
    if check and r.returncode:
        raise RuntimeError('Command failed: '+str(args[:7])+'\n'+r.stderr.decode('utf-8',errors='replace')[-2000:])
    return r


def compose(*args,**kwargs): return shell(COMMAND+list(args),**kwargs)


def task(mode, database=None):
    args=['run','--rm','--no-deps']
    if database: args+=['-e','DB_NAME='+database]
    result=compose(*args,'tests','python','-m','evaluation.reliability',mode)
    return json.loads(result.stdout.decode().strip().splitlines()[-1])


def ready():
    compose('exec','-T','api','python','-c',
            'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=10)')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report={'status':'failed','started_at':datetime.now(timezone.utc).isoformat(),
            'scope':'local synthetic isolated qualification','source_revision':shell(['git','rev-parse','HEAD']).stdout.decode().strip()}
    stop=threading.Event(); samples=[]
    def sampler():
        while not stop.is_set():
            ids=compose('ps','-q',check=False).stdout.decode().split()
            if ids:
                rows=shell(['docker','stats','--no-stream','--format','{{json .}}',*ids],check=False)
                samples.append({'at':datetime.now(timezone.utc).isoformat(),
                                'containers':[json.loads(x) for x in rows.stdout.decode().splitlines()]})
            stop.wait(10)
    thread=None
    try:
        compose('down','--remove-orphans')
        compose('build','api','tests','simulator','migrate','seed')
        compose('up','-d','--wait','api'); ready()
        thread=threading.Thread(target=sampler); thread.start()
        report['backlog']=task('backlog'); print('Backlog and received/resolved alerts passed',flush=True)
        log_before=compose('logs','--no-color','api').stdout.splitlines()
        report['load']=task('load'); print('Normal, peak and short soak passed',flush=True)
        load_logs=compose('logs','--no-color','api').stdout.splitlines()[len(log_before):]
        downstream=[]
        for line in load_logs:
            if b'{"event": "psa_request"' in line:
                downstream.append(json.loads(line[line.index(b'{'):]))
        assert downstream and all(e['status']==200 or e['status']==201 for e in downstream)
        report['downstream_load_samples']=downstream
        # Quiescent snapshot: no worker/monitor service in this test stack.
        before=task('digest')
        dump=compose('exec','-T','db','pg_dump','-U','cw_test','-d','cw_ops_test','-Fc').stdout
        (OUT/'backup.dump').write_bytes(dump)
        compose('exec','-T','db','createdb','-U','cw_test','cw_ops_restore_test')
        started=time.monotonic()
        compose('exec','-T','db','pg_restore','-U','cw_test','-d','cw_ops_restore_test','--exit-on-error',data=dump)
        restored=task('digest','cw_ops_restore_test')
        assert before==restored, 'Restored rows/sequence state differ'
        report['backup_restore']={'status':'passed','archive_sha256':hashlib.sha256(dump).hexdigest(),
                                  'archive_bytes':len(dump),'restore_and_verify_seconds':time.monotonic()-started,
                                  'restored':restored,'scope':'consistent logical dump into separate disposable database; no loss of snapshot rows'}
        print('Backup restored and every public table/sequence matched',flush=True)
        # Monitor runs in API container with dedicated /tmp inbox to survive each poll.
        def monitor(): compose('exec','-T','api','python','-m','app.monitor','--once','--directory','/tmp/qualification-inbox')
        monitor()
        compose('pause','db')
        try:
            monitor()
            probe=compose('exec','-T','api','python','-c',
                'import httpx; r=httpx.get("http://127.0.0.1:8000/health/ready",timeout=10); assert r.status_code==503',check=False)
            assert probe.returncode==0, 'Readiness did not fail closed on DB outage'
        finally: compose('unpause','db')
        ready(); monitor()
        events=json.loads(compose('exec','-T','api','python','-c',
            'import json; print(json.dumps([json.loads(x) for x in open("/tmp/qualification-inbox/alerts.jsonl")]))').stdout)
        states={e['state'] for e in events if e['code']=='database_unavailable'}
        assert states=={'firing','resolved'}
        report['database_outage']={'status':'passed','readiness_during_outage':503,'recovered_readiness':200,'received_alerts':events}
        print('Database outage, local alert delivery and recovery passed',flush=True)
        # Bound exhaustion to a disposable 64 MiB container, swap disallowed.
        image=compose('images','-q','api').stdout.decode().strip()
        name=PROJECT+'-oom'
        try:
            shell(['docker','run','--name',name,'--memory','64m','--memory-swap','64m','--cpus','0.25','--network','none',
                   '--read-only','--security-opt','no-new-privileges:true',image,'python','-c',
                   'chunks=[]\nwhile True: chunks.append(bytearray(8*1024*1024))'],check=False)
            state=json.loads(shell(['docker','inspect','--format','{{json .State}}',name]).stdout)
            assert state['OOMKilled'] and state['ExitCode']==137
            ready()
            report['resource_exhaustion']={'status':'passed','oom_killed':True,'exit_code':137,'api_survived':True,
                                           'scope':'isolated backend-image process, not actual model inference','limit_mib':64}
        finally: shell(['docker','rm','-f',name],check=False)
        # A real pinned model runtime under a deliberately insufficient cap.
        model_name=PROJECT+'-model-pressure'
        try:
            shell(['docker','run','-d','--name',model_name,'--memory','256m','--memory-swap','256m','--cpus','1',
                   '--network',PROJECT+'_default','--network-alias','ollama',
                   '--mount','type=volume,source=cw-ops-local_ollama_models,target=/root/.ollama,readonly',
                   '-e','OLLAMA_NUM_PARALLEL=1','-e','OLLAMA_MAX_LOADED_MODELS=1',
                   'ollama/ollama:0.12.3@sha256:c622a7adec67cf5bd7fe1802b7e26aa583a955a54e91d132889301f50c3e0bd0'])
            for _ in range(20):
                probe=shell(['docker','exec',model_name,'ollama','list'],check=False)
                if probe.returncode==0: break
                time.sleep(1)
            assert probe.returncode==0 and b'qwen3:0.6b' in probe.stdout
            result=task('model-exhaustion')
            state=json.loads(shell(['docker','inspect','--format','{{json .State}}',model_name]).stdout)
            memory=shell(['docker','exec',model_name,'cat','/sys/fs/cgroup/memory.events'],check=False).stdout.decode()
            result.update({'limit_mib':256,'container_oom_killed':state['OOMKilled'],'memory_events':memory})
            (OUT/'ollama-pressure.log').write_bytes(shell(['docker','logs',model_name],check=False).stderr)
            report['local_model_pressure']=result
            ready()
        finally: shell(['docker','rm','-f',model_name],check=False)
        # Rebuild exact previous release from tracked Git archive, no .env.
        archive=shell(['git','archive','phase-6']).stdout
        shell(['docker','build','-t','cw-ops-phase6-rollback','-f','backend/Dockerfile','-'],data=archive)
        override=OUT/'rollback.yaml'
        override.write_text('services:\n  api:\n    image: cw-ops-phase6-rollback\n',encoding='utf-8')
        old=COMMAND+['-f',str(override)]
        try:
            shell(old+['up','-d','--no-deps','--no-build','--wait','api']); ready()
            result=compose('run','--rm','--no-deps','tests','python','-m','unittest',
                'tests.test_phase2.WorkflowTests.test_note_exact_approved_payload_and_replay',
                'tests.test_phase2.WorkflowTests.test_permission_and_approval_boundaries','-v')
            (OUT/'rollback-tests.log').write_bytes(result.stdout+result.stderr)
        finally: compose('up','-d','--no-deps','--no-build','--wait','api')
        ready()
        report['rollback']={'status':'passed','previous_ref':'phase-6','schema':'004_automation.sql unchanged',
                            'verified_write_and_permission_tests':2,'candidate_restored':True}
        report['resources']=samples
        report['status']='passed'
    finally:
        stop.set()
        if thread: thread.join(timeout=30)
        compose('unpause','db',check=False)
        logs=compose('logs','--no-color','api','simulator',check=False).stdout
        (OUT/'service.log').write_bytes(logs)
        compose('down','--remove-orphans',check=False)
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        report['source_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
             for directory in ('backend','evaluation','scripts','tests') for p in sorted((ROOT/directory).rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts}
        (ROOT/'docs/evidence/phase-7-qualification.json').write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8')
    print('Phase 7 qualification '+report['status'],flush=True)


if __name__=='__main__': main()
