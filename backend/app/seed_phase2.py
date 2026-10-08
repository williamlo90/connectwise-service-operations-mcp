"""Synthetic mappings are explicit, not inferred from company names."""
from psycopg.types.json import Jsonb
from .passwords import hash_password


def seed_phase2(conn, password):
    conn.execute("INSERT INTO actors (id,tenant_id,username,password_hash,role) VALUES ('approver-b','b','approver-b',%s,'approver') ON CONFLICT DO NOTHING",(hash_password(password),))
    conn.execute("INSERT INTO actor_scopes VALUES ('b','approver-b','acme','support') ON CONFLICT DO NOTHING")
    for tenant,company,board,member,work_type,work_role in [('a',10,1,7,1,1),('b',20,2,9,2,2)]:
        conn.execute('''INSERT INTO psa_connections VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                     (tenant,'http://simulator:8000/v4_6_release/apis/3.0',f'demo-{tenant}','synthetic-public',
                      'SIMULATOR_SECRET','synthetic-client',Jsonb({str(company):'acme',str(company+1):'restricted'}),
                      Jsonb({str(board):'support',str(board+10):'restricted'}),
                      Jsonb({f'op-{tenant}':member,f'approver-{tenant}':member}),work_type,work_role,'Asia/Jakarta'))
        conn.execute('INSERT INTO sync_cursors (tenant_id) VALUES (%s) ON CONFLICT DO NOTHING',(tenant,))
        records=[('company',company,{'id':company,'identifier':f'ACME-{tenant}','name':'Acme Demo'}),
                 ('board',board,{'id':board,'name':'Support','inactiveFlag':False}),
                 ('member',member,{'id':member,'identifier':f'tech-{tenant}','name':f'Technician {tenant}'})]
        for tid,cid,bid,summary in [(100,company,board,'VPN connection fails' if tenant=='a' else 'Printer unavailable'),
                                    (101,company+1,board,'Restricted company ticket'),
                                    (102,company,board+10,'Restricted board ticket')]:
            records.append(('ticket',tid,{'id':tid,'summary':summary,'company':{'id':cid,'name':'Acme Demo'},
                'board':{'id':bid,'name':'Support'},'status':{'id':1,'name':'New'},'owner':{'id':member},
                '_info':{'lastUpdated':'2026-10-08T00:00:00Z'}}))
        records.extend([('note',1,{'id':1,'ticketId':100,'text':'Technician confirmed the reported issue.',
            'internalAnalysisFlag':True,'detailDescriptionFlag':False,'resolutionFlag':False,'internalFlag':True,'externalFlag':False}),
            ('note',2,{'id':2,'ticketId':100,'text':'Customer reported a service interruption.',
            'internalAnalysisFlag':False,'detailDescriptionFlag':True,'resolutionFlag':False,'internalFlag':False,'externalFlag':True})])
        for kind,rid,payload in records:
            conn.execute('INSERT INTO simulator_records VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING', (tenant,kind,rid,Jsonb(payload)))
