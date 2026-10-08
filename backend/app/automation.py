"""Durable read-only PSA synchronization; job state and checkpoint commit together."""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from .db import connection
from .main import Actor, allow, audit
from .workflows import sync_page
from .tracing import correlation_id

router = APIRouter(prefix='/automation', tags=['automation'])
PERMANENT = {'downstream_credentials_rejected', 'platform_credentials_missing',
             'platform_not_configured', 'connected_mode_not_enabled', 'invalid_downstream_schema',
             'downstream_not_found', 'scan_page_limit'}


def enqueue_due():
    """Coalesce missed intervals; a review item blocks new work for its tenant."""
    with connection() as conn:
        rows = conn.execute('''SELECT * FROM automation_schedules WHERE enabled AND next_due<=now()
            ORDER BY next_due,tenant_id FOR UPDATE SKIP LOCKED LIMIT 10''').fetchall()
        for row in rows:
            conn.execute('''INSERT INTO automation_jobs(id,tenant_id,event_key) VALUES (%s,%s,%s)
                ON CONFLICT DO NOTHING''', (uuid4(), row['tenant_id'], row['next_due'].isoformat()))
            conn.execute("UPDATE automation_schedules SET next_due=now()+interval '1 second'*interval_seconds WHERE tenant_id=%s",
                         (row['tenant_id'],))
        return len(rows)


def process_one():
    # Keep the row lock through the bounded read. Process death rolls back both
    # the page checkpoint and job state, so the page is safely re-read.
    with connection() as conn:
        job = conn.execute('''SELECT j.* FROM automation_jobs j JOIN automation_schedules s USING(tenant_id)
            WHERE s.enabled AND j.status IN ('queued','retry') AND j.next_attempt<=now()
            ORDER BY j.next_attempt,j.created_at,j.tenant_id FOR UPDATE OF j SKIP LOCKED LIMIT 1''').fetchone()
        if not job:
            return None
        token = correlation_id.set(str(job['id']))
        try:
            try:
                with conn.transaction():
                    if job['pages'] >= 100:
                        raise HTTPException(502, 'scan_page_limit')
                    page = sync_page(job['tenant_id'], conn)
            except HTTPException as error:
                attempt = job['attempts'] + 1
                code = error.detail if error.detail in PERMANENT | {'downstream_read_failed', 'downstream_rate_limited'} else 'sync_failed'
                status = 'review' if code in PERMANENT or attempt >= 3 else 'retry'
                conn.execute('''UPDATE automation_jobs SET status=%s,attempts=%s,total_attempts=total_attempts+1,
                    last_error=%s,next_attempt=%s WHERE id=%s''',
                    (status, attempt, code, datetime.now(timezone.utc)+timedelta(seconds=min(60,5*2**(attempt-1))), job['id']))
                return {'job_id': str(job['id']), 'status': status, 'error': code}
            conn.execute('''UPDATE automation_jobs SET status=%s,pages=pages+1,attempts=0,total_attempts=total_attempts+1,
                last_error=NULL,next_attempt=now(),finished_at=CASE WHEN %s THEN now() ELSE NULL END WHERE id=%s''',
                ('completed' if page['completed'] else 'queued', page['completed'], job['id']))
            return {'job_id': str(job['id']), 'status': 'completed' if page['completed'] else 'queued', **page}
        finally:
            correlation_id.reset(token)


def tick():
    enqueue_due()
    result = process_one()
    with connection() as conn:
        conn.execute("INSERT INTO worker_heartbeat VALUES ('sync',now()) ON CONFLICT(name) DO UPDATE SET last_tick=excluded.last_tick")
    return result


@router.get('/status')
def status(actor: Actor):
    allow(actor, ('administrator',))
    with connection() as conn:
        schedule = conn.execute('SELECT * FROM automation_schedules WHERE tenant_id=%s', (actor['tenant_id'],)).fetchone()
        counts = conn.execute('SELECT status,count(*) count FROM automation_jobs WHERE tenant_id=%s GROUP BY status', (actor['tenant_id'],)).fetchall()
        heartbeat = conn.execute("SELECT last_tick,last_tick>now()-interval '30 seconds' AS healthy FROM worker_heartbeat WHERE name='sync'").fetchone()
    return {'schedule': schedule, 'jobs': counts, 'worker': heartbeat, 'action': 'read_only_ticket_sync'}


@router.get('/jobs')
def jobs(actor: Actor, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=10000)):
    allow(actor, ('administrator',))
    with connection() as conn:
        rows = conn.execute('''SELECT id,status,attempts,total_attempts,pages,last_error,next_attempt,created_at,finished_at
            FROM automation_jobs WHERE tenant_id=%s ORDER BY created_at DESC,id LIMIT %s OFFSET %s''',
            (actor['tenant_id'], limit+1, offset)).fetchall()
    return {'items': rows[:limit], 'next_offset': offset+limit if len(rows)>limit else None}


class Schedule(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool = Field(strict=True)
    interval_seconds: int = Field(ge=60, le=3600, strict=True)


@router.post('/schedule')
def schedule(body: Schedule, actor: Actor, request: Request):
    allow(actor, ('administrator',))
    with connection() as conn:
        conn.execute('''INSERT INTO automation_schedules(tenant_id,enabled,interval_seconds) VALUES (%s,%s,%s)
            ON CONFLICT(tenant_id) DO UPDATE SET enabled=excluded.enabled,interval_seconds=excluded.interval_seconds''',
            (actor['tenant_id'], body.enabled, body.interval_seconds))
        audit(conn, actor, 'automation_schedule_changed', request)
    return {'enabled': body.enabled, 'interval_seconds': body.interval_seconds}


@router.post('/jobs/{job_id}/retry')
def retry(job_id: UUID, actor: Actor, request: Request):
    allow(actor, ('administrator',))
    with connection() as conn:
        job = conn.execute('SELECT * FROM automation_jobs WHERE id=%s AND tenant_id=%s FOR UPDATE', (job_id,actor['tenant_id'])).fetchone()
        if not job:
            raise HTTPException(404, 'job_not_found')
        if job['status'] != 'review':
            raise HTTPException(409, 'job_not_in_review')
        conn.execute("UPDATE automation_jobs SET status='queued',attempts=0,pages=0,next_attempt=now(),last_error=NULL WHERE id=%s", (job_id,))
        # Restart the read-only scan after operator repair; existing cache/event
        # hashes prevent duplicate observations while durable history is kept.
        conn.execute('UPDATE sync_cursors SET page=1 WHERE tenant_id=%s', (actor['tenant_id'],))
        audit(conn, actor, 'automation_retry_requested', request)
    return {'job_id': job_id, 'status': 'queued'}
