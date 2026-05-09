package broker

# Phase 1 stub: default allow with empty scope and short TTL. Real per-target
# policies arrive in Phase 2+.
default decision := {
    "allow": true,
    "reason": "phase1 stub: default allow",
    "policy_id": "stub.default_allow",
    "scope_granted": {},
    "max_ttl_seconds": 900,
    "requires_step_up": false,
}
