"""Rebuild a disposable test stack, run HTTP and client acceptance, then clean up."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from check_workflow_cli import check_cli

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ['docker', 'compose', '--env-file', '.env.example', '-p', 'cw-ops-test', '-f', 'compose.test.yaml']


def run(*args, check=True, capture=False):
    return subprocess.run(COMMAND + list(args), cwd=ROOT, check=check,
                          capture_output=capture, text=True, encoding='utf-8')


def main():
    status = 'failed'
    result = {}
    logs = ''
    try:
        # Only this named test project is reset. Its PostgreSQL data lives in tmpfs.
        run('down', '--remove-orphans')
        run('build')
        run('up', '-d', '--wait', 'api')
        acceptance = run('run', '--rm', '--no-deps', 'tests', capture=True, check=False)
        output = acceptance.stdout + acceptance.stderr
        print(output)
        acceptance.check_returncode()
        summary = re.search(r'Ran (\d+) tests in ([\d.]+)s', output)
        if not summary:
            raise RuntimeError('Missing test summary')
        run('run', '--rm', '--no-deps', 'client')
        run('run', '--rm', '--no-deps', 'client', '--consumer-smoke')
        check_cli(COMMAND)
        logs = run('logs', '--no-color', 'api', capture=True).stdout
        for secret in ('synthetic-test-user-password-only', 'synthetic-test-database-password-only', 'synthetic-test-simulator-secret-only', 'Bearer ', 'access_token'):
            if secret in logs:
                raise RuntimeError('Sensitive content found in API log')
        events = []
        for line in logs.splitlines():
            if '{"event": "http_request"' in line:
                events.append(json.loads(line[line.index('{'):]))
        if not events or not any(e['status'] == 404 for e in events):
            raise RuntimeError('Missing structured denied-access evidence')
        result = {'tests_total': int(summary[1]), 'suite_seconds': float(summary[2]),
                  'http_tests': len(re.findall(r'^test_\w+ \(test_(?:phase2|smoke)\.', output, re.MULTILINE)),
                  'asgi_assistant_tests': len(re.findall(r'^test_\w+ \(test_assistant\.', output, re.MULTILINE)),
                  'provider_contract_tests': len(re.findall(r'^test_\w+ \(test_ai_providers\.', output, re.MULTILINE)),
                  'skill_package_tests': len(re.findall(r'^test_\w+ \(test_skill_contracts\.', output, re.MULTILINE)),
                  'test_cases': re.findall(r'^(test_\w+) .*? \.\.\. ok$', output, re.MULTILINE),
                  'structured_http_events': len(events), 'log_secret_check': 'passed',
                  'typescript_client': 'passed', 'workflow_cli': 'passed', 'consumer_contract_1_0_0': 'passed (HTTP bridge)', 'http_acceptance': 'passed'}
        status = 'passed'
    finally:
        run('down', '--remove-orphans', check=False)
        evidence = ROOT / 'docs' / 'evidence' / 'phase-3-run.json'
        files = {}
        for directory in ('backend', 'client', 'tests', 'scripts', 'contracts', 'skills'):
            for path in sorted((ROOT / directory).rglob('*')):
                if path.is_file() and not any(part in ('node_modules', 'dist', '__pycache__') for part in path.parts) and path.name != 'resolved.json':
                    files[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        for name in ('compose.yaml','compose.test.yaml','compose.ai.yaml'):
            files[name] = hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        evidence.write_text(json.dumps({'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'status': status, 'environment': 'local Docker Linux / isolated PostgreSQL tmpfs',
            'dataset': 'synthetic phase-2 seed: 2 tenants, 7 actors, 4 local tickets, 6 remote tickets',
            'connectwise': 'not tested', 'source_sha256': files, **result}, indent=2)+'\n', encoding='utf-8')
    return 0 if status == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
