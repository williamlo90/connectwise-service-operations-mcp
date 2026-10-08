"""Run one bounded scheduler tick at a time; SIGTERM finishes the current tick."""
import argparse
import json
import signal
from threading import Event
from .db import connection


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--health', action='store_true')
    args = parser.parse_args()
    if args.health:
        with connection() as conn:
            row = conn.execute("SELECT last_tick>now()-interval '30 seconds' AS healthy FROM worker_heartbeat WHERE name='sync'").fetchone()
        return 0 if row and row['healthy'] else 1
    from . import main as domain_application  # Initialize routes before shared workflow services.
    from .automation import tick
    stopping = Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stopping.set())
    while not stopping.is_set():
        try:
            result = tick()
            if result:
                print(json.dumps({'event': 'automation_tick', **result}), flush=True)
        except Exception:
            print(json.dumps({'event': 'automation_unavailable'}), flush=True)
            if args.once:
                return 1
        if args.once:
            return 0
        stopping.wait(2)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
