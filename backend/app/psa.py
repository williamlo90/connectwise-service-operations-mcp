"""HTTP transport with bounded read retries; POST is never automatically retried."""
import os
import time
from urllib.parse import urlparse
import httpx
from fastapi import HTTPException
from .db import connection
from .tracing import correlation_id


class PSA:
    def __init__(self, tenant):
        with connection() as conn:
            self.config=conn.execute('SELECT * FROM psa_connections WHERE tenant_id=%s',(tenant,)).fetchone()
        if not self.config:raise HTTPException(503,'platform_not_configured')
        cfg=self.config
        # This phase deliberately cannot address a real vendor or arbitrary host.
        url=urlparse(cfg['base_url'])
        if url.scheme!='http' or url.hostname!='simulator' or url.port!=8000:
            raise HTTPException(503,'connected_mode_not_enabled')
        secret=os.environ.get(cfg['private_key_env'],'')
        if len(secret)<24:raise HTTPException(503,'platform_credentials_missing')
        self.client=httpx.Client(base_url=cfg['base_url']+'/',
            auth=(cfg['company_login']+'+'+cfg['public_key'],secret),
            headers={'clientId':cfg['client_id'],'Accept':'application/json','X-Correlation-ID':correlation_id.get()},
            timeout=0.6,follow_redirects=False,trust_env=False)

    def __enter__(self):return self
    def __exit__(self,*args):self.client.close()

    def get(self,path,params=None):
        for attempt in range(3):
            try:
                response=self.client.get(path,params=params)
                if response.status_code in (429,502,503,504) and attempt<2:
                    time.sleep(0.05*(2**attempt));continue
                if response.status_code in (401,403):raise HTTPException(502,'downstream_credentials_rejected')
                if response.status_code==429:raise HTTPException(503,'downstream_rate_limited')
                if response.status_code==404:raise HTTPException(404,'downstream_not_found')
                if not response.is_success:raise HTTPException(502,'downstream_read_failed')
                return response.json()
            except (httpx.TransportError,ValueError):
                if attempt==2:raise HTTPException(502,'downstream_read_failed')
                time.sleep(0.05*(2**attempt))

    def all(self,path,params=None):
        rows=[]
        for page in range(1,101):
            batch=self.get(path,{**(params or {}),'page':page,'pageSize':100})
            if not isinstance(batch,list):raise HTTPException(502,'invalid_downstream_schema')
            rows.extend(batch)
            if len(batch)<100:return rows
        raise HTTPException(502,'downstream_output_limit')

    def post(self,path,payload):
        try:
            response=self.client.post(path,json=payload)
            if not response.is_success:return None
            value=response.json()
            return value if isinstance(value,dict) and isinstance(value.get('id'),int) else None
        except (httpx.TransportError,ValueError):return None
