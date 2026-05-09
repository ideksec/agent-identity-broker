#!/usr/bin/env bash
# Insert agent rows into the broker DB so /v1/credentials lookups (Phase 2+)
# don't 403 with agent_disabled. For Phase 1, only the SPIFFE ID needs to
# exist. Idempotent — uses ON CONFLICT.
set -euo pipefail

NS="broker-system"
PG_POD="$(kubectl -n "$NS" get pod -l app=postgres -o jsonpath='{.items[0].metadata.name}')"

kubectl -n "$NS" exec -i "$PG_POD" -- psql -U broker -d broker <<'SQL'
INSERT INTO agents (spiffe_id, display_name, owner, purpose, metadata)
VALUES (
  'spiffe://broker.local/ns/agents/sa/triage-bot',
  'Triage Bot',
  'platform-team',
  'Demo agent for the broker POC',
  '{}'::jsonb
)
ON CONFLICT (spiffe_id) DO NOTHING;

SELECT spiffe_id, display_name FROM agents;
SQL
