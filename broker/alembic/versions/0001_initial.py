"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("spiffe_id", sa.Text(), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text()),
        sa.Column("owner", sa.Text()),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "disabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )

    op.create_table(
        "managed_credentials",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("target_credential_id", sa.Text(), nullable=False),
        sa.Column("credential_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("credential_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("label", sa.Text()),
        sa.Column("purpose", sa.Text()),
        sa.Column("pool_key", sa.Text()),
        sa.Column(
            "rotation_schedule", sa.Text(), nullable=False, server_default="24h"
        ),
        sa.Column("last_rotated_at", sa.DateTime(timezone=True)),
        sa.Column("next_rotation_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_decision_id", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("deletion_reason", sa.Text()),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.create_index(
        "managed_creds_active_pool",
        "managed_credentials",
        ["target", "pool_key"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "managed_creds_next_rotation",
        "managed_credentials",
        ["next_rotation_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "leases",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "agent_spiffe_id",
            sa.Text(),
            sa.ForeignKey("agents.spiffe_id"),
            nullable=False,
        ),
        sa.Column("user_subject", sa.Text()),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("credential_type", sa.Text(), nullable=False),
        sa.Column(
            "scope_granted",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revocation_reason", sa.Text()),
        sa.Column("decision_id", sa.Text(), nullable=False),
        sa.Column("external_ref", sa.Text()),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "managed_credential_id",
            sa.Text(),
            sa.ForeignKey("managed_credentials.id"),
        ),
    )
    op.create_index(
        "leases_active",
        "leases",
        ["agent_spiffe_id", "expires_at"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index(
        "leases_expiring",
        "leases",
        ["expires_at"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index(
        "leases_managed_cred",
        "leases",
        ["managed_credential_id"],
        postgresql_where=sa.text("managed_credential_id IS NOT NULL"),
    )

    op.create_table(
        "audit_log",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True
        ),
        sa.Column("event_id", sa.Text(), nullable=False, unique=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("agent_spiffe_id", sa.Text()),
        sa.Column("user_subject", sa.Text()),
        sa.Column("decision_id", sa.Text()),
        sa.Column("lease_id", sa.Text()),
        sa.Column("target", sa.Text()),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.create_index(
        "audit_event_type", "audit_log", ["event_type", "occurred_at"]
    )
    op.create_index(
        "audit_agent", "audit_log", ["agent_spiffe_id", "occurred_at"]
    )
    op.create_index("audit_decision", "audit_log", ["decision_id"])

    op.create_table(
        "vault_entries",
        sa.Column("name", sa.Text(), primary_key=True),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "gateway_sessions",
        sa.Column("session_token", sa.Text(), primary_key=True),
        sa.Column(
            "lease_id", sa.Text(), sa.ForeignKey("leases.id"), nullable=False
        ),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column(
            "upstream_credential_ciphertext", sa.LargeBinary(), nullable=False
        ),
        sa.Column(
            "upstream_credential_nonce", sa.LargeBinary(), nullable=False
        ),
        sa.Column(
            "upstream_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("gateway_sessions_lease", "gateway_sessions", ["lease_id"])

    op.create_table(
        "oauth_state",
        sa.Column("state_id", sa.Text(), primary_key=True),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("agent_spiffe_id", sa.Text(), nullable=False),
        sa.Column("user_subject", sa.Text()),
        sa.Column("code_verifier", sa.Text()),
        sa.Column("redirect_uri", sa.Text()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "consumed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_table("oauth_state")
    op.drop_index("gateway_sessions_lease", table_name="gateway_sessions")
    op.drop_table("gateway_sessions")
    op.drop_table("vault_entries")
    op.drop_index("audit_decision", table_name="audit_log")
    op.drop_index("audit_agent", table_name="audit_log")
    op.drop_index("audit_event_type", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("leases_managed_cred", table_name="leases")
    op.drop_index("leases_expiring", table_name="leases")
    op.drop_index("leases_active", table_name="leases")
    op.drop_table("leases")
    op.drop_index(
        "managed_creds_next_rotation", table_name="managed_credentials"
    )
    op.drop_index(
        "managed_creds_active_pool", table_name="managed_credentials"
    )
    op.drop_table("managed_credentials")
    op.drop_table("agents")
