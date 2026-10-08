"""Exercise the actual compiled CLI across separate synthetic operator/approver sessions."""
from pathlib import Path
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def check_cli(command, mcp=False):
    def call(args,stdin=None):
        if mcp: args = args + ['--mcp']
        r=subprocess.run(command+['run','--rm','--no-deps','-T']+args,cwd=ROOT,input=stdin,
                         text=True,capture_output=True,encoding='utf-8')
        if r.returncode:
            raise RuntimeError('Synthetic workflow CLI failed: '+r.stderr)
        return r.stdout

    def payload(output):
        return json.loads(output[output.index('{\n'):])

    p=payload(call(['client','--workflow','note','A-100'],'Phase 2 local CLI verification note.\n'))
    approve=['-e','DEMO_USERNAME=approver-a','client','--workflow','approve',p['id']]
    declined=call(approve,'DECLINE\n')
    if 'No approval submitted.' not in declined:raise RuntimeError('Decline not honored')
    approved=call(approve,'APPROVE\n')
    if '"status": "approved"' not in approved:raise RuntimeError('Approval failed')
    op=payload(call(['client','--workflow','execute',p['id']]))
    if op['status']!='verified':raise RuntimeError('Write was not verified')
    verified=payload(call(['client','--workflow','verify',op['id']]))
    if verified['external_id']!=op['external_id']:raise RuntimeError('Receipt changed')
    # Multiple piped answers must survive between async readline operations.
    time=payload(call(['client','--workflow','time','A-100'],
        'Synthetic CLI work log\n30\nTimer recorded 30 minutes\n2026-10-08T09:00:00+07:00\n'))
    if time['payload']['actualHours']!=0.5:raise RuntimeError('CLI duration mismatch')
    print(('MCP' if mcp else 'HTTP') + ' workflow CLI prepare/decline/approve/execute/verify and time input PASS')
    return verified
