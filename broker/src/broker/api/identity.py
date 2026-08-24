from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from broker.audit.log import record as audit_record
from broker.auth.deps import authenticated_agent, maybe_user
from broker.auth.principals import AgentPrincipal, UserPrincipal
from broker.db.session import get_session

router = APIRouter()


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat().replace(
        "+00:00", "Z"
    )


@router.get("/v1/identity")
async def identity(
    agent: AgentPrincipal = Depends(authenticated_agent),
    user: UserPrincipal | None = Depends(maybe_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    body: dict = {
        "agent": {
            "spiffe_id": agent.spiffe_id,
            "trust_domain": agent.trust_domain,
            "issued_at": _iso(agent.issued_at),
            "expires_at": _iso(agent.expires_at),
        },
        "user": None
        if user is None
        else {
            "subject": user.subject,
            "email": user.email,
            "groups": user.groups,
            "expires_at": _iso(user.expires_at),
        },
    }

    await audit_record(
        session,
        "identity.echoed",
        agent_spiffe_id=agent.spiffe_id,
        user_subject=user.subject if user else None,
        payload={"with_obo": user is not None},
    )
    await session.commit()
    return body
