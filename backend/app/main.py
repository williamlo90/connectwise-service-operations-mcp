import json
import logging
import secrets
import time
from uuid import UUID,uuid4
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
import psycopg
from .config import settings
from .db import connection
from .passwords import hash_password, token_hash, verify_password

settings()  # Refuse invalid configuration before accepting requests.
app = FastAPI(title='Service Operations — Local Foundation', version='0.1.0', docs_url=None, redoc_url=None)
logger = logging.getLogger('service_ops')
logging.basicConfig(level=logging.INFO, format='%(message)s')
bearer = HTTPBearer(auto_error=False)
DUMMY_PASSWORD = hash_password(secrets.token_urlsafe(32))


@app.middleware('http')
async def request_log(request: Request, call_next):
    from .tracing import correlation_id
    try:
        request.state.correlation_id = str(UUID(request.headers.get('X-Correlation-ID','')))
    except ValueError:
        request.state.correlation_id = str(uuid4())
    correlation_id.set(request.state.correlation_id)
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        response = JSONResponse(status_code=500, content={'error':'internal_error'})
    response.headers['X-Correlation-ID'] = request.state.correlation_id
    response.headers['Cache-Control'] = 'no-store'
    route = request.scope.get('route')
    logger.info(json.dumps({'event':'http_request','correlation_id':request.state.correlation_id,
                           'method':request.method,'route':getattr(route,'path','unmatched'),
                           'status':response.status_code,'elapsed_ms':round((time.monotonic()-start)*1000,2)}))
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Default validation errors include input values; never echo supplied passwords.
    return JSONResponse(status_code=422, content={'error':'invalid_request'})


@app.exception_handler(psycopg.Error)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={'error':'database_unavailable'})


class Login(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1,max_length=100,pattern=r'^[a-z0-9-]+$')
    password: str = Field(min_length=1,max_length=256)


@app.get('/health/live')
def live():
    return {'status':'alive','platform_mode':'synthetic'}


@app.get('/health/ready')
def ready():
    with connection() as conn:
        row = conn.execute("SELECT name FROM schema_migrations WHERE name='003_assistant.sql'").fetchone()
    if not row:
        raise HTTPException(503,'schema_not_ready')
    return {'status':'ready','platform_mode':'synthetic'}


def audit(conn, actor, event, request):
    conn.execute('INSERT INTO audit_events (tenant_id,actor_id,event,correlation_id) VALUES (%s,%s,%s,%s)',
                 (actor['tenant_id'],actor['id'],event,request.state.correlation_id))


@app.post('/auth/login')
def login(body: Login, request: Request):
    failure = None
    token = None
    with connection() as conn:
        key = token_hash(body.username)
        conn.execute('INSERT INTO login_attempts (username_hash) VALUES (%s) ON CONFLICT DO NOTHING',(key,))
        attempt = conn.execute('SELECT * FROM login_attempts WHERE username_hash=%s FOR UPDATE',(key,)).fetchone()
        now = datetime.now(timezone.utc)
        if now - attempt['window_start'] >= timedelta(minutes=5):
            conn.execute('UPDATE login_attempts SET failures=0,window_start=now() WHERE username_hash=%s',(key,))
            attempt['failures'] = 0
        if attempt['failures'] >= 5:
            failure = 429
        else:
            actor = conn.execute('SELECT * FROM actors WHERE username=%s',(body.username,)).fetchone()
            valid = verify_password(body.password, actor['password_hash'] if actor else DUMMY_PASSWORD)
            if not actor or not actor['active'] or not valid:
                conn.execute('UPDATE login_attempts SET failures=failures+1 WHERE username_hash=%s',(key,))
                failure = 401
            else:
                conn.execute('UPDATE login_attempts SET failures=0,window_start=now() WHERE username_hash=%s',(key,))
                conn.execute('DELETE FROM sessions WHERE expires_at<=now()')
                token = secrets.token_urlsafe(32)
                conn.execute('INSERT INTO sessions (token_hash,actor_id,expires_at) VALUES (%s,%s,%s)',
                             (token_hash(token),actor['id'],now+timedelta(minutes=settings().session_minutes)))
                audit(conn,actor,'login',request)
    if failure:
        raise HTTPException(failure,'login_throttled' if failure==429 else 'invalid_credentials')
    return {'access_token':token,'token_type':'bearer','expires_in':settings().session_minutes*60}


