from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Broker configuration. All values come from env (BROKER_* prefix)."""

    model_config = SettingsConfigDict(env_prefix="BROKER_", extra="ignore")

    db_url: str = Field(
        default="postgresql+asyncpg://broker:broker@postgres:5432/broker"
    )

    # Policy
    opa_url: str = Field(default="http://localhost:8181")

    # SPIFFE / SPIRE
    spire_jwks_url: str = Field(
        default="http://spire-spiffe-oidc-discovery-provider.spire.svc/keys"
    )
    spire_issuer: str = Field(default="https://spire.broker.local")
    trust_domain: str = Field(default="broker.local")
    audience: str = Field(default="https://broker.broker-system.svc.cluster.local")

    # Mock IdP (for OBO)
    mock_idp_jwks_url: str = Field(
        default="http://mock-idp.broker-system.svc:8080/.well-known/jwks.json"
    )
    mock_idp_issuer: str = Field(
        default="https://mock-idp.broker-system.svc.cluster.local"
    )

    # Vault key (32 bytes, base64). Required at runtime; default empty so unit
    # tests can construct settings without it.
    vault_key: str = Field(default="")

    # Federation (Phase 3+)
    federation_issuer: str = Field(default="")
    federation_key_path: str = Field(default="")

    # Gateway (Phase 5+)
    gateway_public_url: str = Field(
        default="https://gateway.broker-system.svc.cluster.local"
    )

    # GitHub (Phase 2+)
    github_app_id: str = Field(default="")
    github_private_key_path: str = Field(default="")

    # AWS (Phase 3+)
    aws_region: str = Field(default="us-east-1")

    # Mock connectors base (Phase 4+)
    mock_connectors_base: str = Field(
        default="http://mock-connectors.broker-system.svc:8080"
    )

    log_level: str = Field(default="INFO")


def get_settings() -> Settings:
    return Settings()
