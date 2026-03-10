"""Tests for pod.confirmation module."""

import time

from pod.confirmation import ConfirmationChallenge, ConfirmationResponse


class TestConfirmationChallenge:
    def test_create(self):
        c = ConfirmationChallenge.create(
            action="checkout",
            risk_level="high",
            ttl_seconds=300,
        )
        assert c.action == "checkout"
        assert c.risk_level == "high"
        assert c.challenge_id.startswith("conf_")
        assert c.is_expired is False

    def test_expired(self):
        c = ConfirmationChallenge.create(
            action="checkout",
            ttl_seconds=-10,
        )
        assert c.is_expired is True

    def test_to_dict(self):
        c = ConfirmationChallenge.create(
            action="checkout",
            display_to_user={"summary": "Buy stuff", "total": "€100"},
        )
        d = c.to_dict()
        assert "wais_confirmation" in d
        inner = d["wais_confirmation"]
        assert inner["action"] == "checkout"
        assert inner["display_to_user"]["total"] == "€100"

    def test_approval_methods_default(self):
        c = ConfirmationChallenge.create(action="checkout")
        assert c.approval_methods == ["user_confirm"]

    def test_custom_approval_methods(self):
        c = ConfirmationChallenge.create(
            action="checkout",
            approval_methods=["biometric", "pin"],
        )
        assert "biometric" in c.approval_methods


class TestConfirmationResponse:
    def test_is_valid(self):
        r = ConfirmationResponse(
            challenge_id="conf_abc",
            approved=True,
            user_hash="sha256:abc",
            platform_signature="sig123",
        )
        assert r.is_valid is True

    def test_is_invalid_missing_fields(self):
        r = ConfirmationResponse()
        assert r.is_valid is False

    def test_is_invalid_not_approved(self):
        r = ConfirmationResponse(
            challenge_id="conf_abc",
            approved=False,
            user_hash="sha256:abc",
            platform_signature="sig123",
        )
        assert r.is_valid is False

    def test_to_dict(self):
        r = ConfirmationResponse(
            challenge_id="conf_abc",
            approved=True,
            approval_method="biometric",
            approved_at=1000,
            user_hash="sha256:abc",
            platform_signature="sig123",
        )
        d = r.to_dict()
        assert "wais_confirmation_response" in d
        assert d["wais_confirmation_response"]["challenge_id"] == "conf_abc"
