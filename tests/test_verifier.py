"""Tests for pod.verifier module."""

import time
import json
import base64

from pod.verifier import PoDVerifier, VerificationResult
from pod.issuer import PoDIssuer
from pod.token import DelegationPayload
from pod.scopes import Scopes

from tests.conftest import PLATFORM_URL, AUDIENCE


class TestVerificationResult:
    def test_requires_confirmation_invalid(self):
        r = VerificationResult(valid=False)
        assert r.requires_confirmation(50, "EUR") is True

    def test_exceeds_limit_invalid(self):
        r = VerificationResult(valid=False)
        assert r.exceeds_limit(50, "EUR") is True


class TestPoDVerifier:
    def test_valid_token(self, verifier, sample_token):
        result = verifier.verify(
            sample_token,
            required_scopes=["catalog.browse"],
            expected_audience=AUDIENCE,
        )
        assert result.valid is True
        assert result.token is not None
        assert result.token.iss == PLATFORM_URL

    def test_expired_token(self, keypair, user_hash):
        priv, pub = keypair
        issuer = PoDIssuer(platform_url=PLATFORM_URL, private_key_pem=priv)
        token = issuer.create_token(
            agent_session="s1",
            audience=AUDIENCE,
            user_hash=user_hash,
            scopes=["catalog.browse"],
            ttl_seconds=-100,  # Already expired
        )
        verifier = PoDVerifier()
        verifier.add_trusted_platform_pem(PLATFORM_URL, pub)
        result = verifier.verify(token, expected_audience=AUDIENCE)
        assert result.valid is False
        assert "expired" in result.reason.lower()

    def test_wrong_audience(self, verifier, sample_token):
        result = verifier.verify(
            sample_token,
            expected_audience="https://wrong-store.com",
        )
        assert result.valid is False
        assert "audience" in result.reason.lower()

    def test_missing_scopes(self, verifier, sample_token):
        result = verifier.verify(
            sample_token,
            required_scopes=["payment.execute"],
            expected_audience=AUDIENCE,
        )
        assert result.valid is False
        assert "scopes" in result.reason.lower()

    def test_tampered_signature(self, verifier, sample_token):
        parts = sample_token.split(".")
        # Flip a character in the signature
        sig = parts[2]
        tampered = sig[:-1] + ("A" if sig[-1] != "A" else "B")
        tampered_token = f"{parts[0]}.{parts[1]}.{tampered}"
        result = verifier.verify(tampered_token, expected_audience=AUDIENCE)
        assert result.valid is False
        assert "signature" in result.reason.lower()

    def test_unknown_platform(self, sample_token):
        verifier = PoDVerifier()  # No trusted platforms
        result = verifier.verify(sample_token)
        assert result.valid is False
        assert "unknown" in result.reason.lower()

    def test_invalid_format(self, verifier):
        result = verifier.verify("not.a.valid.token.here")
        assert result.valid is False

    def test_replay_protection(self, verifier, sample_token):
        # First use should work
        result1 = verifier.verify(sample_token, expected_audience=AUDIENCE)
        assert result1.valid is True
        # Second use should be rejected as replay
        result2 = verifier.verify(sample_token, expected_audience=AUDIENCE)
        assert result2.valid is False
        assert "replay" in result2.reason.lower()

    def test_iat_future(self, keypair, user_hash):
        """Token issued far in the future should be rejected."""
        priv, pub = keypair
        issuer = PoDIssuer(platform_url=PLATFORM_URL, private_key_pem=priv)
        # Manually create a token with iat far in the future
        token = issuer.create_token(
            agent_session="s1",
            audience=AUDIENCE,
            user_hash=user_hash,
            scopes=["catalog.browse"],
            ttl_seconds=3600,
        )
        # Tamper with iat by rebuilding payload
        parts = token.split(".")
        padding = 4 - len(parts[1]) % 4
        p1 = parts[1]
        if padding != 4:
            p1 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(p1))
        payload["iat"] = int(time.time()) + 600  # 10 min in future
        new_payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()
        # Re-sign with the private key
        import pod.issuer as issuer_mod
        iss = PoDIssuer(platform_url=PLATFORM_URL, private_key_pem=priv)
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec, utils
        signing_input = f"{parts[0]}.{new_payload_b64}".encode()
        der_sig = iss._private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
        r, s = utils.decode_dss_signature(der_sig)
        sig_bytes = r.to_bytes(32, "big") + s.to_bytes(32, "big")
        sig_b64 = base64.urlsafe_b64encode(sig_bytes).rstrip(b"=").decode()
        future_token = f"{parts[0]}.{new_payload_b64}.{sig_b64}"

        verifier = PoDVerifier()
        verifier.add_trusted_platform_pem(PLATFORM_URL, pub)
        result = verifier.verify(future_token, expected_audience=AUDIENCE)
        assert result.valid is False
        assert "future" in result.reason.lower()

    def test_allow_expired(self, keypair, user_hash):
        priv, pub = keypair
        issuer = PoDIssuer(platform_url=PLATFORM_URL, private_key_pem=priv)
        token = issuer.create_token(
            agent_session="s1",
            audience=AUDIENCE,
            user_hash=user_hash,
            scopes=["catalog.browse"],
            ttl_seconds=-100,
        )
        verifier = PoDVerifier(allow_expired=True)
        verifier.add_trusted_platform_pem(PLATFORM_URL, pub)
        result = verifier.verify(token, expected_audience=AUDIENCE)
        assert result.valid is True

    def test_user_not_verified(self, keypair):
        priv, pub = keypair
        issuer = PoDIssuer(platform_url=PLATFORM_URL, private_key_pem=priv)
        user_hash = DelegationPayload.hash_user_id("user-1")
        token = issuer.create_token(
            agent_session="s1",
            audience=AUDIENCE,
            user_hash=user_hash,
            scopes=["catalog.browse"],
            user_verified=False,
        )
        verifier = PoDVerifier()
        verifier.add_trusted_platform_pem(PLATFORM_URL, pub)
        result = verifier.verify(token, expected_audience=AUDIENCE)
        assert result.valid is False
        assert "verified" in result.reason.lower()
