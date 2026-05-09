"""Phase 1 integration test.

Asserts that the demo Job has succeeded and that audit rows landed.

Run order:
    make up && make seed && make demo
    pytest tests/integration/test_phase1.py -v
"""
import json
import shutil
import subprocess

import pytest

from tests.integration.conftest import run_in_postgres


pytestmark = pytest.mark.skipif(
    shutil.which("kubectl") is None,
    reason="integration tests require kubectl + a running kind cluster",
)


def test_demo_job_succeeded():
    out = subprocess.check_output(
        [
            "kubectl",
            "-n",
            "agents",
            "get",
            "job",
            "triage-bot-demo",
            "-o",
            "json",
        ]
    )
    job = json.loads(out)
    succeeded = job.get("status", {}).get("succeeded", 0)
    assert succeeded == 1, f"demo job did not succeed: {job.get('status')}"


def test_audit_rows_present():
    count = int(run_in_postgres(
        "SELECT count(*) FROM audit_log WHERE event_type = 'identity.echoed'"
    ))
    # Two calls: one without OBO, one with.
    assert count >= 2, f"expected at least 2 identity.echoed rows, got {count}"


def test_audit_includes_obo_call():
    count = int(run_in_postgres(
        "SELECT count(*) FROM audit_log "
        "WHERE event_type = 'identity.echoed' "
        "AND user_subject = 'alice@acme.com'"
    ))
    assert count >= 1, "expected at least one identity.echoed audit row with OBO user"


def test_agent_seeded():
    rows = run_in_postgres("SELECT spiffe_id FROM agents")
    assert "spiffe://broker.local/ns/agents/sa/triage-bot" in rows
