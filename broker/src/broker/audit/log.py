from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from broker.db.models import AuditEvent
from broker.ids import event_id
from broker.logging import get_logger

log = get_logger("audit")


async def record(
    session: AsyncSession,
    event_type: str,
    *,
    agent_spiffe_id: str | None = None,
    user_subject: str | None = None,
    decision_id: str | None = None,
    lease_id: str | None = None,
    target: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    """Persist an audit row and emit a structured log line.

    Caller is responsible for committing the session.
    """
    evt = AuditEvent(
        event_id=event_id(),
        event_type=event_type,
        agent_spiffe_id=agent_spiffe_id,
        user_subject=user_subject,
        decision_id=decision_id,
        lease_id=lease_id,
        target=target,
        payload=payload or {},
    )
    session.add(evt)
    await session.flush()

    log.info(
        "audit",
        event_id=evt.event_id,
        event_type=event_type,
        agent_spiffe_id=agent_spiffe_id,
        user_subject=user_subject,
        decision_id=decision_id,
        lease_id=lease_id,
        target=target,
        payload=payload or {},
    )
    return evt
