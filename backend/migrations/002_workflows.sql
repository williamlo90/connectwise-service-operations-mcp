CREATE TABLE psa_connections (
 tenant_id text PRIMARY KEY REFERENCES tenants(id),
 base_url text NOT NULL, company_login text NOT NULL, public_key text NOT NULL,
 private_key_env text NOT NULL, client_id text NOT NULL,
 company_map jsonb NOT NULL, board_map jsonb NOT NULL,
 member_map jsonb NOT NULL, work_type_id integer NOT NULL, work_role_id integer NOT NULL,
 timezone text NOT NULL DEFAULT 'Asia/Jakarta'
);
CREATE TABLE proposals (
 id uuid PRIMARY KEY, tenant_id text NOT NULL, actor_id text NOT NULL,
 ticket_id text NOT NULL, external_ticket_id integer NOT NULL,
 kind text NOT NULL CHECK(kind IN ('note','time')),
 payload jsonb NOT NULL, payload_hash text NOT NULL, source_hash text NOT NULL,
 source_snapshot jsonb NOT NULL, evidence jsonb NOT NULL,
 expires_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,id),
 FOREIGN KEY(tenant_id,actor_id) REFERENCES actors(tenant_id,id),
 FOREIGN KEY(tenant_id,ticket_id) REFERENCES tickets(tenant_id,id)
);
CREATE TABLE approvals (
 id uuid PRIMARY KEY, tenant_id text NOT NULL, proposal_id uuid NOT NULL UNIQUE,
 actor_id text NOT NULL, payload_hash text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(tenant_id,proposal_id) REFERENCES proposals(tenant_id,id),
 FOREIGN KEY(tenant_id,actor_id) REFERENCES actors(tenant_id,id)
);
CREATE TABLE operations (
 id uuid PRIMARY KEY, tenant_id text NOT NULL, proposal_id uuid NOT NULL UNIQUE,
 idempotency_key uuid NOT NULL, request_hash text NOT NULL,
 status text NOT NULL CHECK(status IN ('dispatched','unknown','verified','review')),
 external_id integer, expected jsonb NOT NULL, observed jsonb,
 error_code text, created_at timestamptz NOT NULL DEFAULT now(), verified_at timestamptz,
 UNIQUE(tenant_id,idempotency_key),
 FOREIGN KEY(tenant_id,proposal_id) REFERENCES proposals(tenant_id,id)
);
CREATE TABLE sync_cursors (
 tenant_id text PRIMARY KEY REFERENCES tenants(id), page integer NOT NULL DEFAULT 1,
 generation integer NOT NULL DEFAULT 1, last_completed_at timestamptz
);
CREATE TABLE ticket_source_cache (
 tenant_id text NOT NULL REFERENCES tenants(id), external_id integer NOT NULL,
 payload jsonb NOT NULL, source_hash text NOT NULL,
 fetched_at timestamptz NOT NULL DEFAULT now(), generation integer NOT NULL,
 PRIMARY KEY(tenant_id,external_id)
);
-- Simulator owns these tables. The production-path adapter never accesses them.
CREATE TABLE simulator_records (
 tenant_id text NOT NULL, kind text NOT NULL, id integer NOT NULL, payload jsonb NOT NULL,
 PRIMARY KEY(tenant_id,kind,id)
);
CREATE SEQUENCE simulator_write_id START 1000;
CREATE TABLE simulator_faults (
 tenant_id text NOT NULL, route text NOT NULL, mode text NOT NULL, remaining integer NOT NULL,
 PRIMARY KEY(tenant_id,route)
);
