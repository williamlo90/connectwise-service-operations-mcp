"""Scheduled production sync code against real PostgreSQL and the HTTP simulator."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import os
import subprocess
import sys
import time
import unittest
from uuid import uuid4
import httpx
from psycopg.types.json import Jsonb
from app import main as domain_application
from app.automation import enqueue_due, process_one, tick
from app.config import settings
from app.db import connection


class AutomationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if settings().app_environment!='test' or settings().db_name!='cw_ops_test':
            raise RuntimeError('Isolated test database required')
        cls.client=httpx.Client(base_url='http://api:8000',timeout=15)
        cls.headers={}
        for user in ('admin-a','op-a','worker-a','op-b'):
            response=cls.client.post('/auth/login',json={'username':user,'password':os.environ['DEMO_PASSWORD']})
            response.raise_for_status();cls.headers[user]={'Authorization':'Bearer '+response.json()['access_token']}

    @classmethod
    def tearDownClass(cls):
        for headers in cls.headers.values():cls.client.post('/auth/logout',headers=headers)
        cls.client.close()

    def setUp(self):
        with connection() as conn:
            conn.execute('DELETE FROM automation_jobs')
            conn.execute('DELETE FROM ticket_change_events')
            conn.execute('DELETE FROM ticket_source_cache')
            conn.execute('DELETE FROM simulator_faults')
            conn.execute('UPDATE sync_cursors SET page=1,generation=0,last_completed_at=NULL')
            conn.execute('UPDATE automation_schedules SET enabled=true,next_due=now(),interval_seconds=300')

    def tearDown(self):
        with connection() as conn:conn.execute('DELETE FROM simulator_faults')

    def job(self,tenant='a'):
        with connection() as conn:return conn.execute('SELECT * FROM automation_jobs WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 1',(tenant,)).fetchone()

    def fault(self,mode,remaining=100):
        with connection() as conn:
            conn.execute("INSERT INTO simulator_faults VALUES ('a','tickets',%s,%s) ON CONFLICT(tenant_id,route) DO UPDATE SET mode=excluded.mode,remaining=excluded.remaining",(mode,remaining))

    def due_retry(self):
        with connection() as conn:conn.execute("UPDATE automation_jobs SET next_attempt=now() WHERE tenant_id='a'")

    def drain(self):
        for _ in range(10):
            if process_one() is None:return
        self.fail('Jobs did not drain within page budget')

    def test_schedule_two_tenants_checkpoint_and_no_side_effects(self):
        with connection() as conn:before=conn.execute("SELECT count(*) n FROM simulator_records WHERE kind IN ('note','time')").fetchone()['n']
        tick();self.drain()
        for tenant in ('a','b'):
            self.assertEqual(self.job(tenant)['status'],'completed')
            self.assertEqual(self.job(tenant)['pages'],2)
        with connection() as conn:
            self.assertEqual(conn.execute('SELECT count(*) n FROM ticket_source_cache').fetchone()['n'],6)
            self.assertEqual(conn.execute('SELECT count(*) n FROM ticket_change_events').fetchone()['n'],6)
            self.assertEqual(conn.execute("SELECT count(*) n FROM simulator_records WHERE kind IN ('note','time')").fetchone()['n'],before)
            self.assertEqual(conn.execute("SELECT payload->>'summary' summary FROM ticket_source_cache WHERE tenant_id='b' AND external_id=100").fetchone()['summary'],'Printer unavailable')
        r=self.client.get('/workflow/tickets/B-100/cached',headers=self.headers['op-b']);self.assertEqual(r.status_code,200);self.assertFalse(r.json()['stale'])
        self.assertEqual(self.client.get('/workflow/tickets/B-100/cached',headers=self.headers['op-a']).status_code,404)

    def test_duplicate_trigger_parallel_workers_and_unchanged_scan(self):
        with ThreadPoolExecutor(4) as pool:list(pool.map(lambda _:enqueue_due(),range(4)))
        with connection() as conn:self.assertEqual(conn.execute('SELECT count(*) n FROM automation_jobs').fetchone()['n'],2)
        for _ in range(4):
            with ThreadPoolExecutor(4) as pool:list(pool.map(lambda _:process_one(),range(4)))
        with connection() as conn:
            conn.execute('UPDATE automation_schedules SET next_due=now()')
        enqueue_due();self.drain()
        with connection() as conn:
            self.assertEqual(conn.execute('SELECT count(*) n FROM ticket_change_events').fetchone()['n'],6)
            self.assertEqual(conn.execute("SELECT count(*) n FROM automation_jobs WHERE status='completed'").fetchone()['n'],4)

    def test_external_update_emits_one_new_observation(self):
        enqueue_due();self.drain()
        with connection() as conn:original=conn.execute("SELECT payload FROM simulator_records WHERE tenant_id='a' AND kind='ticket' AND id=100").fetchone()['payload']
        try:
            changed=deepcopy(original);changed['summary']='Updated by external technician';changed['_info']['lastUpdated']='2026-10-08T12:00:00Z'
            with connection() as conn:
                conn.execute("UPDATE simulator_records SET payload=%s WHERE tenant_id='a' AND kind='ticket' AND id=100",(Jsonb(changed),))
                conn.execute('UPDATE automation_schedules SET next_due=now()')
            enqueue_due();self.drain()
            with connection() as conn:self.assertEqual(conn.execute('SELECT count(*) n FROM ticket_change_events').fetchone()['n'],7)
            r=self.client.get('/workflow/tickets/A-100/cached',headers=self.headers['op-a']);self.assertEqual(r.json()['ticket']['summary'],changed['summary'])
        finally:
            with connection() as conn:conn.execute("UPDATE simulator_records SET payload=%s WHERE tenant_id='a' AND kind='ticket' AND id=100",(Jsonb(original),))

    def test_transient_rate_limit_backoff_then_recovery(self):
        enqueue_due();self.fault('rate_limit',3);process_one()
        job=self.job();self.assertEqual(job['status'],'retry');self.assertEqual(job['last_error'],'downstream_rate_limited');self.assertEqual(job['attempts'],1)
        process_one()  # Other tenant may progress; failed tenant waits.
        self.assertEqual(self.job()['total_attempts'],1)
        with connection() as conn:self.assertEqual(conn.execute("SELECT page FROM sync_cursors WHERE tenant_id='a'").fetchone()['page'],1)
        self.due_retry();self.drain();self.assertEqual(self.job()['status'],'completed')

    def test_retry_budget_review_and_admin_recovery(self):
        enqueue_due();self.fault('unavailable')
        for _ in range(3):
            self.due_retry();self.drain()
        job=self.job();self.assertEqual(job['status'],'review');self.assertEqual(job['attempts'],3)
        with connection() as conn:conn.execute('UPDATE automation_schedules SET next_due=now()')
        enqueue_due();self.assertEqual(self.job()['id'],job['id'])
        with connection() as conn:conn.execute('DELETE FROM simulator_faults')
        path=f"/automation/jobs/{job['id']}/retry"
        self.assertEqual(self.client.post(path,headers=self.headers['op-a']).status_code,403)
        self.assertEqual(self.client.post(path,headers=self.headers['admin-a']).status_code,200)
        self.assertEqual(self.client.post(path,headers=self.headers['admin-a']).status_code,409)
        self.drain();self.assertEqual(self.job()['status'],'completed');self.assertGreater(self.job()['total_attempts'],3)

    def test_partial_scan_failure_preserves_committed_page(self):
        enqueue_due();process_one();self.fault('unavailable')
        self.drain()
        with connection() as conn:
            self.assertEqual(conn.execute("SELECT page FROM sync_cursors WHERE tenant_id='a'").fetchone()['page'],2)
            self.assertEqual(conn.execute("SELECT count(*) n FROM ticket_source_cache WHERE tenant_id='a'").fetchone()['n'],2)
            conn.execute('DELETE FROM simulator_faults')
        self.due_retry();self.drain()
        self.assertEqual(self.job()['pages'],2)
        with connection() as conn:self.assertEqual(conn.execute("SELECT count(*) n FROM ticket_change_events WHERE tenant_id='a'").fetchone()['n'],3)

    def test_malformed_source_fails_closed_without_advancing(self):
        with connection() as conn:original=conn.execute("SELECT payload FROM simulator_records WHERE tenant_id='a' AND kind='ticket' AND id=100").fetchone()['payload']
        try:
            invalid=deepcopy(original);invalid['company']=None
            with connection() as conn:conn.execute("UPDATE simulator_records SET payload=%s WHERE tenant_id='a' AND kind='ticket' AND id=100",(Jsonb(invalid),))
            enqueue_due();process_one()
            self.assertEqual(self.job()['status'],'review');self.assertEqual(self.job()['last_error'],'invalid_downstream_schema')
            with connection() as conn:
                self.assertEqual(conn.execute("SELECT page FROM sync_cursors WHERE tenant_id='a'").fetchone()['page'],1)
                self.assertEqual(conn.execute("SELECT count(*) n FROM ticket_source_cache WHERE tenant_id='a'").fetchone()['n'],0)
        finally:
            with connection() as conn:conn.execute("UPDATE simulator_records SET payload=%s WHERE tenant_id='a' AND kind='ticket' AND id=100",(Jsonb(original),))

    def test_credentials_failure_immediate_review(self):
        enqueue_due();self.fault('unauthorized');process_one()
        self.assertEqual(self.job()['status'],'review');self.assertEqual(self.job()['last_error'],'downstream_credentials_rejected');self.assertEqual(self.job()['attempts'],1)
        self.drain();self.assertEqual(self.job()['attempts'],1)

    def test_admin_scope_pause_and_strict_schedule(self):
        for user in ('op-a','worker-a','op-b'):
            self.assertEqual(self.client.get('/automation/jobs',headers=self.headers[user]).status_code,403)
        self.assertEqual(self.client.get('/automation/status').status_code,401)
        headers=self.headers['admin-a']
        self.assertEqual(self.client.post('/automation/schedule',headers=headers,json={'enabled':False,'interval_seconds':300,'tenant_id':'b'}).status_code,422)
        self.assertEqual(self.client.post('/automation/schedule',headers=headers,json={'enabled':False,'interval_seconds':300}).status_code,200)
        enqueue_due();self.assertIsNone(self.job('a'));self.assertIsNotNone(self.job('b'))
        foreign=self.job('b')['id'];self.assertEqual(self.client.post(f'/automation/jobs/{foreign}/retry',headers=headers).status_code,404)
        self.assertEqual(self.client.get('/automation/jobs',headers=headers).json()['items'],[])
        self.assertFalse(self.client.get('/automation/status',headers=headers).json()['schedule']['enabled'])

    def test_worker_process_death_rolls_back_page_and_replays(self):
        enqueue_due()
        child=subprocess.Popen([sys.executable,'-c',"""
