from fastapi import APIRouter, Request
from sqlalchemy import text

from broker.db.session import session_factory

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request) -> dict:
    # DB
    db_ok = False
    try:
        async with session_factory()() as s:
            await s.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # SPIRE JWKS
    jwks_ok = await request.app.state.spire_jwks.reachable()
    # Mock IdP JWKS (best-effort; OBO is optional but readyz still asserts it)
    obo_ok = await request.app.state.idp_jwks.reachable()

    ok = db_ok and jwks_ok and obo_ok
    body = {
        "status": "ok" if ok else "degraded",
        "components": {
            "db": db_ok,
            "spire_jwks": jwks_ok,
            "idp_jwks": obo_ok,
        },
    }
    if not ok:
        from fastapi.responses import JSONResponse

        return JSONResponse(body, status_code=503)
    return body
