from fastapi import Header, HTTPException, Request

from broker.auth.obo import InvalidOBO, OBOValidator
from broker.auth.principals import AgentPrincipal, UserPrincipal
from broker.auth.spiffe import InvalidSVID, SpiffeValidator


def _strip_bearer(value: str) -> str:
    parts = value.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return value.strip()


async def authenticated_agent(
    request: Request,
    authorization: str | None = Header(default=None),
) -> AgentPrincipal:
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_svid", "reason": "missing Authorization header"},
        )
    token = _strip_bearer(authorization)
    validator: SpiffeValidator = request.app.state.spiffe_validator
    try:
        return await validator.validate(token)
    except InvalidSVID as e:
        raise HTTPException(
            status_code=401, detail={"error": "invalid_svid", "reason": str(e)}
        ) from e


async def maybe_user(
    request: Request,
    x_on_behalf_of: str | None = Header(default=None),
) -> UserPrincipal | None:
    if not x_on_behalf_of:
        return None
    validator: OBOValidator = request.app.state.obo_validator
    try:
        return await validator.validate(_strip_bearer(x_on_behalf_of))
    except InvalidOBO as e:
        raise HTTPException(
            status_code=401, detail={"error": "invalid_obo", "reason": str(e)}
        ) from e
