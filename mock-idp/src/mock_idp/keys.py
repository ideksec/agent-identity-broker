import base64
import os

import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


class SigningKey:
    def __init__(self, private_pem: bytes, kid: str | None = None):
        self.private_pem = private_pem
        self.private_key = serialization.load_pem_private_key(private_pem, password=None)
        self.public_key = self.private_key.public_key()

        # Stable kid: SHA-256(public_key DER) prefix (RFC 7638-ish).
        if kid:
            self.kid = kid
        else:
            der = self.public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            digest = hashes.Hash(hashes.SHA256())
            digest.update(der)
            self.kid = _b64url(digest.finalize())[:16]

    @classmethod
    def from_path_or_generate(cls, path: str | None) -> "SigningKey":
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                return cls(f.read())
        # Generate ephemeral
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return cls(private_pem)

    def jwk(self) -> dict:
        jwk = jwt.algorithms.RSAAlgorithm.to_jwk(self.public_key, as_dict=True)
        jwk["kid"] = self.kid
        jwk["alg"] = "RS256"
        jwk["use"] = "sig"
        return jwk
