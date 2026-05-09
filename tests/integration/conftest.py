"""Integration test fixtures.

These tests assume the kind cluster is already up (`make up && make seed`)
and use kubectl to run probes inside the cluster. They do NOT spawn local
processes.
"""
import shutil
import subprocess

import pytest


def _kubectl_available() -> bool:
    return shutil.which("kubectl") is not None


@pytest.fixture(scope="session")
def kubectl():
    if not _kubectl_available():
        pytest.skip("kubectl not on PATH; integration tests need a kind cluster")
    return shutil.which("kubectl")


@pytest.fixture(scope="session")
def kind_context() -> str:
    return "kind-broker"


def run_in_postgres(sql: str) -> str:
    """Execute SQL in the postgres pod and return stdout."""
    pod = subprocess.check_output(
        [
            "kubectl",
            "-n",
            "broker-system",
            "get",
            "pod",
            "-l",
            "app=postgres",
            "-o",
            "jsonpath={.items[0].metadata.name}",
        ]
    ).decode()
    out = subprocess.check_output(
        [
            "kubectl",
            "-n",
            "broker-system",
            "exec",
            "-i",
            pod,
            "--",
            "psql",
            "-U",
            "broker",
            "-d",
            "broker",
            "-At",
            "-c",
            sql,
        ]
    ).decode()
    return out.strip()
