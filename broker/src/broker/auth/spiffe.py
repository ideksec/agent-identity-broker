import jwt

from broker.auth.jwks_cache import JWKSCache
from broker.auth.principals import AgentPrincipal


class InvalidSVID(Exception):
    pass


class SpiffeValidator:
    """Validate SPIFFE JWT-SVIDs against SPIRE's OIDC JWKS.

    A valid JWT-SVID must:
      - have signature valid against a key in the SPIRE JWKS
      - have ``aud`` containing the broker's expected audience
      - be unexpired
      - have ``sub`` starting with ``spiffe://<trust_domain>/``
    """

    def __init__(
        self,
        jwks: JWKSCache,
        expected_audience: str,
        trust_domain: str,
        algorithms: tuple[str, ...] = ("RS256", "ES256", "ES384"),
    ) -> None:
        self.jwks = jwks
        self.expected_audience = expected_audience
        self.trust_domain = trust_domain
        self.algorithms = list(algorithms)

    async def validate(self, token: str) -> AgentPrincipal:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as e:
            raise InvalidSVID(f"unparseable token: {e}") from e

        kid = header.get("kid")
        try:
            jwk = await self.jwks.get_key(kid)
        except Exception as e:
            raise InvalidSVID(f"jwks lookup failed: {e}") from e

        try:
            claims = jwt.decode(
                token,
                key=jwk.key,
                algorithms=self.algorithms,
                audience=self.expected_audience,
                options={"require": ["sub", "exp", "aud", "iat"]},
            )
        except jwt.PyJWTError as e:
            raise InvalidSVID(f"signature/claims invalid: {e}") from e

        sub = claims.get("sub", "")
        prefix = f"spiffe://{self.trust_domain}/"
        if not sub.startswith(prefix):
            raise InvalidSVID(
                f"sub {sub!r} not in trust domain {self.trust_domain!r}"
            )

        return AgentPrincipal(
            spiffe_id=sub,
            issued_at=int(claims["iat"]),
            expires_at=int(claims["exp"]),
            raw_claims=claims,
        )