from app import main
from app import automation
import time
original=automation.sync_page
def interrupted(*args):
    result=original(*args)
    print('page_uncommitted',flush=True)
    time.sleep(60)
    return result
automation.sync_page=interrupted
automation.process_one()
"""],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(1) as pool:
                waiting=pool.submit(child.stdout.readline)
                try:self.assertEqual(waiting.result(timeout=10).strip(),'page_uncommitted')
                finally:child.kill();child.wait(timeout=5)
        finally:
            if child.poll() is None:child.kill();child.wait(timeout=5)
            child.stdout.close();child.stderr.close()
        with connection() as conn:
            self.assertEqual(conn.execute('SELECT count(*) n FROM ticket_source_cache').fetchone()['n'],0)
            self.assertEqual(conn.execute('SELECT count(*) n FROM ticket_change_events').fetchone()['n'],0)
            self.assertTrue(all(r['page']==1 for r in conn.execute('SELECT page FROM sync_cursors').fetchall()))
        # PostgreSQL may still be releasing the killed client's row lock when
        # process.wait() returns. A surviving worker polls again after SKIP LOCKED.
        deadline=time.monotonic()+5
        while time.monotonic()<deadline and self.job()['status']!='completed':
            self.drain()
            if self.job()['status']!='completed':time.sleep(.05)
        self.assertEqual(self.job()['status'],'completed')

    def test_real_worker_entrypoint_heartbeat_and_health(self):
        result=subprocess.run([sys.executable,'-m','app.worker','--once'],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('automation_tick',result.stdout)
        health=subprocess.run([sys.executable,'-m','app.worker','--health'],capture_output=True,timeout=10)
        self.assertEqual(health.returncode,0)
