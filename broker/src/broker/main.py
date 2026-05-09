from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from broker.api import health, identity
from broker.auth.jwks_cache import JWKSCache
from broker.auth.obo import OBOValidator
from broker.auth.spiffe import SpiffeValidator
from broker.config import get_settings
from broker.db.session import dispose_engine, init_engine
from broker.logging import configure_logging, get_logger

log = get_logger("broker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info(
        "broker.starting",
        trust_domain=settings.trust_domain,
        audience=settings.audience,
        spire_jwks_url=settings.spire_jwks_url,
        mock_idp_jwks_url=settings.mock_idp_jwks_url,
    )

    init_engine(settings.db_url)

    http = httpx.AsyncClient(timeout=10)
    spire_jwks = JWKSCache(settings.spire_jwks_url, ttl=300, http=http)
    idp_jwks = JWKSCache(settings.mock_idp_jwks_url, ttl=300, http=http)

    app.state.settings = settings
    app.state.http = http
    app.state.spire_jwks = spire_jwks
    app.state.idp_jwks = idp_jwks
    app.state.spiffe_validator = SpiffeValidator(
        jwks=spire_jwks,
        expected_audience=settings.audience,
        trust_domain=settings.trust_domain,
    )
    app.state.obo_validator = OBOValidator(
        jwks=idp_jwks,
        expected_audience=settings.audience,
        expected_issuer=settings.mock_idp_issuer,
    )

    log.info("broker.started")
    try:
        yield
    finally:
        await http.aclose()
        await dispose_engine()
        log.info("broker.stopped")


def create_app() -> FastAPI:
    app = FastAPI(title="Agent Identity Broker", version="0.1.0", lifespan=lifespan)

    app.include_router(health.router)
    app.include_router(identity.router)

    @app.exception_handler(StarletteHTTPException)
    async def http_exc_handler(request, exc: StarletteHTTPException):
        # If the route raised with a dict detail, surface it directly.
        if isinstance(exc.detail, dict):
            return JSONResponse(exc.detail, status_code=exc.status_code)
        return JSONResponse(
            {"error": "http_error", "reason": str(exc.detail)},
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request, exc: RequestValidationError):
        return JSONResponse(
            {"error": "invalid_request", "reason": "schema_validation_failed",
             "details": exc.errors()},
            status_code=400,
        )

    return app


app = create_app()
