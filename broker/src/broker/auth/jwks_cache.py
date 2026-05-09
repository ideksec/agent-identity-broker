import asyncio
import time
from dataclasses import dataclass

import httpx
import jwt
from jwt import PyJWK


@dataclass
class CachedJWKS:
    keys_by_kid: dict[str, PyJWK]
    fetched_at: float


class JWKSCache:
    """Fetch and cache a JWKS document. TTL in seconds.

    Resilient to JWKS rotation: a kid miss triggers a forced refresh once.
    """

    def __init__(self, jwks_url: str, ttl: int = 300, http: httpx.AsyncClient | None = None):
        self.jwks_url = jwks_url
        self.ttl = ttl
        self._cache: CachedJWKS | None = None
        self._lock = asyncio.Lock()
        self._http = http

    def _is_fresh(self) -> bool:
        return self._cache is not None and (time.time() - self._cache.fetched_at) < self.ttl

    async def _fetch(self) -> CachedJWKS:
        client = self._http or httpx.AsyncClient(timeout=5)
        try:
            r = await client.get(self.jwks_url)
            r.raise_for_status()
            data = r.json()
        finally:
            if self._http is None:
                await client.aclose()
        keys: dict[str, PyJWK] = {}
        for k in data.get("keys", []):
            try:
                pyjwk = PyJWK(k)
            except Exception:
                continue
            kid = k.get("kid") or pyjwk.key_id or ""
            keys[kid] = pyjwk
        return CachedJWKS(keys_by_kid=keys, fetched_at=time.time())

    async def get_key(self, kid: str | None) -> PyJWK:
        if not self._is_fresh():
            async with self._lock:
                if not self._is_fresh():
                    self._cache = await self._fetch()
        assert self._cache is not None
        if kid and kid in self._cache.keys_by_kid:
            return self._cache.keys_by_kid[kid]
        # kid miss — force a one-shot refresh in case keys rotated.
        async with self._lock:
            self._cache = await self._fetch()
        if kid and kid in self._cache.keys_by_kid:
            return self._cache.keys_by_kid[kid]
        # No kid in token — if there's only one key, use it.
        if not kid and len(self._cache.keys_by_kid) == 1:
            return next(iter(self._cache.keys_by_kid.values()))
        raise jwt.InvalidKeyError(f"no JWK matched kid={kid!r}")

    async def reachable(self) -> bool:
        try:
            if not self._is_fresh():
                async with self._lock:
                    self._cache = await self._fetch()
            return self._cache is not None and len(self._cache.keys_by_kid) > 0
        except Exception:
            return False
