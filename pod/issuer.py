"""
PoD Token Issuer.

Used by agent platforms (e.g., Anthropic, OpenAI) to create
delegation tokens that agents present to websites.
"""

from __future__ import annotations

import json
import time
import uuid
import base64
from typing import Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

from pod.token import PoDToken, DelegationPayload, Constraints


class PoDIssuer:
    """Issues Proof of Delegation tokens for an agent platform."""

    def __init__(
        self,
        platform_url: str,
        private_key_path: Optional[str] = None,
        private_key_pem: Optional[bytes] = None,
        key_id: Optional[str] = None,
    ):
        self.platform_url = platform_url
        self.key_id = key_id

        if private_key_path:
            with open(private_key_path, "rb") as f:
                self._private_key = serialization.load_pem_private_key(f.read(), password=None)
        elif private_key_pem:
            self._private_key = serialization.load_pem_private_key(private_key_pem, password=None)
        else:
            raise ValueError("Either private_key_path or private_key_pem must be provided")

    @staticmethod
    def generate_keypair() -> tuple[bytes, bytes]:
        """Generate an ES256 key pair for signing tokens.

        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        private_key = ec.generate_private_key(ec.SECP256R1())

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return private_pem, public_pem

    def create_token(
        self,
        agent_session: str,
        audience: str,
        user_hash: str,
        scopes: list[str],
        constraints: Optional[dict] = None,
        ttl_seconds: int = 3600,
        user_verified: bool = True,
    ) -> str:
        """Create a signed PoD token.

        Args:
            agent_session: Unique identifier for the agent session.
            audience: Target website URL.
            user_hash: Privacy-preserving hash of the user.
            scopes: List of authorized scopes.
            constraints: Optional constraints dict.
            ttl_seconds: Token time-to-live in seconds (default 1 hour).
            user_verified: Whether the user has been verified.

        Returns:
            Encoded and signed PoD token string.
        """
        now = int(time.time())

        constraint_obj = Constraints()
        if constraints:
            constraint_obj = Constraints(
                max_transaction_amount=constraints.get("max_transaction_amount"),
                require_confirmation_above=constraints.get("require_confirmation_above"),
                allowed_domains=constraints.get("allowed_domains"),
                geo_restrictions=constraints.get("geo_restrictions"),
            )

        token = PoDToken(
            alg="ES256",
            typ="WAIS-PoD",
            kid=self.key_id,
            iss=self.platform_url,
            sub=f"agent:{agent_session}",
            aud=audience,
            iat=now,
            exp=now + ttl_seconds,
            jti=str(uuid.uuid4()),
            delegation=DelegationPayload(
                user_hash=user_hash,
                user_verified=user_verified,
                consent_timestamp=now,
                scopes=scopes,
                constraints=constraint_obj,
            ),
        )

        return self._sign(token)

    def _sign(self, token: PoDToken) -> str:
        """Sign the token and return the encoded string."""
        header_b64 = self._b64url_encode(json.dumps(token.header))
        payload_b64 = self._b64url_encode(json.dumps(token.payload))

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

        der_signature = self._private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
        # Convert DER signature to R||S format per RFC 7518 (JWS ES256)
        r, s = utils.decode_dss_signature(der_signature)
        signature = r.to_bytes(32, byteorder="big") + s.to_bytes(32, byteorder="big")
        signature_b64 = self._b64url_encode_bytes(signature)

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    @staticmethod
    def _b64url_encode(data: str) -> str:
        return base64.urlsafe_b64encode(data.encode("utf-8")).rstrip(b"=").decode("utf-8")

    @staticmethod
    def _b64url_encode_bytes(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")
