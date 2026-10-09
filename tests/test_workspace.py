"""Browser API access is bounded by the same tenant and ticket scopes."""
import os
import unittest
import httpx
from app.db import connection
from app.config import settings


class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if settings().app_environment != 'test' or settings().db_name != 'cw_ops_test':
            raise RuntimeError('Requires isolated test database')
        cls.client = httpx.Client(base_url='http://api:8000', timeout=15)
        cls.headers = {}
        for user in ('op-a','op-b','approver-a','auditor-a'):
            response = cls.client.post('/auth/login', json={'username':user,'password':os.environ['DEMO_PASSWORD']})
            response.raise_for_status()
            cls.headers[user] = {'Authorization':'Bearer '+response.json()['access_token']}

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_workspace_assets_and_security_headers(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertIn('Review the proposed update.',response.text)
        self.assertIn("frame-ancestors 'none'",response.headers['content-security-policy'])
        self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        self.assertEqual(self.client.get('/assets/workspace.js').status_code,200)

    def test_activity_tenant_role_scope_and_approval(self):
        self.assertEqual(self.client.get('/workspace/activity').status_code,401)
        self.assertEqual(self.client.get('/workspace/activity',headers=self.headers['auditor-a']).status_code,403)
        response=self.client.post('/workflow/proposals',headers=self.headers['op-a'],json={
            'kind':'note','ticket_id':'A-100','content':'Workspace scoped access acceptance.'})
        self.assertEqual(response.status_code,201,response.text)
        proposal=response.json()
        def items(user):
            result=self.client.get('/workspace/activity',headers=self.headers[user])
            self.assertEqual(result.status_code,200,result.text)
            return result.json()['items']
        row=next(r for r in items('approver-a') if r['id']==proposal['id'])
        self.assertEqual(row['status'],'proposed')
        self.assertNotIn(proposal['id'],[r['id'] for r in items('op-b')])
        approved=self.client.post(f'/workflow/proposals/{proposal["id"]}/approve',headers=self.headers['approver-a'],json={'confirmed':True,'payload_hash':proposal['payload_hash']})
        self.assertEqual(approved.status_code,200,approved.text)
        self.assertEqual(next(r for r in items('op-a') if r['id']==proposal['id'])['status'],'approved')
        with connection() as conn:
            scopes=conn.execute("DELETE FROM actor_scopes WHERE tenant_id='a' AND actor_id='approver-a' RETURNING *").fetchall()
        try:
            self.assertEqual(items('approver-a'),[])
        finally:
            with connection() as conn:
                for scope in scopes:
                    conn.execute('INSERT INTO actor_scopes (tenant_id,actor_id,company_id,board_id) VALUES (%s,%s,%s,%s)',tuple(scope[k] for k in ('tenant_id','actor_id','company_id','board_id')))

    def test_direct_review_scopes_and_current_receipt(self):
        response=self.client.post('/workflow/proposals',headers=self.headers['op-a'],json={
            'kind':'note','ticket_id':'A-100','content':'MCP review entry acceptance.'})
        self.assertEqual(response.status_code,201,response.text)
        proposal=response.json();path=f'/workspace/proposals/{proposal["id"]}'
        self.assertEqual(self.client.get(path).status_code,401)
        self.assertEqual(self.client.get(path,headers=self.headers['op-b']).status_code,404)
        self.assertEqual(self.client.get(path,headers=self.headers['auditor-a']).status_code,403)
        review=self.client.get(path,headers=self.headers['approver-a'])
        self.assertEqual(review.status_code,200,review.text)
        self.assertEqual(review.json()['status'],'proposed')
        self.assertEqual(review.json()['payload_hash'],proposal['payload_hash'])
        self.assertEqual(len(review.json()['source_hash']),64)
        self.assertNotIn('source_snapshot',review.json())
        approved=self.client.post(f'/workflow/proposals/{proposal["id"]}/approve',headers=self.headers['approver-a'],json={
            'confirmed':True,'payload_hash':proposal['payload_hash']})
        self.assertEqual(approved.status_code,200,approved.text)
        self.assertEqual(self.client.get(path,headers=self.headers['op-a']).json()['status'],'approved')
        with connection() as conn:
            scopes=conn.execute("DELETE FROM actor_scopes WHERE tenant_id='a' AND actor_id='approver-a' RETURNING *").fetchall()
        try:
            self.assertEqual(self.client.get(path,headers=self.headers['approver-a']).status_code,404)
        finally:
            with connection() as conn:
                for scope in scopes:
                    conn.execute('INSERT INTO actor_scopes (tenant_id,actor_id,company_id,board_id) VALUES (%s,%s,%s,%s)',tuple(scope[k] for k in ('tenant_id','actor_id','company_id','board_id')))
