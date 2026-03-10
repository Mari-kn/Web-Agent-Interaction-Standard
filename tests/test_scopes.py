"""Tests for pod.scopes module."""

from pod.scopes import Scopes


class TestScopes:
    def test_risk_level_known(self):
        assert Scopes.risk_level("catalog.browse") == "low"
        assert Scopes.risk_level("checkout.execute") == "high"
        assert Scopes.risk_level("payment.execute") == "critical"

    def test_risk_level_unknown(self):
        assert Scopes.risk_level("unknown.scope") == "medium"

    def test_is_high_risk(self):
        assert Scopes.is_high_risk("checkout.execute") is True
        assert Scopes.is_high_risk("payment.execute") is True
        assert Scopes.is_high_risk("catalog.browse") is False

    def test_ecommerce_read(self):
        scopes = Scopes.ecommerce_read()
        assert "catalog.browse" in scopes
        assert "checkout.execute" not in scopes

    def test_ecommerce_full(self):
        scopes = Scopes.ecommerce_full()
        assert "catalog.browse" in scopes
        assert "checkout.execute" in scopes
        assert "cart.modify" in scopes

    def test_travel_full(self):
        scopes = Scopes.travel_full()
        assert "availability.search" in scopes
        assert "booking.create" in scopes
