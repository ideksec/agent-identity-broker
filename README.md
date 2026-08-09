# Agent Identity Broker

![Status: experimental](https://img.shields.io/badge/status-experimental-orange)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![secret-scan](https://github.com/ideksec/agent-identity-broker/actions/workflows/secret-scan.yml/badge.svg)](https://github.com/ideksec/agent-identity-broker/actions/workflows/secret-scan.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)

> **Experimental proof of concept — not production software.**
>
> This repository explores identity and authorization patterns for autonomous
> and user-delegated AI agents, including SPIFFE workload identity, short-lived
> credential brokering, policy-based authorization, and auditable delegation.
> It is intentionally experimental and has not been production-hardened or
> independently security-reviewed.

A central identity broker that issues short-lived, policy-scoped credentials to
AI agents on Kubernetes: SPIFFE workload identity in, GitHub / AWS / SaaS access
credentials out, every decision authorized against policy and audited.

This repo is being built phase-by-phase (see [Phases](#phases) below). Current state: **Phase 1**.

## Why I built this

As AI agents start taking real actions in real systems, they need to
authenticate to services like GitHub, AWS, and SaaS APIs. The default today is
to hand an agent a long-lived, broadly-scoped API key in an environment
variable — a credential that never expires, is over-privileged, can't be
attributed to a specific run, and gives no way to distinguish an agent acting
on its own from one acting on behalf of a user.

This project explores a different model: give each agent a strong,
cryptographically-verifiable *workload* identity (SPIFFE/SPIRE), and have a
central broker exchange that identity — plus optional on-behalf-of user
context — for **short-lived, narrowly-scoped, policy-checked** credentials to
downstream systems, with every decision recorded in an audit log. It's a
hands-on way for me to work through the identity primitives (SPIFFE, OIDC
federation, OPA) that I think agentic systems will increasingly depend on.

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

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the Phase 1 component
layout, trust domain, and request flow.

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

Key pieces of Phase 1:

- `broker/` — FastAPI service (Python 3.12)
- `mock-idp/` — issues user JWTs for OBO testing
- `sdk/` — `agent_sdk.BrokerClient`
- `demo-agent/` — Job that exercises the broker
- `deploy/k8s/` — manifests
- `deploy/helm-values/spire-values.yaml` — SPIRE Helm values
- `policy/` — OPA policies + agent/user data (stub policy in Phase 1)
- `Makefile` — `up`, `down`, `seed`, `demo`, dev loops

## Security note

No credentials are committed to this repository. All secrets (Postgres
password, vault key, mock-IdP and broker signing keys) are generated at
`make seed` time as Kubernetes Secrets; `.env` and key material are
git-ignored, and `.env.example` contains placeholders only. The full commit
history has been scanned with [gitleaks](https://github.com/gitleaks/gitleaks).

That said — see the disclaimer at the top. This is an experiment, not a
security-reviewed system. Please don't run it against real credentials.

## License

Licensed under the [Apache License 2.0](LICENSE).
