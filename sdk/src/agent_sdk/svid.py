"""SVID source — fetches a JWT-SVID from the SPIRE Workload API.

The default backend uses the ``spiffe`` library's gRPC client. A simple
file-backed fallback is also provided for testing and for environments where
``spiffe`` is unavailable.
"""
from __future__ import annotations

import os
from typing import Protocol

DEFAULT_SOCKET = "/run/spire/agent-sockets/spire-agent.sock"


class SVIDSource(Protocol):
    async def fetch(self) -> str: ...


class WorkloadAPISVIDSource:
    """Fetch a JWT-SVID from the SPIRE Workload API for one audience."""

    def __init__(
        self,
        audience: str,
        socket_path: str = DEFAULT_SOCKET,
    ):
        self.audience = audience
        self.socket_path = socket_path
        # Lazily import spiffe so unit tests can patch / not need the dep.
        self._jwt_source = None

    def _get_source(self):
        if self._jwt_source is None:
            from spiffe import JwtSource

            # An explicit SPIFFE_ENDPOINT_SOCKET in the environment wins;
            # otherwise use the socket path this source was built with.
            socket = os.environ.get("SPIFFE_ENDPOINT_SOCKET") or (
                f"unix://{self.socket_path}"
            )
            self._jwt_source = JwtSource(socket_path=socket)
        return self._jwt_source

    async def fetch(self) -> str:
        # spiffe is sync; offload to threadpool if needed. Workload API
        # calls are already cheap, so do it inline.
        src = self._get_source()
        svid = src.fetch_svid(audience={self.audience})
        return svid.token


class StaticTokenSVIDSource:
    """Returns a pre-fetched JWT-SVID. Useful in tests."""

    def __init__(self, token: str):
        self._token = token

    async def fetch(self) -> str:
        return self._token


class FileSVIDSource:
    """Reads a JWT-SVID from a file on every call (for env-var-based testing)."""

    def __init__(self, path: str):
        self.path = path

    async def fetch(self) -> str:
        with open(self.path) as f:
            return f.read().strip()
