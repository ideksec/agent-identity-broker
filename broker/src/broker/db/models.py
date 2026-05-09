from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"

    spiffe_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    disabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class Lease(Base):
    __tablename__ = "leases"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    agent_spiffe_id: Mapped[str] = mapped_column(
        Text, ForeignKey("agents.spiffe_id"), nullable=False
    )
    user_subject: Mapped[str | None] = mapped_column(Text)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    credential_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_granted: Mapped[dict] = mapped_column(JSONB, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(Text)
    decision_id: Mapped[str] = mapped_column(Text, nullable=False)
    external_ref: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
    managed_credential_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("managed_credentials.id")
    )

    __table_args__ = (
        Index(
            "leases_active",
            "agent_spiffe_id",
            "expires_at",
            postgresql_where="revoked_at IS NULL",
        ),
        Index(
            "leases_expiring",
            "expires_at",
            postgresql_where="revoked_at IS NULL",
        ),
        Index(
            "leases_managed_cred",
            "managed_credential_id",
            postgresql_where="managed_credential_id IS NOT NULL",
        ),
    )


class AuditEvent(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    agent_spiffe_id: Mapped[str | None] = mapped_column(Text)
    user_subject: Mapped[str | None] = mapped_column(Text)
    decision_id: Mapped[str | None] = mapped_column(Text)
    lease_id: Mapped[str | None] = mapped_column(Text)
    target: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    __table_args__ = (
        Index("audit_event_type", "event_type", "occurred_at"),
        Index("audit_agent", "agent_spiffe_id", "occurred_at"),
        Index("audit_decision", "decision_id"),
    )


class ManagedCredential(Base):
    __tablename__ = "managed_credentials"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    target_credential_id: Mapped[str] = mapped_column(Text, nullable=False)
    credential_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    credential_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    label: Mapped[str | None] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(Text)
    pool_key: Mapped[str | None] = mapped_column(Text)
    rotation_schedule: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="24h"
    )
    last_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_rotation_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_by_decision_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_reason: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    __table_args__ = (
        Index(
            "managed_creds_active_pool",
            "target",
            "pool_key",
            postgresql_where="deleted_at IS NULL",
        ),
        Index(
            "managed_creds_next_rotation",
            "next_rotation_at",
            postgresql_where="deleted_at IS NULL",
        ),
    )


class VaultEntry(Base):
    __tablename__ = "vault_entries"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class GatewaySession(Base):
    __tablename__ = "gateway_sessions"

    session_token: Mapped[str] = mapped_column(Text, primary_key=True)
    lease_id: Mapped[str] = mapped_column(
        Text, ForeignKey("leases.id"), nullable=False
    )
    target: Mapped[str] = mapped_column(Text, nullable=False)
    upstream_credential_ciphertext: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False
    )
    upstream_credential_nonce: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False
    )
    upstream_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("gateway_sessions_lease", "lease_id"),)


class OAuthState(Base):
    __tablename__ = "oauth_state"

    state_id: Mapped[str] = mapped_column(Text, primary_key=True)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    agent_spiffe_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_subject: Mapped[str | None] = mapped_column(Text)
    code_verifier: Mapped[str | None] = mapped_column(Text)
    redirect_uri: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
