import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from broker.auth.jwks_cache import JWKSCache
from broker.auth.spiffe import InvalidSVID, SpiffeValidator


def _gen_rsa_keypair_and_jwk(kid: str = "test-kid"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(
        key.public_key(), as_dict=True
    )
    jwk["kid"] = kid
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"
    return private_pem, public_pem, jwk


class _StaticJWKS(JWKSCache):
    def __init__(self, jwk_dict: dict):
        from jwt import PyJWK

        self.jwks_url = "test://"
        self.ttl = 300
        kid = jwk_dict.get("kid", "")
        self._cache = type("C", (), {})()
        self._cache.keys_by_kid = {kid: PyJWK(jwk_dict)}
        self._cache.fetched_at = time.time()
        import asyncio

        self._lock = asyncio.Lock()
        self._http = None

    async def _fetch(self):
        return self._cache


def _sign(claims: dict, private_pem: bytes, kid: str) -> str:
    return jwt.encode(
        claims, private_pem, algorithm="RS256", headers={"kid": kid}
    )


@pytest.mark.asyncio
async def test_valid_svid():
    private_pem, _public_pem, jwk = _gen_rsa_keypair_and_jwk()
    jwks = _StaticJWKS(jwk)
    v = SpiffeValidator(jwks, expected_audience="aud://broker", trust_domain="broker.local")
    now = int(time.time())
    token = _sign(
        {
            "iss": "https://spire.broker.local",
            "sub": "spiffe://broker.local/ns/agents/sa/triage-bot",
            "aud": "aud://broker",
            "iat": now,
            "exp": now + 300,
        },
        private_pem,
        kid="test-kid",
    )
    p = await v.validate(token)
    assert p.spiffe_id == "spiffe://broker.local/ns/agents/sa/triage-bot"
    assert p.trust_domain == "broker.local"


@pytest.mark.asyncio
async def test_wrong_trust_domain_rejected():
    private_pem, _public_pem, jwk = _gen_rsa_keypair_and_jwk()
    jwks = _StaticJWKS(jwk)
    v = SpiffeValidator(jwks, expected_audience="aud://broker", trust_domain="broker.local")
    now = int(time.time())
    token = _sign(
        {
            "iss": "x",
            "sub": "spiffe://other.local/ns/agents/sa/x",
            "aud": "aud://broker",
            "iat": now,
            "exp": now + 300,
        },
        private_pem,
        kid="test-kid",
    )
    with pytest.raises(InvalidSVID):
        await v.validate(token)


@pytest.mark.asyncio
async def test_expired_rejected():
    private_pem, _public_pem, jwk = _gen_rsa_keypair_and_jwk()
    jwks = _StaticJWKS(jwk)
    v = SpiffeValidator(jwks, expected_audience="aud://broker", trust_domain="broker.local")
    now = int(time.time())
    token = _sign(
        {
            "iss": "x",
            "sub": "spiffe://broker.local/ns/agents/sa/x",
            "aud": "aud://broker",
            "iat": now - 600,
            "exp": now - 300,
        },
        private_pem,
        kid="test-kid",
    )
    with pytest.raises(InvalidSVID):
        await v.validate(token)


@pytest.mark.asyncio
async def test_wrong_audience_rejected():
    private_pem, _public_pem, jwk = _gen_rsa_keypair_and_jwk()
    jwks = _StaticJWKS(jwk)
    v = SpiffeValidator(jwks, expected_audience="aud://broker", trust_domain="broker.local")
    now = int(time.time())
    token = _sign(
        {
            "iss": "x",
            "sub": "spiffe://broker.local/ns/agents/sa/x",
            "aud": "aud://other",
            "iat": now,
            "exp": now + 300,
        },
        private_pem,
        kid="test-kid",
    )
    with pytest.raises(InvalidSVID):
        await v.validate(token)
