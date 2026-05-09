import jwt

from broker.auth.jwks_cache import JWKSCache
from broker.auth.principals import UserPrincipal


class InvalidOBO(Exception):
    pass


class OBOValidator:
    """Validate user JWTs presented in X-On-Behalf-Of."""

    def __init__(
        self,
        jwks: JWKSCache,
        expected_audience: str,
        expected_issuer: str | None = None,
        algorithms: tuple[str, ...] = ("RS256",),
    ) -> None:
        self.jwks = jwks
        self.expected_audience = expected_audience
        self.expected_issuer = expected_issuer
        self.algorithms = list(algorithms)

    async def validate(self, token: str) -> UserPrincipal:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as e:
            raise InvalidOBO(f"unparseable token: {e}") from e

        kid = header.get("kid")
        try:
            jwk = await self.jwks.get_key(kid)
        except Exception as e:
            raise InvalidOBO(f"jwks lookup failed: {e}") from e

        decode_kwargs: dict = {
            "key": jwk.key,
            "algorithms": self.algorithms,
            "audience": self.expected_audience,
            "options": {"require": ["sub", "exp", "aud", "iat"]},
        }
        if self.expected_issuer:
            decode_kwargs["issuer"] = self.expected_issuer

        try:
            claims = jwt.decode(token, **decode_kwargs)
        except jwt.PyJWTError as e:
            raise InvalidOBO(f"signature/claims invalid: {e}") from e

        return UserPrincipal(
            subject=claims["sub"],
            email=claims.get("email"),
            groups=list(claims.get("groups", []) or []),
            issued_at=int(claims["iat"]),
            expires_at=int(claims["exp"]),
            raw_claims=claims,
        )
