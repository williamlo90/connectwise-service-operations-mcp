"""Explicit bounded provider evaluation, isolated from persistent local projects."""
import json
import os
from pathlib import Path
import subprocess
import sys
from ai_canary import config, ROOT


def main():
    cfg=config()
    if not cfg.get('OPENAI_API_KEY'):raise RuntimeError('Configure the ignored .env key first')
    output=ROOT/'local/evaluation-output'
    output.mkdir(parents=True,exist_ok=True)
    if (output/'report.json').exists():raise RuntimeError('Evaluation report already exists; preserve it before a deliberate new run')
    prior_reserved=0.0
    for saved in (ROOT/'local').glob('evaluation-*/report.json'):
        if saved.parent==output:continue
        previous=json.loads(saved.read_text(encoding='utf-8'))
        outstanding=previous.get('hosted_reservations',0)
        for row in previous.get('cases',[]):
            if row['provider']=='openai':
                outstanding-=1
                usage=(row.get('run') or {}).get('usage') or {}
                prior_reserved+=(usage['input_tokens']*0.4+usage['output_tokens']*1.6)/1_000_000 if all(isinstance(usage.get(k),int) for k in ('input_tokens','output_tokens')) else 0.02
        outstanding-=sum(r['provider']=='openai' and r.get('passed',False) for r in previous.get('negative_cases',[]))
        prior_reserved+=max(0,outstanding)*0.02
    if prior_reserved+16*0.02>0.50:raise RuntimeError('Cumulative evaluation budget would be exceeded')
    environment={**os.environ,'EVALUATION_PRIOR_RESERVED_USD':str(prior_reserved),'OPENAI_API_KEY':cfg['OPENAI_API_KEY'],'COMPOSE_PARALLEL_LIMIT':'1'}
    command=['docker','compose','--env-file','.env.example','-p','cw-ops-eval','-f','compose.test.yaml','-f','compose.eval.yaml']
    def run(*args,check=True):return subprocess.run(command+list(args),cwd=ROOT,env=environment,check=check)
    metadata={'code_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'dirty_paths':subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines(),
              'host':'Windows / approximately 16 GiB RAM / CPU-only inference, 2 CPUs, 1536 MiB cap',
              'max_hosted_assistant_requests':16,'authorized_budget_usd':0.50,'prior_reserved_usd':prior_reserved}
    (output/'environment.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    try:
        run('down','--remove-orphans')
        run('build','api','tests','migrate','seed','simulator')
        run('up','-d','--wait','api','ollama')
        return run('run','--rm','--no-deps','-T','tests',check=False).returncode
    finally:
        run('down','--remove-orphans',check=False)


if __name__=='__main__':sys.exit(main())