def current_actor(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    if not credentials or len(credentials.credentials)>256:
        raise HTTPException(401,'authentication_required')
    with connection() as conn:
        actor = conn.execute('SELECT a.id,a.tenant_id,a.role FROM sessions s JOIN actors a ON a.id=s.actor_id WHERE s.token_hash=%s AND s.expires_at>now() AND a.active',
                             (token_hash(credentials.credentials),)).fetchone()
    if not actor:
        raise HTTPException(401,'invalid_session')
    return actor


Actor = Annotated[dict, Depends(current_actor)]


def allow(actor, roles):
    if actor['role'] not in roles:
        raise HTTPException(403,'insufficient_role')


@app.get('/me')
def me(actor: Actor):
    return {**actor,'platform_mode':'synthetic'}


@app.post('/auth/logout',status_code=204)
def logout(actor: Actor, credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)]):
    with connection() as conn:
        conn.execute('DELETE FROM sessions WHERE token_hash=%s',(token_hash(credentials.credentials),))
    return Response(status_code=204)


# Listing and direct-ID reads enforce the same tenant + company + board scope.
TICKET_QUERY = '''SELECT t.id,t.summary,t.status,t.company_id,t.board_id,t.version,t.updated_at,c.name AS company_name
FROM tickets t JOIN companies c ON c.tenant_id=t.tenant_id AND c.id=t.company_id
WHERE t.tenant_id=%s AND EXISTS (SELECT 1 FROM actor_scopes s
WHERE s.tenant_id=t.tenant_id AND s.actor_id=%s AND s.company_id=t.company_id AND s.board_id=t.board_id)'''


@app.get('/tickets')
def tickets(actor: Actor, request: Request, q: str = Query(default='',max_length=100),
            limit: int = Query(default=20,ge=1,le=100), offset: int = Query(default=0,ge=0,le=10000)):
    allow(actor,('operator','approver'))
    with connection() as conn:
        rows = conn.execute(TICKET_QUERY + ' AND (strpos(lower(t.summary),lower(%s))>0 OR strpos(lower(c.name),lower(%s))>0) ORDER BY t.id LIMIT %s OFFSET %s',
                            (actor['tenant_id'],actor['id'],q,q,limit+1,offset)).fetchall()
        audit(conn,actor,'ticket_list',request)
    return {'items':rows[:limit],'next_offset':offset+limit if len(rows)>limit else None,'platform_mode':'synthetic'}


@app.get('/tickets/{ticket_id}')
def ticket(ticket_id: str, actor: Actor, request: Request):
    allow(actor,('operator','approver'))
    if len(ticket_id)>100:
        raise HTTPException(404,'ticket_not_found')
    with connection() as conn:
        row = conn.execute(TICKET_QUERY+' AND t.id=%s',(actor['tenant_id'],actor['id'],ticket_id)).fetchone()
        if not row:
            raise HTTPException(404,'ticket_not_found')
        audit(conn,actor,'ticket_read',request)
    return {**row,'platform_mode':'synthetic'}


@app.get('/audit')
def audit_list(actor: Actor):
    allow(actor,('auditor',))
    with connection() as conn:
        rows = conn.execute('SELECT id,event,correlation_id,created_at FROM audit_events WHERE tenant_id=%s ORDER BY id DESC LIMIT 100',(actor['tenant_id'],)).fetchall()
    return {'items':rows}


@app.get('/admin/config')
def admin_config(actor: Actor):
    allow(actor,('administrator',))
    return {'platform_mode':'synthetic','session_minutes':settings().session_minutes}


from .workflows import router as workflow_router
app.include_router(workflow_router)
from .assistant import router as assistant_router
app.include_router(assistant_router)
