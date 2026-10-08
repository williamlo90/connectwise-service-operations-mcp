"""Host-operator monitoring: aggregate metadata only, durable local alert inbox.

No outbound webhook or application-user endpoint. Run a single instance per
inbox; its filesystem must be restricted to the deployment operator.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
from threading import Event
from uuid import uuid4
from .db import connection


def snapshot():
    with connection() as conn:
        queue = conn.execute("""SELECT count(*) FILTER (WHERE status IN ('queued','retry')) pending,
            count(*) FILTER (WHERE status='review') review,
            coalesce(max(extract(epoch FROM now()-created_at)) FILTER
              (WHERE status IN ('queued','retry')),0) oldest_seconds FROM automation_jobs""").fetchone()
        heartbeat = conn.execute("SELECT last_tick>now()-interval '30 seconds' healthy FROM worker_heartbeat WHERE name='sync'").fetchone()
        stale = conn.execute("""SELECT count(*) n FROM sync_cursors c JOIN automation_schedules s USING(tenant_id)
            WHERE s.enabled AND (c.last_completed_at IS NULL OR
              c.last_completed_at<now()-interval '1 second'*(s.interval_seconds+60))""").fetchone()['n']
        operations = conn.execute('SELECT status,count(*) n FROM operations GROUP BY status').fetchall()
        assistant = conn.execute("""SELECT status,count(*) n,avg(latency_ms) mean_elapsed_ms,
            sum(cost_usd) known_cost_usd,count(*) FILTER(WHERE cost_usd IS NULL) unknown_cost_count
            FROM assistant_runs GROUP BY status""").fetchall()
    return {'database': 'ready', 'worker_healthy': bool(heartbeat and heartbeat['healthy']),
            'queue': queue, 'stale_sync_count': stale, 'operations': operations, 'assistant': assistant}


def incidents(metrics):
    if metrics['database'] != 'ready':
        return {'database_unavailable'}
    found = set()
    if not metrics['worker_healthy']: found.add('worker_stale')
    if metrics['queue']['oldest_seconds'] > 60: found.add('queue_backlog')
    if metrics['queue']['review']: found.add('sync_review')
    if metrics['stale_sync_count']: found.add('sync_stale')
    if any(r['status'] != 'verified' and r['n'] for r in metrics['operations']): found.add('write_review')
    return found


def atomic_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, default=str, indent=2)+'\n', encoding='utf-8')
    os.replace(temp, path)


def poll(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        metrics = snapshot()
    except Exception:
        # Never write exception text, connection strings or business payloads.
        metrics = {'database': 'unavailable'}
    active = incidents(metrics)
    state_path = directory/'state.json'
    previous = set(json.loads(state_path.read_text(encoding='utf-8'))['active']) if state_path.exists() else set()
    received = []
    for code in sorted(active ^ previous):
        event = {'id': str(uuid4()), 'received_at': datetime.now(timezone.utc).isoformat(),
                 'code': code, 'state': 'firing' if code in active else 'resolved'}
        # Append+fsync before state advance: restart can repeat, never silently
        # acknowledge an alert that has not reached the local inbox.
        inbox = directory/'alerts.jsonl'
        if inbox.exists() and inbox.stat().st_size >= 5*1024*1024:
            os.replace(inbox, directory/'alerts.previous.jsonl')
        with inbox.open('a', encoding='utf-8') as out:
            out.write(json.dumps(event)+'\n'); out.flush(); os.fsync(out.fileno())
        received.append(event)
    atomic_json(directory/'metrics.json', {'collected_at': datetime.now(timezone.utc).isoformat(), **metrics})
    atomic_json(state_path, {'active': sorted(active)})
    return received


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', default='/inbox')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    stopping = Event()
    for sig in (signal.SIGTERM, signal.SIGINT): signal.signal(sig, lambda *_: stopping.set())
    while not stopping.is_set():
        events = poll(args.directory)
        if events: print(json.dumps({'event': 'local_alert_delivery', 'received': len(events)}), flush=True)
        if args.once: return
        stopping.wait(10)


if __name__ == '__main__': main()
