CREATE TABLE tenants (id text PRIMARY KEY, name text NOT NULL);
CREATE TABLE actors (
 id text PRIMARY KEY, tenant_id text NOT NULL REFERENCES tenants(id),
 username text NOT NULL UNIQUE, password_hash text NOT NULL,
 role text NOT NULL CHECK(role IN ('operator','approver','administrator','auditor','worker')),
 active boolean NOT NULL DEFAULT true, UNIQUE(tenant_id,id)
);
CREATE TABLE companies (
 tenant_id text NOT NULL REFERENCES tenants(id), id text NOT NULL, name text NOT NULL,
 PRIMARY KEY(tenant_id,id)
);
CREATE TABLE boards (
 tenant_id text NOT NULL REFERENCES tenants(id), id text NOT NULL, name text NOT NULL,
 PRIMARY KEY(tenant_id,id)
);
CREATE TABLE actor_scopes (
 tenant_id text NOT NULL, actor_id text NOT NULL, company_id text NOT NULL, board_id text NOT NULL,
 PRIMARY KEY(tenant_id,actor_id,company_id,board_id),
 FOREIGN KEY(tenant_id,actor_id) REFERENCES actors(tenant_id,id),
 FOREIGN KEY(tenant_id,company_id) REFERENCES companies(tenant_id,id),
 FOREIGN KEY(tenant_id,board_id) REFERENCES boards(tenant_id,id)
);
CREATE TABLE tickets (
 tenant_id text NOT NULL, id text NOT NULL, company_id text NOT NULL, board_id text NOT NULL,
 summary text NOT NULL, status text NOT NULL, version integer NOT NULL DEFAULT 1,
 updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant_id,id),
 FOREIGN KEY(tenant_id,company_id) REFERENCES companies(tenant_id,id),
 FOREIGN KEY(tenant_id,board_id) REFERENCES boards(tenant_id,id)
);
CREATE TABLE sessions (
 token_hash text PRIMARY KEY, actor_id text NOT NULL REFERENCES actors(id),
 expires_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX sessions_actor ON sessions(actor_id);
CREATE TABLE login_attempts (
 username_hash text PRIMARY KEY, failures integer NOT NULL DEFAULT 0,
 window_start timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE audit_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 tenant_id text NOT NULL, actor_id text NOT NULL,
 event text NOT NULL, correlation_id uuid NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(tenant_id,actor_id) REFERENCES actors(tenant_id,id)
);
