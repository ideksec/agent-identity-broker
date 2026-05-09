import os
import time

import jwt
import ulid
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from mock_idp.keys import SigningKey


ISSUER = os.environ.get(
    "IDP_ISSUER", "https://mock-idp.broker-system.svc.cluster.local"
)
AUDIENCE = os.environ.get(
    "IDP_AUDIENCE", "https://broker.broker-system.svc.cluster.local"
)
PRIVATE_KEY_PATH = os.environ.get("IDP_PRIVATE_KEY_PATH")
USERS_PATH = os.environ.get("IDP_USERS_PATH", "/data/users.yaml")
TOKEN_TTL_SECONDS = int(os.environ.get("IDP_TOKEN_TTL_SECONDS", "3600"))


def _load_users() -> dict[str, dict]:
    if not os.path.exists(USERS_PATH):
        # Built-in fallback so the service runs without a ConfigMap.
        return {
            "alice@acme.com": {
                "subject": "alice@acme.com",
                "email": "alice@acme.com",
                "groups": ["payments-eng", "on-call"],
            },
            "bob@acme.com": {
                "subject": "bob@acme.com",
                "email": "bob@acme.com",
                "groups": ["security-team"],
            },
            "carol@acme.com": {
                "subject": "carol@acme.com",
                "email": "carol@acme.com",
                "groups": ["interns"],
            },
        }
    with open(USERS_PATH) as f:
        data = yaml.safe_load(f) or {}
    out = {}
    for u in data.get("users", []):
        out[u["subject"]] = u
    return out


SIGNER = SigningKey.from_path_or_generate(PRIVATE_KEY_PATH)
USERS = _load_users()

app = FastAPI(title="Mock IdP", version="0.1.0")


class LoginRequest(BaseModel):
    username: str


@app.post("/login")
def login(body: LoginRequest):
    user = USERS.get(body.username)
    if user is None:
        raise HTTPException(status_code=404, detail={"error": "unknown_user"})
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": user["subject"],
        "email": user.get("email"),
        "groups": user.get("groups", []),
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
        "jti": ulid.new().str,
    }
    token = jwt.encode(
        claims,
        SIGNER.private_pem,
        algorithm="RS256",
        headers={"kid": SIGNER.kid},
    )
    return {"id_token": token, "expires_in": TOKEN_TTL_SECONDS}


@app.get("/.well-known/jwks.json")
def jwks():
    return {"keys": [SIGNER.jwk()]}


@app.get("/.well-known/openid-configuration")
def openid_configuration():
    return {
        "issuer": ISSUER,
        "jwks_uri": f"{ISSUER}/.well-known/jwks.json",
        "response_types_supported": ["id_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
