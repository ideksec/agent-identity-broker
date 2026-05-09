# Open Questions (parking lot)

Park here, don't block on them.

1. **Agent registration source of truth.** Should agents go through SPIRE
   ClusterSPIFFEIDs only, or via a broker `/admin/agents` API that writes both
   the DB row and the ClusterSPIFFEID resource?
2. **Step-up authorization.** When policy returns `requires_step_up=true`,
   what's the user-facing UX in a real deployment? OOB push? webauthn?
3. **MCP-server discovery.** How should the broker discover MCP servers per
   the MCP spec and tie them to the right policy/credential needs automatically?
4. **Federation key rotation.** Rotation strategy for the broker's own
   federation signing key? POC is manual; production needs key rollover with
   an overlap window.
5. **Chained delegation.** How to support agent → agent delegation
   (chained on-behalf-of)?
6. **Audit immutability.** Audit log rows are mutable Postgres today. Retention
   + tamper-evidence story?
