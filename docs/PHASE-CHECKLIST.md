# Phase Acceptance Checklist

Pulled from `POC_SPEC.md` §20. Tick boxes as phases are completed.

## Phase 1 — SPIRE + broker skeleton

- [ ] `make up` completes without error
- [ ] All pods Running in namespaces `spire`, `broker-system`, `agents`
- [ ] `make demo` Job exits 0
- [ ] `/v1/identity` returns the demo agent's SPIFFE ID
- [ ] With `X-On-Behalf-Of`, `/v1/identity` includes `alice@acme.com` and groups
- [ ] `audit_log` rows exist for the identity calls

## Phase 2 — GitHub connector + lifecycle

- [ ] All Phase 1 criteria still pass
- [ ] Demo agent reads README from real `acme-test/demo-repo`
- [ ] `leases` row with `credential_type="github_installation_token"`
- [ ] `audit_log` shows `credential.requested`, `policy.evaluated`, `credential.issued`
- [ ] Negative test (out-of-entitlement scope) → 403 + `credential.denied`

## Phase 3 — AWS STS via OIDC federation

- [ ] Demo agent calls `s3 list-buckets`
- [ ] `leases` row with `credential_type="aws_sts_session"`
- [ ] Broker `/.well-known/jwks.json` reachable from public ngrok URL
- [ ] CloudTrail shows `AssumeRoleWithWebIdentity`

## Phase 4 — Blended identity + mock connectors

- [ ] Demo agent succeeds against all 5 targets
- [ ] Blended denial: alice blocked from a repo only bob can access
- [ ] Disabling agent → subsequent requests fail `agent_disabled`

## Phase 5 — MCP Gateway + revocation + rotation (Pattern B)

- [ ] Atlassian + oauth-generic targets work via gateway
- [ ] `gateway_sessions` rows exist; deletion / revoke marks them
- [ ] Revoked gateway-mode lease → next gateway call returns 401
- [ ] Rotation worker rotates Atlassian token without lease ID change

## Phase 6 — Managed long-lived credentials (Pattern C)

- [ ] Legacy SaaS demo step succeeds
- [ ] `managed_credentials` row created and decryptable
- [ ] Manual rotate → target_credential_id changes; demo call survives
- [ ] Manual delete → cascading lease/session revokes; next demo call 401
- [ ] `scripts/check-drift.sh` reports zero drift
- [ ] Simulated rotation failure → `managed_credential.rotation_failed` audit;
      next tick succeeds
