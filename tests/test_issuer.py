"""Tests for pod.issuer module."""

import base64
import json

from pod.issuer import PoDIssuer
from pod.scopes import Scopes
from pod.token import DelegationPayload

from tests.conftest import PLATFORM_URL, AUDIENCE


class TestPoDIssuer:
    def test_generate_keypair(self):
        priv, pub = PoDIssuer.generate_keypair()
        assert b"BEGIN PRIVATE KEY" in priv
        assert b"BEGIN PUBLIC KEY" in pub

    def test_create_token_format(self, issuer, user_hash):
        token = issuer.create_token(
            agent_session="s1",
            audience=AUDIENCE,
            user_hash=user_hash,
            scopes=["catalog.browse"],
        )
        parts = token.split(".")
        assert len(parts) == 3

    def test_signature_is_64_bytes(self, issuer, user_hash):
        """ES256 R||S signature must be exactly 64 bytes."""
        token = issuer.create_token(
            agent_session="s1",
            audience=AUDIENCE,
            user_hash=user_hash,
            scopes=["catalog.browse"],
        )
        sig_b64 = token.split(".")[2]
        # Add padding
        padding = 4 - len(sig_b64) % 4
        if padding != 4:
            sig_b64 += "=" * padding
        sig_bytes = base64.urlsafe_b64decode(sig_b64)
        assert len(sig_bytes) == 64

    def test_token_header(self, issuer, user_hash):
        token = issuer.create_token(
            agent_session="s1",
            audience=AUDIENCE,
            user_hash=user_hash,
            scopes=["catalog.browse"],
        )
        header_b64 = token.split(".")[0]
        padding = 4 - len(header_b64) % 4
        if padding != 4:
            header_b64 += "=" * padding
        header = json.loads(base64.urlsafe_b64decode(header_b64))
        assert header["alg"] == "ES256"
        assert header["typ"] == "WAIS-PoD"
        assert header["kid"] == "test-key-1"

    def test_token_payload_has_jti(self, issuer, user_hash):
        token = issuer.create_token(
            agent_session="s1",
            audience=AUDIENCE,
            user_hash=user_hash,
            scopes=["catalog.browse"],
        )
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        assert "jti" in payload
        assert payload["jti"] is not None

    def test_token_payload_fields(self, issuer, user_hash):
        token = issuer.create_token(
            agent_session="s1",
            audience=AUDIENCE,
            user_hash=user_hash,
            scopes=["catalog.browse"],
            ttl_seconds=7200,
        )
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        assert payload["iss"] == PLATFORM_URL
        assert payload["aud"] == AUDIENCE
        assert payload["sub"] == "agent:s1"
        assert payload["exp"] - payload["iat"] == 7200

    def test_issuer_requires_key(self):
        try:
            PoDIssuer(platform_url="https://test.com")
            assert False, "Should raise ValueError"
        except ValueError:
            pass
