CREATE TABLE assistant_runs (
 id uuid PRIMARY KEY, tenant_id text NOT NULL, actor_id text NOT NULL,
 request_hash text NOT NULL, skill text NOT NULL, ticket_id text, operation_id uuid,
 provider text NOT NULL, model text, prompt_version text NOT NULL, schema_version text NOT NULL,
 skill_version text NOT NULL, status text NOT NULL, inference_active boolean NOT NULL DEFAULT true,
 input_hash text, source_hash text, result jsonb, error_code text,
 proposal_id uuid, latency_ms integer, usage jsonb, cost_usd numeric,
 created_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 FOREIGN KEY(tenant_id,actor_id) REFERENCES actors(tenant_id,id),
 FOREIGN KEY(tenant_id,ticket_id) REFERENCES tickets(tenant_id,id),
 FOREIGN KEY(tenant_id,proposal_id) REFERENCES proposals(tenant_id,id),
 CHECK(status IN ('running','completed','abstained','rejected','failed','cancelled'))
);
CREATE INDEX assistant_active_runs ON assistant_runs(tenant_id,status);
CREATE TABLE skill_grants (
 tenant_id text NOT NULL, actor_id text NOT NULL, skill text NOT NULL,
 PRIMARY KEY(tenant_id,actor_id,skill),
 FOREIGN KEY(tenant_id,actor_id) REFERENCES actors(tenant_id,id)
);
