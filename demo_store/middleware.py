"""PoD token verification middleware for the demo store."""

from __future__ import annotations

import base64
import os
from functools import wraps
from typing import Optional

import httpx
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicNumbers, SECP256R1

from fastapi import Request, HTTPException

from pod.verifier import PoDVerifier, VerificationResult

# Global verifier instance, configured at startup
verifier: Optional[PoDVerifier] = None


async def setup_verifier():
    """Fetch JWKS from platform and configure the verifier."""
    global verifier

    platform_url = os.environ.get("PLATFORM_URL", "http://localhost:8000")
    store_url = os.environ.get("STORE_URL", "http://localhost:8001")

    verifier = PoDVerifier()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{platform_url}/.well-known/jwks.json", timeout=5.0)
            resp.raise_for_status()
            jwks = resp.json()

        for key_data in jwks.get("keys", []):
            pem = jwk_to_pem(key_data)
            verifier.add_trusted_platform_pem(platform_url, pem)
    except Exception as e:
        print(f"Warning: Could not fetch JWKS from {platform_url}: {e}")
        print("  Store will reject all tokens until platform is available.")


def jwk_to_pem(jwk: dict) -> bytes:
    """Convert a JWK EC key to PEM format."""
    x_b64 = jwk["x"]
    y_b64 = jwk["y"]

    # Add padding
    for val in (x_b64, y_b64):
        padding = 4 - len(val) % 4
        if padding != 4:
            val += "=" * padding

    x_bytes = base64.urlsafe_b64decode(x_b64 + "==")
    y_bytes = base64.urlsafe_b64decode(y_b64 + "==")

    x = int.from_bytes(x_bytes, byteorder="big")
    y = int.from_bytes(y_bytes, byteorder="big")

    public_numbers = EllipticCurvePublicNumbers(x=x, y=y, curve=SECP256R1())
    public_key = public_numbers.public_key()

    from cryptography.hazmat.primitives import serialization
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def verify_pod_token(
    request: Request,
    required_scopes: list[str] | None = None,
) -> VerificationResult:
    """Verify the PoD token from request headers."""
    if verifier is None:
        raise HTTPException(status_code=503, detail="Verifier not configured")

    token_string = request.headers.get("X-WAIS-PoD")
    if not token_string:
        raise HTTPException(status_code=401, detail="Missing X-WAIS-PoD header")

    store_url = os.environ.get("STORE_URL", "http://localhost:8001")

    result = verifier.verify(
        token_string=token_string,
        required_scopes=required_scopes,
        expected_audience=store_url,
    )

    if not result.valid:
        raise HTTPException(status_code=403, detail=f"Token verification failed: {result.reason}")

    return result
