from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentPrincipal:
    spiffe_id: str
    issued_at: int
    expires_at: int
    raw_claims: dict = field(default_factory=dict)

    @property
    def trust_domain(self) -> str:
        # spiffe://<trust-domain>/<path>
        rest = self.spiffe_id[len("spiffe://"):]
        return rest.split("/", 1)[0]


@dataclass(frozen=True)
class UserPrincipal:
    subject: str
    email: str | None
    groups: list[str]
    issued_at: int
    expires_at: int
    raw_claims: dict = field(default_factory=dict)
