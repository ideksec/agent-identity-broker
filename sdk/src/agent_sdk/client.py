from __future__ import annotations

import httpx

from agent_sdk.exceptions import BrokerError, InvalidSVID, PolicyDenied
from agent_sdk.svid import SVIDSource, WorkloadAPISVIDSource


class BrokerClient:
    """Thin async client over the broker HTTP API.

    The client fetches a JWT-SVID per-call from its SVIDSource. For Phase 1
    only ``get_identity()`` is implemented; ``get_credential()`` lands in
    Phase 2.
    """

    def __init__(
        self,
        broker_url: str,
        *,
        svid_source: SVIDSource | None = None,
        audience: str | None = None,
        verify_tls: bool | str = True,
        timeout: float = 10.0,
    ):
        self.broker_url = broker_url.rstrip("/")
        if svid_source is None:
            aud = audience or self.broker_url
            svid_source = WorkloadAPISVIDSource(audience=aud)
        self.svid_source = svid_source
        self.http = httpx.AsyncClient(timeout=timeout, verify=verify_tls)

    async def aclose(self) -> None:
        await self.http.aclose()

    async def __aenter__(self) -> BrokerClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def _headers(self, on_behalf_of: str | None) -> dict[str, str]:
        svid = await self.svid_source.fetch()
        h = {"Authorization": f"Bearer {svid}"}
        if on_behalf_of:
            h["X-On-Behalf-Of"] = on_behalf_of
        return h

    def _raise_for(self, resp: httpx.Response) -> None:
        try:
            body = resp.json()
        except Exception:
            body = {"error": "non_json", "reason": resp.text[:500]}
        if resp.status_code == 401:
            raise InvalidSVID(body.get("reason") or "unauthorized")
        if resp.status_code == 403:
            if body.get("error") == "policy_denied":
                raise PolicyDenied(body)
            raise BrokerError(body.get("reason") or "forbidden")
        raise BrokerError(
            f"broker returned {resp.status_code}: {body.get('reason') or body}"
        )

    async def get_identity(self, *, on_behalf_of: str | None = None) -> dict:
        """Return the broker's view of who is calling (and any OBO user)."""
        headers = await self._headers(on_behalf_of)
        r = await self.http.get(f"{self.broker_url}/v1/identity", headers=headers)
        if r.status_code != 200:
            self._raise_for(r)
        return r.json()
