"""HTTP acceptance against the dedicated disposable PostgreSQL test stack."""
import os
import unittest
import httpx
from app.db import connection
from app.config import settings
from app.passwords import token_hash
from app.migrate import migrate
from app.seed import seed
from app.config import Settings
from pydantic import ValidationError


class FoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if settings().app_environment != 'test' or settings().db_name != 'cw_ops_test':
            raise RuntimeError('Tests require the isolated cw_ops_test database')
        cls.client = httpx.Client(base_url='http://api:8000',timeout=10)
        cls.password = os.environ['DEMO_PASSWORD']

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def auth(self, username='op-a'):
        result = self.client.post('/auth/login',json={'username':username,'password':self.password})
        self.assertEqual(result.status_code,200)
        return {'Authorization':'Bearer '+result.json()['access_token']}

    def test_health(self):
        self.assertEqual(self.client.get('/health/live').status_code,200)
        self.assertEqual(self.client.get('/health/ready').json()['status'],'ready')

    def test_fail_closed_configuration(self):
        for values in ({'db_password':'short-secret'}, {'platform_mode':'connected'}, {'app_environment':'production'}):
            with self.assertRaises(ValidationError) as result:
                Settings(**values)
            self.assertNotIn('short-secret',str(result.exception))

    def test_anonymous_and_invalid_token(self):
        for headers in ({},{'Authorization':'Bearer invalid'}):
            for path in ('/me','/tickets','/tickets/A-100','/audit','/admin/config'):
                self.assertEqual(self.client.get(path,headers=headers).status_code,401)

    def test_scope_and_direct_id(self):
        for username,tenant,expected,denied in [('op-a','a','A-100',['B-100','A-101','A-102']),('op-b','b','B-100',['A-100','A-101'])]:
            headers=self.auth(username)
            self.assertEqual(self.client.get('/me',headers=headers).json()['tenant_id'],tenant)
            result=self.client.get('/tickets?q=Acme',headers={**headers,'X-Tenant-ID':'b','X-Role':'administrator'}).json()
            self.assertEqual([t['id'] for t in result['items']],[expected])
            self.assertEqual(self.client.get('/tickets/'+expected,headers=headers).status_code,200)
            for tid in denied:
                self.assertEqual(self.client.get('/tickets/'+tid,headers=headers).status_code,404)

    def test_roles(self):
        matrix={'op-a':(200,403,403),'approver-a':(200,403,403),'admin-a':(403,200,403),'auditor-a':(403,403,200),'worker-a':(403,403,403)}
        for user,expected in matrix.items():
            headers=self.auth(user)
            for path,code in zip(['/tickets','/admin/config','/audit'],expected):
                self.assertEqual(self.client.get(path,headers=headers).status_code,code)

    def test_validation_and_query_injection(self):
        response=self.client.post('/auth/login',json={'username':'op-a','password':self.password,'tenant_id':'b','role':'administrator'})
        self.assertEqual(response.status_code,422)
        self.assertNotIn(self.password,response.text)
        headers=self.auth()
        self.assertEqual(self.client.get('/tickets',params={'q':"' OR 1=1 --"},headers=headers).json()['items'],[])
        self.assertEqual(self.client.get('/tickets?limit=101',headers=headers).status_code,422)
        self.assertEqual(self.client.get('/tickets?offset=-1',headers=headers).status_code,422)
        self.assertEqual(self.client.get('/tickets?limit=1&offset=1',headers=headers).json()['items'],[])

    def test_logout_expiry_and_disabled_actor(self):
        headers=self.auth()
        self.assertEqual(self.client.post('/auth/logout',headers=headers).status_code,204)
        self.assertEqual(self.client.get('/me',headers=headers).status_code,401)
        headers=self.auth()
        with connection() as conn:
            conn.execute("UPDATE sessions SET expires_at=now()-interval '1 second' WHERE token_hash=%s",(token_hash(headers['Authorization'][7:]),))
        self.assertEqual(self.client.get('/me',headers=headers).status_code,401)
        headers=self.auth('op-b')
        try:
            with connection() as conn:
                conn.execute("UPDATE actors SET active=false WHERE id='op-b'")
            self.assertEqual(self.client.get('/tickets',headers=headers).status_code,401)
        finally:
            with connection() as conn:
                conn.execute("UPDATE actors SET active=true WHERE id='op-b'")

    def test_login_throttle(self):
        for _ in range(5):
            self.assertEqual(self.client.post('/auth/login',json={'username':'nonexistent','password':'bad'}).status_code,401)
        self.assertEqual(self.client.post('/auth/login',json={'username':'nonexistent','password':'bad'}).status_code,429)

    def test_audit_and_secret_storage(self):
        headers=self.auth()
        response=self.client.get('/tickets/A-100',headers=headers)
        cid=response.headers['x-correlation-id']
        self.assertEqual(response.headers['cache-control'],'no-store')
        auditor=self.auth('auditor-a')
        result=self.client.get('/audit',headers=auditor)
        self.assertIn(cid,result.text)
        self.assertNotIn(self.password,result.text)
        with connection() as conn:
            event=conn.execute('SELECT * FROM audit_events WHERE correlation_id=%s',(cid,)).fetchone()
            self.assertEqual(event['tenant_id'],'a')
            self.assertEqual(event['actor_id'],'op-a')
            session=conn.execute('SELECT token_hash FROM sessions WHERE actor_id=%s',('op-a',)).fetchone()
            self.assertEqual(len(session['token_hash']),64)
            self.assertNotEqual(session['token_hash'],headers['Authorization'][7:])

    def test_idempotent_migration_and_seed(self):
        migrate()
        seed()
        with connection() as conn:
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM tickets').fetchone()['n'],4)
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM actors').fetchone()['n'],7)


if __name__=='__main__':
    unittest.main(verbosity=2)
