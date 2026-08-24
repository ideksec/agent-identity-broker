import time

import httpx
import pytest

from broker.auth.obo import OBOValidator
from broker.auth.spiffe import SpiffeValidator
from broker.db.session import get_session
from broker.main import create_app
from tests.unit.broker.test_spiffe import _gen_rsa_keypair_and_jwk, _sign, _StaticJWKS

TRUST_DOMAIN = "broker.local"
AUDIENCE = "aud://broker"
IDP_ISSUER = "https://mock-idp.broker-system.svc.cluster.local"
SPIFFE_ID = f"spiffe://{TRUST_DOMAIN}/ns/agents/sa/triage-bot"


class FakeSession:
    """Stands in for an AsyncSession; records audit rows instead of persisting."""

    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        self.committed = True


@pytest.fixture
def spire_keys():
    return _gen_rsa_keypair_and_jwk(kid="spire-kid")


@pytest.fixture
def idp_keys():
    return _gen_rsa_keypair_and_jwk(kid="idp-kid")


@pytest.fixture
def fake_session():
    return FakeSession()


@pytest.fixture
def app(spire_keys, idp_keys, fake_session):
    _, _, spire_jwk = spire_keys
    _, _, idp_jwk = idp_keys

    app = create_app()
    app.state.spiffe_validator = SpiffeValidator(
        jwks=_StaticJWKS(spire_jwk),
        expected_audience=AUDIENCE,
        trust_domain=TRUST_DOMAIN,
    )
    app.state.obo_validator = OBOValidator(
        jwks=_StaticJWKS(idp_jwk),
        expected_audience=AUDIENCE,
        expected_issuer=IDP_ISSUER,
    )

    async def override_session():
        yield fake_session

    app.dependency_overrides[get_session] = override_session
    return app


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _svid(spire_keys, **overrides) -> str:
    private_pem, _, _ = spire_keys
    now = int(time.time())
    claims = {
        "iss": "https://spire.broker.local",
        "sub": SPIFFE_ID,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 300,
    }
    claims.update(overrides)
    return _sign(claims, private_pem, kid="spire-kid")


def _obo(idp_keys, **overrides) -> str:
    private_pem, _, _ = idp_keys
    now = int(time.time())
    claims = {
        "iss": IDP_ISSUER,
        "aud": AUDIENCE,
        "sub": "alice@acme.com",
        "email": "alice@acme.com",
        "groups": ["payments-eng", "on-call"],
        "iat": now,
        "exp": now + 600,
    }
    claims.update(overrides)
    return _sign(claims, private_pem, kid="idp-kid")


async def test_healthz(client):
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_identity_requires_authorization(client):
    r = await client.get("/v1/identity")
    assert r.status_code == 401
    body = r.json()
    assert body["error"] == "invalid_svid"
    assert "missing" in body["reason"]


async def test_identity_rejects_garbage_token(client):
    r = await client.get(
        "/v1/identity", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert r.status_code == 401
    assert r.json()["error"] == "invalid_svid"


async def test_identity_without_obo(client, spire_keys, fake_session):
    token = _svid(spire_keys)
    r = await client.get(
        "/v1/identity", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["agent"]["spiffe_id"] == SPIFFE_ID
    assert body["agent"]["trust_domain"] == TRUST_DOMAIN
    assert body["agent"]["expires_at"].endswith("Z")
    assert body["user"] is None

    # One audit row, committed, marked as no-OBO.
    assert len(fake_session.added) == 1
    evt = fake_session.added[0]
    assert evt.event_type == "identity.echoed"
    assert evt.agent_spiffe_id == SPIFFE_ID
    assert evt.user_subject is None
    assert evt.payload == {"with_obo": False}
    assert fake_session.committed


async def test_identity_with_obo(client, spire_keys, idp_keys, fake_session):
    r = await client.get(
        "/v1/identity",
        headers={
            "Authorization": f"Bearer {_svid(spire_keys)}",
            "X-On-Behalf-Of": _obo(idp_keys),
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["agent"]["spiffe_id"] == SPIFFE_ID
    assert body["user"]["subject"] == "alice@acme.com"
    assert body["user"]["email"] == "alice@acme.com"
    assert body["user"]["groups"] == ["payments-eng", "on-call"]

    evt = fake_session.added[0]
    assert evt.user_subject == "alice@acme.com"
    assert evt.payload == {"with_obo": True}
    assert fake_session.committed


async def test_identity_accepts_token_without_bearer_prefix(client, spire_keys):
    r = await client.get(
        "/v1/identity", headers={"Authorization": _svid(spire_keys)}
    )
    assert r.status_code == 200


async def test_identity_rejects_invalid_obo(client, spire_keys, idp_keys, fake_session):
    now = int(time.time())
    expired = _obo(idp_keys, iat=now - 1200, exp=now - 600)
    r = await client.get(
        "/v1/identity",
        headers={
            "Authorization": f"Bearer {_svid(spire_keys)}",
            "X-On-Behalf-Of": expired,
        },
    )
    assert r.status_code == 401
    assert r.json()["error"] == "invalid_obo"
    # A bad OBO must fail the whole request: nothing audited or committed.
    assert fake_session.added == []
    assert not fake_session.committed


async def test_identity_rejects_svid_outside_trust_domain(client, spire_keys):
    token = _svid(spire_keys, sub="spiffe://other.local/ns/agents/sa/rogue")
    r = await client.get(
        "/v1/identity", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 401
    assert r.json()["error"] == "invalid_svid"
