# Architecture

This is the narrative companion to `POC_SPEC.md` §3. Read the spec for the full
picture; this document captures the Phase 1 surface only.

## Components in Phase 1

| Component | Namespace | Purpose |
|-----------|-----------|---------|
| SPIRE Server + Agent + OIDC discovery | `spire` | Workload identity (JWT-SVIDs) |
| Postgres 16 | `broker-system` | State store (leases, audit, etc.) |
| Mock IdP | `broker-system` | Issues user JWTs for OBO testing |
| OPA (sidecar to broker) | `broker-system` | Policy decisions (stub default-allow in Phase 1) |
| Broker | `broker-system` | FastAPI: `/healthz`, `/readyz`, `/v1/identity` |
| Demo agent | `agents` | One-shot Job exercising `/v1/identity` |

## Trust domain & SPIFFE IDs

- Trust domain: `broker.local`
- Broker: `spiffe://broker.local/ns/broker-system/sa/broker`
- Demo agent: `spiffe://broker.local/ns/agents/sa/triage-bot`

The SPIRE Controller Manager auto-registers ClusterSPIFFEIDs derived from the
pod's namespace and ServiceAccount name (see `deploy/helm-values/spire-values.yaml`).

## Phase 1 request flow

```
demo-agent ── pyspiffe ──► SPIRE Workload API ──► JWT-SVID
demo-agent ── HTTP POST /login ─► mock-idp ──► user JWT
demo-agent ── GET /v1/identity ─► broker
                                  │
                                  ├─ validate JWT-SVID (SPIRE OIDC JWKS)
                                  ├─ validate user JWT  (mock-idp JWKS)
                                  ├─ write audit_log row
                                  └─ return { agent, user }
```

No connector or policy logic is exercised in Phase 1 — the OPA sidecar is up
and reachable but unused by `/v1/identity`. It comes online in Phase 2 when
`POST /v1/credentials` lands.

## Where to look in code

- `broker/src/broker/main.py` — FastAPI app + lifespan
- `broker/src/broker/auth/spiffe.py` — SVID validation
- `broker/src/broker/auth/obo.py` — user JWT validation
- `broker/src/broker/api/identity.py` — `/v1/identity` route
- `broker/src/broker/audit/log.py` — audit writer
- `mock-idp/src/mock_idp/main.py` — IdP service
- `sdk/src/agent_sdk/client.py` — `BrokerClient`
- `demo-agent/src/demo_agent/agent.py` — demo flow
