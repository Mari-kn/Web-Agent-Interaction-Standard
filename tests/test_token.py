"""Tests for pod.token module."""

import time

from pod.token import PoDToken, DelegationPayload, Constraints


class TestConstraints:
    def test_exceeds_amount_none(self):
        c = Constraints()
        assert c.exceeds_amount(1000, "EUR") is False

    def test_exceeds_amount_under(self):
        c = Constraints(max_transaction_amount={"value": 500, "currency": "EUR"})
        assert c.exceeds_amount(499, "EUR") is False

    def test_exceeds_amount_over(self):
        c = Constraints(max_transaction_amount={"value": 500, "currency": "EUR"})
        assert c.exceeds_amount(501, "EUR") is True

    def test_exceeds_amount_different_currency(self):
        c = Constraints(max_transaction_amount={"value": 500, "currency": "EUR"})
        assert c.exceeds_amount(100, "USD") is True

    def test_needs_confirmation_none(self):
        c = Constraints()
        assert c.needs_confirmation(1000, "EUR") is False

    def test_needs_confirmation_under(self):
        c = Constraints(require_confirmation_above={"value": 100, "currency": "EUR"})
        assert c.needs_confirmation(50, "EUR") is False

    def test_needs_confirmation_over(self):
        c = Constraints(require_confirmation_above={"value": 100, "currency": "EUR"})
        assert c.needs_confirmation(150, "EUR") is True

    def test_to_dict_empty(self):
        c = Constraints()
        assert c.to_dict() == {}

    def test_to_dict_full(self):
        c = Constraints(
            max_transaction_amount={"value": 500, "currency": "EUR"},
            allowed_domains=["example.com"],
        )
        d = c.to_dict()
        assert "max_transaction_amount" in d
        assert "allowed_domains" in d
        assert "require_confirmation_above" not in d


class TestDelegationPayload:
    def test_hash_user_id(self):
        h = DelegationPayload.hash_user_id("user-123")
        assert h.startswith("sha256:")
        assert len(h) == 71  # "sha256:" + 64 hex chars

    def test_hash_user_id_deterministic(self):
        h1 = DelegationPayload.hash_user_id("user-123")
        h2 = DelegationPayload.hash_user_id("user-123")
        assert h1 == h2

    def test_has_scope_exact(self):
        dp = DelegationPayload(
            user_hash="test", user_verified=True,
            consent_timestamp=0, scopes=["catalog.browse", "cart.modify"],
        )
        assert dp.has_scope("catalog.browse") is True
        assert dp.has_scope("checkout.execute") is False

    def test_has_scope_wildcard(self):
        dp = DelegationPayload(
            user_hash="test", user_verified=True,
            consent_timestamp=0, scopes=["catalog.*"],
        )
        assert dp.has_scope("catalog.browse") is True
        assert dp.has_scope("catalog.compare") is True
        assert dp.has_scope("cart.modify") is False

    def test_has_all_scopes(self):
        dp = DelegationPayload(
            user_hash="test", user_verified=True,
            consent_timestamp=0, scopes=["catalog.browse", "cart.modify"],
        )
        assert dp.has_all_scopes(["catalog.browse", "cart.modify"]) is True
        assert dp.has_all_scopes(["catalog.browse", "checkout.execute"]) is False

    def test_to_dict(self):
        dp = DelegationPayload(
            user_hash="test", user_verified=True,
            consent_timestamp=1000, scopes=["catalog.browse"],
        )
        d = dp.to_dict()
        assert d["user_hash"] == "test"
        assert d["user_verified"] is True
        assert d["scopes"] == ["catalog.browse"]


class TestPoDToken:
    def test_is_expired(self):
        token = PoDToken(exp=int(time.time()) - 100)
        assert token.is_expired is True

    def test_not_expired(self):
        token = PoDToken(exp=int(time.time()) + 3600)
        assert token.is_expired is False

    def test_header(self):
        token = PoDToken(alg="ES256", typ="WAIS-PoD", kid="key-1")
        h = token.header
        assert h == {"alg": "ES256", "typ": "WAIS-PoD", "kid": "key-1"}

    def test_header_no_kid(self):
        token = PoDToken()
        h = token.header
        assert "kid" not in h

    def test_payload_always_has_jti(self):
        token = PoDToken(jti=None)
        p = token.payload
        assert "jti" in p
        assert p["jti"] is None

    def test_payload_with_jti(self):
        token = PoDToken(jti="abc-123")
        p = token.payload
        assert p["jti"] == "abc-123"

    def test_to_dict(self):
        token = PoDToken(iss="test", sub="agent:1", aud="store")
        d = token.to_dict()
        assert "header" in d
        assert "payload" in d
