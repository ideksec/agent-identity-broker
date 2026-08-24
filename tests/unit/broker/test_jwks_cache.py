import time

import httpx
import jwt
import pytest

from broker.auth.jwks_cache import JWKSCache
from tests.unit.broker.test_spiffe import _gen_rsa_keypair_and_jwk


class _JWKSServer:
    """Serves a mutable JWKS document and counts fetches."""

    def __init__(self, jwks: dict):
        self.jwks = jwks
        self.fetches = 0
        self.status_code = 200

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.fetches += 1
        return httpx.Response(self.status_code, json=self.jwks)

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler))


def _jwk(kid: str) -> dict:
    _, _, jwk = _gen_rsa_keypair_and_jwk(kid=kid)
    return jwk


@pytest.mark.asyncio
async def test_get_key_by_kid():
    server = _JWKSServer({"keys": [_jwk("kid-a")]})
    cache = JWKSCache("http://jwks.test/keys", ttl=300, http=server.client())
    key = await cache.get_key("kid-a")
    assert key.key_id == "kid-a"
    assert server.fetches == 1


@pytest.mark.asyncio
async def test_fresh_cache_not_refetched():
    server = _JWKSServer({"keys": [_jwk("kid-a")]})
    cache = JWKSCache("http://jwks.test/keys", ttl=300, http=server.client())
    await cache.get_key("kid-a")
    await cache.get_key("kid-a")
    await cache.get_key("kid-a")
    assert server.fetches == 1


@pytest.mark.asyncio
async def test_expired_cache_refetched():
    server = _JWKSServer({"keys": [_jwk("kid-a")]})
    cache = JWKSCache("http://jwks.test/keys", ttl=300, http=server.client())
    await cache.get_key("kid-a")
    # Age the cache past its TTL.
    assert cache._cache is not None
    cache._cache.fetched_at = time.time() - 301
    await cache.get_key("kid-a")
    assert server.fetches == 2


@pytest.mark.asyncio
async def test_kid_miss_forces_refresh_on_rotation():
    server = _JWKSServer({"keys": [_jwk("kid-old")]})
    cache = JWKSCache("http://jwks.test/keys", ttl=300, http=server.client())
    await cache.get_key("kid-old")

    # Keys rotate server-side while the cache is still fresh.
    server.jwks = {"keys": [_jwk("kid-new")]}
    key = await cache.get_key("kid-new")
    assert key.key_id == "kid-new"
    assert server.fetches == 2


@pytest.mark.asyncio
async def test_unknown_kid_raises_after_refresh():
    server = _JWKSServer({"keys": [_jwk("kid-a")]})
    cache = JWKSCache("http://jwks.test/keys", ttl=300, http=server.client())
    with pytest.raises(jwt.InvalidKeyError):
        await cache.get_key("kid-missing")
    # One initial fetch plus one forced refresh for the miss.
    assert server.fetches == 2


@pytest.mark.asyncio
async def test_no_kid_with_single_key_falls_back():
    server = _JWKSServer({"keys": [_jwk("only-kid")]})
    cache = JWKSCache("http://jwks.test/keys", ttl=300, http=server.client())
    key = await cache.get_key(None)
    assert key.key_id == "only-kid"


@pytest.mark.asyncio
async def test_no_kid_with_multiple_keys_raises():
    server = _JWKSServer({"keys": [_jwk("kid-a"), _jwk("kid-b")]})
    cache = JWKSCache("http://jwks.test/keys", ttl=300, http=server.client())
    with pytest.raises(jwt.InvalidKeyError):
        await cache.get_key(None)


@pytest.mark.asyncio
async def test_malformed_jwk_entries_skipped():
    server = _JWKSServer({"keys": [{"kty": "garbage"}, _jwk("kid-good")]})
    cache = JWKSCache("http://jwks.test/keys", ttl=300, http=server.client())
    key = await cache.get_key("kid-good")
    assert key.key_id == "kid-good"


@pytest.mark.asyncio
async def test_reachable_true_with_keys():
    server = _JWKSServer({"keys": [_jwk("kid-a")]})
    cache = JWKSCache("http://jwks.test/keys", ttl=300, http=server.client())
    assert await cache.reachable() is True


@pytest.mark.asyncio
async def test_reachable_false_on_http_error():
    server = _JWKSServer({"keys": []})
    server.status_code = 500
    cache = JWKSCache("http://jwks.test/keys", ttl=300, http=server.client())
    assert await cache.reachable() is False


@pytest.mark.asyncio
async def test_reachable_false_with_empty_keyset():
    server = _JWKSServer({"keys": []})
    cache = JWKSCache("http://jwks.test/keys", ttl=300, http=server.client())
    assert await cache.reachable() is False
