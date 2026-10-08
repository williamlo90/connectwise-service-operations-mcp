"""Bind the local candidate's committed source and evidence without self-hashing."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'docs/evidence/release-manifest.json'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    if args.verify:
        manifest=json.loads(TARGET.read_text(encoding='utf-8'))
        bad=[p for p,h in manifest['files_sha256'].items() if not (ROOT/p).is_file() or digest(ROOT/p)!=h]
        if bad:raise SystemExit('Manifest mismatch: '+', '.join(bad))
        tracked={p.decode() for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0') if p}
        expected=tracked-{'docs/evidence/release-manifest.json','docs/PHASE-8-DELIVERY.md'}
        if expected!=set(manifest['files_sha256']):raise SystemExit('Manifest file coverage changed; regenerate after qualification')
        print('Release manifest verified: '+str(len(manifest['files_sha256']))+' files');return
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    files={}
    for line in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0'):
        if not line:continue
        name=line.decode('utf-8')
        if name=='docs/evidence/release-manifest.json':continue
        # Final delivery report is allowed to point back at this immutable manifest.
        if name=='docs/PHASE-8-DELIVERY.md':continue
        files[name]=digest(ROOT/name)
    installation=json.loads((ROOT/'docs/evidence/phase-8-installation.json').read_text(encoding='utf-8'))
    demo=json.loads((ROOT/'docs/evidence/phase-8-demo.json').read_text(encoding='utf-8'))
    assert installation['status']==demo['status']=='passed'
    runtime=['backend','client','contracts','skills','evaluation','compose.yaml','compose.ops.yaml','compose.ai.yaml','compose.test.yaml']
    changed=subprocess.check_output(['git','diff','--name-only',installation['source_revision'],revision,'--',*runtime],cwd=ROOT,text=True)
    if changed:raise SystemExit('Runtime changed after installation qualification: '+changed)
    regression=json.loads((ROOT/'docs/evidence/phase-7-regression.json').read_text(encoding='utf-8'))
    for name,expected in regression['source_sha256'].items():
        if name.startswith(('backend/','client/','contracts/','skills/','evaluation/')) and digest(ROOT/name)!=expected:
            raise SystemExit('Runtime changed after regression: '+name)
    manifest={'candidate':'local-simulator-rc1','generated_at':datetime.now(timezone.utc).isoformat(),
              'source_revision':revision,'installation_source_revision':installation['source_revision'],
              'status':'local-ready; connected/cloud pending','schema':'004_automation.sql',
              'prompt':'evidence-selector-1.1.0','skills':'1.0.0','schema_ai':'selection-1.0.0',
              'mcp_protocol':'2025-11-25','models':json.loads((ROOT/'contracts/local-model.json').read_text()),
              'hosted_model':'gpt-4.1-mini-2025-04-14','evidence':{
                  'regression':'docs/evidence/phase-7-regression.json','quality':'docs/evidence/phase-6-quality.json',
                  'qualification':'docs/evidence/phase-7-qualification.json','demo':'docs/evidence/phase-8-demo.json',
                  'installation':'docs/evidence/phase-8-installation.json'},
              'untested_integrations':['ConnectWise tenant','Anthropic live','xAI live','Azure runtime'],
              'runtime_unchanged_since_installation':True,'runtime_matches_phase7_regression':True,
              'exclusions':['this manifest (self reference)','final delivery report (links to manifest)','ignored .env/local artifacts'],
              'files_sha256':files}
    TARGET.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Manifest created for '+revision)


if __name__=='__main__':main()
