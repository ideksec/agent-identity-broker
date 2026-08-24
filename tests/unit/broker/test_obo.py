import time

import pytest

from broker.auth.obo import InvalidOBO, OBOValidator
from tests.unit.broker.test_spiffe import _gen_rsa_keypair_and_jwk, _sign, _StaticJWKS


@pytest.mark.asyncio
async def test_valid_obo():
    private_pem, _, jwk = _gen_rsa_keypair_and_jwk(kid="idp-kid")
    jwks = _StaticJWKS(jwk)
    v = OBOValidator(
        jwks,
        expected_audience="aud://broker",
        expected_issuer="https://mock-idp.broker-system.svc.cluster.local",
    )
    now = int(time.time())
    token = _sign(
        {
            "iss": "https://mock-idp.broker-system.svc.cluster.local",
            "aud": "aud://broker",
            "sub": "alice@acme.com",
            "email": "alice@acme.com",
            "groups": ["payments-eng", "on-call"],
            "iat": now,
            "exp": now + 600,
        },
        private_pem,
        kid="idp-kid",
    )
    user = await v.validate(token)
    assert user.subject == "alice@acme.com"
    assert "payments-eng" in user.groups


@pytest.mark.asyncio
async def test_obo_wrong_issuer():
    private_pem, _, jwk = _gen_rsa_keypair_and_jwk(kid="idp-kid")
    jwks = _StaticJWKS(jwk)
    v = OBOValidator(
        jwks,
        expected_audience="aud://broker",
        expected_issuer="https://mock-idp.broker-system.svc.cluster.local",
    )
    now = int(time.time())
    token = _sign(
        {
            "iss": "https://wrong-issuer",
            "aud": "aud://broker",
            "sub": "alice@acme.com",
            "iat": now,
            "exp": now + 600,
        },
        private_pem,
        kid="idp-kid",
    )
    with pytest.raises(InvalidOBO):
        await v.validate(token)
