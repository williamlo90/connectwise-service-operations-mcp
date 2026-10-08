"""Transactional, checksum-verified forward SQL migrations."""
from pathlib import Path
import hashlib
from .db import connection


def migrate():
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(3001001)')
        conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY, sha256 text NOT NULL)')
        for path in sorted((Path(__file__).resolve().parents[1] / 'migrations').glob('*.sql')):
            content = path.read_text(encoding='utf-8')
            digest = hashlib.sha256(content.encode()).hexdigest()
            previous = conn.execute('SELECT sha256 FROM schema_migrations WHERE name=%s', (path.name,)).fetchone()
            if previous:
                if previous['sha256'] != digest:
                    raise RuntimeError('Migration checksum mismatch')
                continue
            conn.execute(content)
            conn.execute('INSERT INTO schema_migrations VALUES (%s,%s)', (path.name, digest))
    print('Migrations ready')


if __name__ == '__main__':
    migrate()
