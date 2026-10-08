CREATE TABLE automation_schedules (
 tenant_id text PRIMARY KEY REFERENCES tenants(id),
 enabled boolean NOT NULL DEFAULT true,
 interval_seconds integer NOT NULL DEFAULT 300 CHECK(interval_seconds BETWEEN 60 AND 3600),
 next_due timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE automation_jobs (
 id uuid PRIMARY KEY, tenant_id text NOT NULL REFERENCES tenants(id),
 event_key text NOT NULL, status text NOT NULL DEFAULT 'queued',
 attempts integer NOT NULL DEFAULT 0, total_attempts integer NOT NULL DEFAULT 0,
 pages integer NOT NULL DEFAULT 0, next_attempt timestamptz NOT NULL DEFAULT now(),
 last_error text, created_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 UNIQUE(tenant_id,event_key), UNIQUE(tenant_id,id),
 CHECK(status IN ('queued','retry','review','completed'))
);
CREATE UNIQUE INDEX automation_one_open_job ON automation_jobs(tenant_id) WHERE status <> 'completed';
CREATE TABLE ticket_change_events (
 id uuid PRIMARY KEY, tenant_id text NOT NULL, external_id integer NOT NULL,
 generation integer NOT NULL, source_hash text NOT NULL,
 detected_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,generation,external_id,source_hash),
 FOREIGN KEY(tenant_id) REFERENCES tenants(id)
);
CREATE TABLE worker_heartbeat (
 name text PRIMARY KEY, last_tick timestamptz NOT NULL
);
