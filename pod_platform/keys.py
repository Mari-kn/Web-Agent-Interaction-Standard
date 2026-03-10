"""Key management for the PoD platform."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def generate_or_load_keypair(keys_dir: str = "keys") -> tuple[bytes, bytes, str]:
    """Generate an ES256 keypair on first run, load from disk after.

    Returns:
        (private_pem, public_pem, kid)
    """
    keys_path = Path(keys_dir)
    keys_path.mkdir(exist_ok=True)

    priv_path = keys_path / "private.pem"
    pub_path = keys_path / "public.pem"

    if priv_path.exists() and pub_path.exists():
        private_pem = priv_path.read_bytes()
        public_pem = pub_path.read_bytes()
    else:
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
        priv_path.write_bytes(private_pem)
        pub_path.write_bytes(public_pem)
        os.chmod(priv_path, 0o600)

    kid = _derive_kid(public_pem)
    return private_pem, public_pem, kid


def _derive_kid(public_pem: bytes) -> str:
    """Derive a key ID from the public key (first 8 chars of SHA256)."""
    return hashlib.sha256(public_pem).hexdigest()[:8]


def get_jwks_document(public_pem: bytes, kid: str) -> dict:
    """Convert a public key PEM to a JWKS document."""
    public_key = serialization.load_pem_public_key(public_pem)
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise ValueError("Expected EC public key")

    numbers = public_key.public_numbers()
    import base64

    x_bytes = numbers.x.to_bytes(32, byteorder="big")
    y_bytes = numbers.y.to_bytes(32, byteorder="big")

    return {
        "keys": [
            {
                "kty": "EC",
                "crv": "P-256",
                "x": base64.urlsafe_b64encode(x_bytes).rstrip(b"=").decode(),
                "y": base64.urlsafe_b64encode(y_bytes).rstrip(b"=").decode(),
                "kid": kid,
                "use": "sig",
                "alg": "ES256",
            }
        ]
    }
