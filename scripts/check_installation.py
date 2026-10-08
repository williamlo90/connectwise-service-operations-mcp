"""Follow the quick start from a Git snapshot with new credentials/volumes."""
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    project='cw-ops-install-'+uuid4().hex[:8]
    directory=(ROOT/'local'/project).resolve();directory.mkdir(parents=True)
    archive=subprocess.check_output(['git','archive','--format=zip',revision],cwd=ROOT)
    with zipfile.ZipFile(io.BytesIO(archive)) as files:
        for entry in files.infolist():
            if not (directory/entry.filename).resolve().is_relative_to(directory):raise RuntimeError('Unsafe archive path')
        files.extractall(directory)
    assert not (directory/'.env').exists()
    env=os.environ.copy();env['API_PORT']='0'
    # Explicit names isolate both data and port from the user's running demo.
    command=['docker','compose','-p',project,'-f','compose.yaml','-f','compose.ops.yaml','--profile','tools','--profile','automation']
    steps=[]
    def run(args,record=True):
        result=subprocess.run(args,cwd=directory,env=env,capture_output=True,text=True,encoding='utf-8')
        if result.returncode:raise RuntimeError('Installation command failed: '+result.stderr[-1500:])
        if record:steps.append({'command':' '.join(['python' if x==sys.executable else x for x in args]),'status':'passed'})
        return result.stdout
    report={'status':'failed','timestamp_utc':datetime.now(timezone.utc).isoformat(),'source_revision':revision,
            'environment':'fresh Git archive, generated secrets, new named volumes and loopback dynamic port; existing Docker download/build cache',
            'project':project,'hosted_requests':0,'steps':steps}
    try:
        run([sys.executable,'scripts/setup_local.py'])
        run(command+['build'])
        run(command+['up','-d','--wait','api'])
        run(command+['run','--rm','--no-deps','seed'])
        result=run(command+['run','--rm','--no-deps','client','--smoke']);assert 'PASS' in result
        context=run(command+['run','--rm','--no-deps','client','--mcp','--workflow','context','A-100']);assert 'VPN connection fails' in context
        run(command+['run','--rm','--no-deps','seed'])
        counts=run(command+['exec','-T','db','psql','-U','cw_ops','-d','cw_ops','-At','-c','SELECT count(*) FROM actors'],record=False)
        assert counts.strip()=='7'
        run(command+['up','-d','--wait','worker','monitor'])
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            p=directory/'local/monitor/metrics.json'
            if p.exists():
                metrics=json.loads(p.read_text(encoding='utf-8'))
                if metrics.get('worker_healthy') and metrics.get('stale_sync_count')==0:break
            time.sleep(1)
        else:raise RuntimeError('Worker/monitor did not become current')
        run(command+['stop'])
        run(command+['up','-d','--wait','api','worker','monitor'])
        result=run(command+['run','--rm','--no-deps','client','--smoke']);assert 'PASS' in result
        report.update(status='passed',seed_idempotent=True,restart_preserved_data=True,worker_and_monitor_current=True)
    finally:
        cleanup=subprocess.run(command+['down','--volumes','--remove-orphans'],cwd=directory,env=env,capture_output=True)
        report['isolated_cleanup_succeeded']=cleanup.returncode==0
        (ROOT/'docs/evidence/phase-8-installation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    assert report['isolated_cleanup_succeeded']
    print(json.dumps({'status':report['status'],'source_revision':revision,'steps':len(steps)}))


if __name__=='__main__':main()
