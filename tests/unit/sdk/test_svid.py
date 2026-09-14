from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent_sdk.svid import (
    FileSVIDSource,
    StaticTokenSVIDSource,
    WorkloadAPISVIDSource,
)


def _fake_jwt_source(token: str) -> MagicMock:
    """A stand-in for spiffe.JwtSource whose fetch_svid returns `token`."""
    inst = MagicMock()
    inst.fetch_svid.return_value = SimpleNamespace(token=token)
    cls = MagicMock(return_value=inst)
    return cls


async def test_workload_api_source_fetches_token_for_audience(monkeypatch):
    monkeypatch.delenv("SPIFFE_ENDPOINT_SOCKET", raising=False)
    fake = _fake_jwt_source("svid-token")

    with patch("spiffe.JwtSource", fake):
        src = WorkloadAPISVIDSource(audience="https://broker", socket_path="/run/x.sock")
        assert await src.fetch() == "svid-token"

    fake.assert_called_once_with(socket_path="unix:///run/x.sock")
    fake.return_value.fetch_svid.assert_called_once_with(audience={"https://broker"})


async def test_workload_api_source_reuses_jwt_source(monkeypatch):
    monkeypatch.delenv("SPIFFE_ENDPOINT_SOCKET", raising=False)
    fake = _fake_jwt_source("t")

    with patch("spiffe.JwtSource", fake):
        src = WorkloadAPISVIDSource(audience="a")
        await src.fetch()
        await src.fetch()

    assert fake.call_count == 1
    assert fake.return_value.fetch_svid.call_count == 2


async def test_workload_api_source_env_socket_takes_precedence(monkeypatch):
    monkeypatch.setenv("SPIFFE_ENDPOINT_SOCKET", "unix:///from/env.sock")
    fake = _fake_jwt_source("t")

    with patch("spiffe.JwtSource", fake):
        await WorkloadAPISVIDSource(audience="a", socket_path="/ignored.sock").fetch()

    fake.assert_called_once_with(socket_path="unix:///from/env.sock")


async def test_static_token_source():
    assert await StaticTokenSVIDSource("abc").fetch() == "abc"


async def test_file_source_strips_whitespace(tmp_path):
    p = tmp_path / "svid"
    p.write_text("  file-token\n")
    assert await FileSVIDSource(str(p)).fetch() == "file-token"


def test_workload_api_source_defaults():
    src = WorkloadAPISVIDSource(audience="a")
    assert src.socket_path == "/run/spire/agent-sockets/spire-agent.sock"
    assert src.audience == "a"
    assert src._jwt_source is None


@pytest.mark.parametrize("token", ["x", "y"])
async def test_static_token_source_parametrized(token):
    assert await StaticTokenSVIDSource(token).fetch() == token
