"""Independent policy expectations exercised across API -> HTTP simulator -> PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import os
import unittest
from uuid import uuid4
import httpx
from psycopg.types.json import Jsonb
from app.db import connection
from app.config import settings


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if settings().app_environment!='test' or settings().db_name!='cw_ops_test':
            raise RuntimeError('Only isolated test database is permitted')
        cls.client=httpx.Client(base_url='http://api:8000',timeout=15)
        cls.headers={}
        for user in ('op-a','approver-a','op-b','approver-b','admin-a','worker-a','auditor-a'):
            r=cls.client.post('/auth/login',json={'username':user,'password':os.environ['DEMO_PASSWORD']})
            r.raise_for_status();cls.headers[user]={'Authorization':'Bearer '+r.json()['access_token']}

    @classmethod
    def tearDownClass(cls):cls.client.close()

    def setUp(self):
        with connection() as conn:
            conn.execute('DELETE FROM simulator_faults')

    def call(self,method,path,user='op-a',body=None,code=200):
        r=self.client.request(method,'/workflow'+path,headers=self.headers[user],json=body)
        self.assertEqual(r.status_code,code,r.text)
        return r.json()

    def prepare(self,user='op-a',kind='note',**extra):
        return self.call('POST','/proposals',user,{'kind':kind,'ticket_id':user[-1].upper()+'-100',
            'content':'Checked connection; awaiting technician follow-up.',**extra},201)

    def approve(self,p,user='approver-a',code=200):
        return self.call('POST',f'/proposals/{p["id"]}/approve',user,
            {'payload_hash':p['payload_hash'],'confirmed':True},code)

    def execute(self,p,key=None,user='op-a',code=200):
        return self.call('POST',f'/proposals/{p["id"]}/execute',user,{'idempotency_key':key or str(uuid4())},code)

    def fault(self,route,mode,remaining=1):
        with connection() as conn:
            conn.execute('INSERT INTO simulator_faults VALUES (%s,%s,%s,%s) ON CONFLICT(tenant_id,route) DO UPDATE SET mode=excluded.mode,remaining=excluded.remaining',('a',route,mode,remaining))

    def remote(self,kind='ticket',rid=100,tenant='a'):
        with connection() as conn:
            return conn.execute('SELECT payload FROM simulator_records WHERE tenant_id=%s AND kind=%s AND id=%s',(tenant,kind,rid)).fetchone()['payload']

    def replace_ticket(self,row):
        with connection() as conn:
            conn.execute("UPDATE simulator_records SET payload=%s WHERE tenant_id='a' AND kind='ticket' AND id=100",(Jsonb(row),))

    def test_context_reference_facts_and_visibility(self):
        r=self.call('GET','/tickets/A-100/context')
        self.assertEqual(r['summary'],'VPN connection fails — New; Acme Demo.')
        self.assertEqual(r['ticket']['company']['id'],10)
        self.assertEqual(r['ticket']['board']['id'],1)
        initial={n['id']:n for n in r['notes'] if n['id']<3}
        self.assertTrue(initial[1]['internalFlag']);self.assertTrue(initial[2]['externalFlag'])
        self.assertTrue(r['missing_information'])
        self.assertEqual({f['field'] for f in r['facts']},{'summary','company','board','status'})

    def test_note_exact_approved_payload_and_replay(self):
        p=self.prepare();payload=p['payload']
        self.assertEqual(set(payload),{'ticketId','text','internalAnalysisFlag','detailDescriptionFlag','resolutionFlag','internalFlag','externalFlag','processNotifications'})
        self.assertEqual(payload['ticketId'],100)
        for k in ('internalAnalysisFlag','internalFlag'):self.assertIs(payload[k],True)
        for k in ('detailDescriptionFlag','resolutionFlag','externalFlag','processNotifications'):self.assertIs(payload[k],False)
        self.assertIn('[cw-op:'+p['id']+']',payload['text'])
        self.approve(p);key=str(uuid4());op=self.execute(p,key)
        self.assertEqual(op['status'],'verified');self.assertIsNotNone(op['verified_at'])
        row=self.remote('note',op['external_id']);self.assertEqual({k:row[k] for k in payload},payload)
        self.assertEqual(self.execute(p,key)['id'],op['id'])
        self.assertEqual(self.execute(p)['id'],op['id'])
        with connection() as conn:
            n=conn.execute("SELECT count(*) n FROM simulator_records WHERE kind='note' AND payload->>'text' LIKE %s",('%[cw-op:'+p['id']+']%',)).fetchone()['n']
        self.assertEqual(n,1)

    def test_time_documented_duration_and_tenant_b_mapping(self):
        p=self.prepare('op-b','time',duration_minutes=45,duration_evidence='Technician timer: 09:00–09:45 WIB',time_start='2026-10-08T09:00:00+07:00')
        payload=p['payload']
        expected={'chargeToId':100,'chargeToType':'ServiceTicket','actualHours':0.75,'member':{'id':9},
            'workType':{'id':2},'workRole':{'id':2},'timeStart':'2026-10-08T02:00:00+00:00',
            'timeEnd':'2026-10-08T02:45:00+00:00','billableOption':'DoNotBill',
            'addToInternalAnalysisFlag':True,'addToDetailDescriptionFlag':False,'addToResolutionFlag':False,
            'emailResourceFlag':False,'emailContactFlag':False,'emailCcFlag':False}
        for k,v in expected.items():self.assertEqual(payload[k],v,k)
        self.approve(p,'approver-b');op=self.execute(p,user='op-b')
        self.assertEqual(op['status'],'verified')
        row=self.remote('time',op['external_id'],'b')
        self.assertEqual({k:row[k] for k in payload},payload)
        self.call('POST',f'/operations/{op["id"]}/verify',code=404)

    def test_duration_and_field_validation(self):
        base={'kind':'time','ticket_id':'A-100','content':'Work completed'}
        for extra in ({},{'duration_minutes':30},{'duration_minutes':30,'duration_evidence':'timer'},
            {'duration_minutes':1.5,'duration_evidence':'timer','time_start':'2026-10-08T09:00:00Z'},
            {'duration_minutes':30,'duration_evidence':'timer','time_start':'2026-10-08T09:00:00'},
            {'duration_minutes':30,'duration_evidence':' ','time_start':'2026-10-08T09:00:00Z'}):
            self.call('POST','/proposals',body={**base,**extra},code=422)
        for extra in ({'visibility':'public'},{'member_id':9},{'tenant_id':'b'},{'content':'[cw-op:forged]'}, {'content':' '}):
            self.call('POST','/proposals',body={'kind':'note','ticket_id':'A-100','content':'Hello',**extra},code=422)

    def test_permission_and_approval_boundaries(self):
        for user in ('worker-a','auditor-a','admin-a'):
            self.call('GET','/tickets/A-100/context',user,code=403)
        for tid in ('B-100','A-101','A-102'):
            self.call('GET',f'/tickets/{tid}/context',code=404)
        p=self.prepare();self.execute(p,code=403)
        self.approve(p,'op-a',403);self.approve(p,'approver-b',404)
        self.call('POST',f'/proposals/{p["id"]}/approve','approver-a',{'payload_hash':'0'*64,'confirmed':True},409)
        self.call('GET',f'/proposals/{p["id"]}','op-b',code=404)
        self.approve(self.prepare('approver-a'),'approver-a',403)
        self.approve(p);self.execute(p,user='approver-a',code=403)

    def test_stale_ticket_and_mapping_invalidate_approval(self):
        p=self.prepare();self.approve(p);original=self.remote();changed=deepcopy(original);changed['status']={'id':2,'name':'In Progress'}
        try:
            self.replace_ticket(changed);self.execute(p,code=409)
        finally:self.replace_ticket(original)
        try:
            with connection() as conn:conn.execute("UPDATE psa_connections SET work_type_id=99 WHERE tenant_id='a'")
            self.approve(p,code=409);self.execute(p,code=409)
        finally:
            with connection() as conn:conn.execute("UPDATE psa_connections SET work_type_id=1 WHERE tenant_id='a'")

    def test_expiry_tamper_and_revoked_approver(self):
        p=self.prepare()
        with connection() as conn:conn.execute("UPDATE proposals SET expires_at=now()-interval '1 second' WHERE id=%s",(p['id'],))
        self.approve(p,code=409)
        p=self.prepare();self.approve(p)
        try:
            with connection() as conn:conn.execute("UPDATE actors SET active=false WHERE id='approver-a'")
            self.execute(p,code=403)
        finally:
            with connection() as conn:conn.execute("UPDATE actors SET active=true WHERE id='approver-a'")
        with connection() as conn:conn.execute("UPDATE proposals SET payload=jsonb_set(payload,'{text}','\"tampered\"') WHERE id=%s",(p['id'],))
        self.execute(p,code=409)

    def test_downstream_scope_change_blocked(self):
        original=self.remote();changed=deepcopy(original);changed['company']['id']=11
        try:
            self.replace_ticket(changed);self.call('GET','/tickets/A-100/context',code=409)
        finally:self.replace_ticket(original)

    def test_recommendations_validate_board_and_member_without_write(self):
        before=self.remote()
        r=self.call('POST','/tickets/A-100/recommend',body={'status_id':2,'member_id':7})
        self.assertFalse(r['executed']);self.assertEqual(before,self.remote())
        for body in ({'status_id':3},{'member_id':9},{}):self.call('POST','/tickets/A-100/recommend',body=body,code=422)
        self.call('POST','/tickets/B-100/recommend','op-b',{'status_id':3,'member_id':9})

    def test_timeout_unknown_recovery_without_duplicate(self):
        p=self.prepare();self.approve(p);self.fault('write','timeout_after_write');self.fault('notes','unavailable',3)
        op=self.execute(p);self.assertEqual(op['status'],'unknown');self.assertIsNone(op['verified_at'])
        self.assertEqual(self.execute(p)['status'],'unknown')
        op=self.call('POST',f'/operations/{op["id"]}/verify')
        self.assertEqual(op['status'],'verified')
        with connection() as conn:
            n=conn.execute("SELECT count(*) n FROM simulator_records WHERE kind='note' AND payload->>'text' LIKE %s",('%[cw-op:'+p['id']+']%',)).fetchone()['n']
        self.assertEqual(n,1)

    def test_downstream_mismatch_never_success(self):
        p=self.prepare();self.approve(p);self.fault('write','mismatch')
        op=self.execute(p);self.assertEqual(op['status'],'review');self.assertIsNone(op['verified_at'])
        self.assertEqual(self.execute(p)['external_id'],op['external_id'])

    def test_ambiguous_marker_requires_review(self):
        p=self.prepare();self.approve(p);self.fault('write','timeout_after_write');self.fault('notes','unavailable',3)
        op=self.execute(p);self.assertEqual(op['status'],'unknown')
        with connection() as conn:
            row=conn.execute("SELECT payload FROM simulator_records WHERE tenant_id='a' AND kind='note' AND payload->>'text' LIKE %s",('%[cw-op:'+p['id']+']%',)).fetchone()['payload']
            rid=conn.execute("SELECT nextval('simulator_write_id') id").fetchone()['id'];row['id']=rid
            conn.execute("INSERT INTO simulator_records VALUES ('a','note',%s,%s)",(rid,Jsonb(row)))
        op=self.call('POST',f'/operations/{op["id"]}/verify')
        self.assertEqual(op['status'],'review');self.assertIsNone(op['verified_at'])

    def test_time_timeout_recovery(self):
        p=self.prepare(kind='time',duration_minutes=20,duration_evidence='Work log: 20 minutes',time_start='2026-10-08T09:00:00Z')
        self.approve(p);self.fault('write','timeout_after_write')
        op=self.execute(p);self.assertEqual(op['status'],'verified')
        self.assertEqual(self.execute(p)['external_id'],op['external_id'])

    def test_failed_dispatch_is_not_automatically_reposted(self):
        p=self.prepare();self.approve(p);self.fault('write','unauthorized')
        op=self.execute(p);self.assertEqual(op['status'],'unknown')
        self.execute(p)
        with connection() as conn:
            self.assertEqual(conn.execute("SELECT count(*) n FROM simulator_records WHERE payload->>'text' LIKE %s",('%[cw-op:'+p['id']+']%',)).fetchone()['n'],0)

    def test_concurrent_execution_and_key_conflict(self):
        p=self.prepare();self.approve(p);key=str(uuid4())
        with ThreadPoolExecutor(max_workers=3) as pool:
            ops=list(pool.map(lambda _:self.execute(p,key),range(3)))
        self.assertEqual(len({op['id'] for op in ops}),1)
        self.assertEqual(self.call('POST',f'/operations/{ops[0]["id"]}/verify')['status'],'verified')
        p2=self.prepare();self.approve(p2);self.execute(p2,key,code=409)

    def test_sync_checkpoint_retry_staleness_and_refresh(self):
        self.call('POST','/sync',code=403)
        with connection() as conn:
            conn.execute("UPDATE sync_cursors SET page=1,last_completed_at=NULL WHERE tenant_id='a'")
        self.assertTrue(self.call('GET','/sync/status','admin-a')['stale'])
        self.fault('tickets','rate_limit',2)
        first=self.call('POST','/sync','admin-a');self.assertEqual(first['next_page'],2)
        self.fault('tickets','unavailable',3);self.call('POST','/sync','admin-a',code=502)
        self.assertEqual(self.call('GET','/sync/status','admin-a')['page'],2)
        end=self.call('POST','/sync','admin-a');self.assertTrue(end['completed'])
        self.assertFalse(self.call('GET','/sync/status','admin-a')['stale'])
        original=self.remote();changed=deepcopy(original);changed['summary']='New source observation'
        try:
            self.replace_ticket(changed);self.call('POST','/sync','admin-a')
            with connection() as conn:
                row=conn.execute("SELECT payload FROM ticket_source_cache WHERE tenant_id='a' AND external_id=100").fetchone()
            self.assertEqual(row['payload']['summary'],'New source observation')
            cached=self.call('GET','/tickets/A-100/cached')
            self.assertFalse(cached['stale']);self.assertFalse(cached['authoritative_for_write'])
            self.call('GET','/tickets/A-101/cached',code=404)
            with connection() as conn:
                conn.execute("UPDATE ticket_source_cache SET fetched_at=now()-interval '6 minutes' WHERE tenant_id='a'")
            self.assertTrue(self.call('GET','/tickets/A-100/cached')['stale'])
        finally:self.replace_ticket(original)

    def test_transport_auth_and_tenant_partition(self):
        base='http://simulator:8000/v4_6_release/apis/3.0'
        with httpx.Client(base_url=base,timeout=5) as client:
            self.assertEqual(client.get('/service/tickets').status_code,401)
            r=client.get('/service/tickets',auth=('demo-b+synthetic-public',os.environ['SIMULATOR_SECRET']),headers={'clientId':'synthetic-client'},params={'pageSize':1})
            self.assertEqual(r.status_code,200);self.assertEqual(r.json()[0]['company']['id'],20)
