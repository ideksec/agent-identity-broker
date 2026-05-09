"""Phase 1 demo agent.

Calls the broker /v1/identity endpoint twice — once without OBO and once
with a user JWT obtained from the mock IdP — and asserts the broker
correctly identifies the workload and (when present) the user.

Exits non-zero on any assertion failure.
"""
from __future__ import annotations

import asyncio
import os
import sys

import httpx
import structlog

from agent_sdk import BrokerClient


def _logger() -> structlog.stdlib.BoundLogger:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )
    return structlog.get_logger("demo-agent")


log = _logger()


async def _fetch_user_jwt(idp_url: str, username: str) -> str:
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.post(
            f"{idp_url.rstrip('/')}/login", json={"username": username}
        )
        r.raise_for_status()
        return r.json()["id_token"]


async def main() -> int:
    broker_url = os.environ["BROKER_URL"]
    expected_spiffe_id = os.environ["EXPECTED_SPIFFE_ID"]
    idp_url = os.environ.get(
        "MOCK_IDP_URL", "http://mock-idp.broker-system.svc:8080"
    )
    user = os.environ.get("OBO_USER", "alice@acme.com")
    audience = os.environ.get("BROKER_AUDIENCE", broker_url)

    log.info(
        "demo.start",
        broker_url=broker_url,
        expected_spiffe_id=expected_spiffe_id,
        idp_url=idp_url,
        obo_user=user,
    )

    async with BrokerClient(
        broker_url, audience=audience, verify_tls=False
    ) as broker:
        # 1. /v1/identity without OBO
        ident = await broker.get_identity()
        log.info("identity.no_obo", body=ident)
        assert (
            ident["agent"]["spiffe_id"] == expected_spiffe_id
        ), f"unexpected SPIFFE ID: {ident['agent']['spiffe_id']!r}"
        assert ident["user"] is None, "expected no user when OBO absent"

        # 2. fetch a user JWT from the mock IdP
        user_jwt = await _fetch_user_jwt(idp_url, user)

        # 3. /v1/identity with OBO
        ident_obo = await broker.get_identity(on_behalf_of=user_jwt)
        log.info("identity.with_obo", body=ident_obo)
        assert (
            ident_obo["agent"]["spiffe_id"] == expected_spiffe_id
        ), "agent SPIFFE ID should be unchanged when OBO is present"
        assert ident_obo["user"] is not None, "expected user when OBO is present"
        assert (
            ident_obo["user"]["subject"] == user
        ), f"unexpected user subject: {ident_obo['user']['subject']!r}"
        assert (
            "groups" in ident_obo["user"]
            and isinstance(ident_obo["user"]["groups"], list)
        ), "user groups missing"

    log.info("demo.complete")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except AssertionError as e:
        log.error("demo.failed", reason=str(e))
        sys.exit(2)
    except Exception as e:
        log.error("demo.crashed", error_type=type(e).__name__, error=str(e))
        sys.exit(1)
