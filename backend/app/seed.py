"""Idempotent synthetic fixtures; preserve existing passwords and records."""
import os
from .config import settings
from .db import connection
from .passwords import hash_password
from .seed_phase2 import seed_phase2

USERS = [('op-a','a','operator'),('approver-a','a','approver'),('admin-a','a','administrator'),
         ('auditor-a','a','auditor'),('worker-a','a','worker'),('op-b','b','operator')]


def seed():
    if settings().platform_mode != 'synthetic':
        raise RuntimeError('Synthetic mode required')
    password = os.environ.get('DEMO_PASSWORD', '')
    if len(password) < 24 or password.startswith('replace-'):
        raise RuntimeError('Set a generated DEMO_PASSWORD of at least 24 characters')
    with connection() as conn:
        for tenant in ('a','b'):
            conn.execute('INSERT INTO tenants VALUES (%s,%s) ON CONFLICT DO NOTHING', (tenant,f'Demo MSP {tenant.upper()}'))
            for cid in ('acme','restricted'):
                conn.execute('INSERT INTO companies VALUES (%s,%s,%s) ON CONFLICT DO NOTHING', (tenant,cid,'Acme Demo' if cid=='acme' else 'Restricted Demo'))
            for bid in ('support','restricted'):
                conn.execute('INSERT INTO boards VALUES (%s,%s,%s) ON CONFLICT DO NOTHING', (tenant,bid,bid.title()))
        for username,tenant,role in USERS:
            conn.execute('INSERT INTO actors (id,tenant_id,username,password_hash,role) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                         (username,tenant,username,hash_password(password),role))
            if role in ('operator','approver'):
                conn.execute('INSERT INTO actor_scopes VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING', (tenant,username,'acme','support'))
        fixtures = [('a','A-100','acme','support','VPN connection fails'),
                    ('a','A-101','restricted','support','Restricted company ticket'),
                    ('a','A-102','acme','restricted','Restricted board ticket'),
                    ('b','B-100','acme','support','Printer unavailable')]
        for tenant,tid,cid,bid,summary in fixtures:
            conn.execute("INSERT INTO tickets (tenant_id,id,company_id,board_id,summary,status) VALUES (%s,%s,%s,%s,%s,'New') ON CONFLICT DO NOTHING",
                         (tenant,tid,cid,bid,summary))
        seed_phase2(conn, password)
    print('Synthetic seed ready: seven actors, two tenants, four local tickets and PSA simulator fixtures. Existing records preserved.')


if __name__ == '__main__':
    seed()
