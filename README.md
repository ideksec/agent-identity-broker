# Agent Identity Broker (POC)

> ## ⚠️ WARNING — VIBE-CODED, NOT FOR PRODUCTION ⚠️
>
> **This repository is a vibe-coded learning/experimentation project. It has
> NOT been security-reviewed, threat-modeled, penetration-tested, or hardened
> in any meaningful way. It almost certainly contains bugs, broken assumptions,
> insecure defaults, and outright mistakes.**
>
> **DO NOT use this code, or any part of it, in a production system, in any
> environment that handles real credentials, or anywhere a failure would have
> real-world consequences.** It exists purely to learn about SPIFFE, OPA,
> credential brokering, and related concepts. Treat it as a sketch, not a
> reference implementation.

Central identity broker that issues short-lived, policy-scoped credentials to
AI agents on Kubernetes. SPIFFE workload identity in, GitHub / AWS / SaaS
access credentials out, every decision audited.

This repo is being built phase-by-phase per `POC_SPEC.md`. Current state: **Phase 1**.

## Phase 1 status

Phase 1 stands up:

- A `kind` Kubernetes cluster with namespaces `spire`, `broker-system`, `agents`.
- SPIRE Server + Agent + OIDC discovery provider (Helm).
- Postgres with the full schema migrated.
- Mock IdP for OBO user JWTs.
- OPA sidecar with a stub default-allow policy.
- The broker FastAPI service exposing:
  - `GET /healthz`, `GET /readyz`
  - `GET /v1/identity` — validates SVID and (optional) OBO user JWT, echoes both.
- Audit log writes for identity calls.
- Agent SDK `BrokerClient.get_identity()` that fetches a JWT-SVID from the SPIRE
  Workload API and calls the broker.
- A demo-agent `Job` that calls `/v1/identity` once without OBO and once with.

Out of Phase 1: connectors, real OPA policies, gateway, lifecycle workers.

## Quick start

```bash
cp .env.example .env
make up        # kind create + namespaces + SPIRE + postgres + mock-idp + opa + broker
make seed      # generate K8s secrets, run alembic migration, seed agents
make demo      # run demo-agent Job, tail logs
```

## Architecture

See `docs/ARCHITECTURE.md`. The full spec lives in `POC_SPEC.md`.

## Phases

1. **SPIRE + broker skeleton** ← current
2. GitHub connector + lifecycle
3. AWS STS via OIDC federation
4. Blended identity + mock connectors
5. MCP Gateway + revocation + rotation (Pattern B)
6. Managed long-lived credentials (Pattern C)

See `docs/PHASE-CHECKLIST.md` for acceptance criteria per phase.

## Running tests

```bash
# Unit tests run anywhere:
cd broker && pip install -e . && pytest -v ../tests/unit/broker

# Integration tests assume the cluster is up:
make up && make seed
pytest -v tests/integration/test_phase1.py
```

## Layout

See `POC_SPEC.md` §5 for the full file tree. Key pieces of Phase 1:

- `broker/` — FastAPI service (Python 3.12)
- `mock-idp/` — issues user JWTs for OBO testing
- `sdk/` — `agent_sdk.BrokerClient`
- `demo-agent/` — Job that exercises the broker
- `deploy/k8s/` — manifests
- `deploy/helm-values/spire-values.yaml` — SPIRE Helm values
- `policy/` — OPA policies + agent/user data (stub policy in Phase 1)
- `Makefile` — `up`, `down`, `seed`, `demo`, dev loops
