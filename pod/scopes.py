"""
Standard WAIS Scopes by vertical.

Provides a taxonomy of scopes for common website interaction patterns.
Sites and agents use these to agree on what actions are authorized.
"""


class Scopes:
    """Standard WAIS scope definitions."""

    # === E-Commerce ===
    CATALOG_BROWSE = "catalog.browse"
    CATALOG_COMPARE = "catalog.compare"
    CART_MODIFY = "cart.modify"
    CHECKOUT_EXECUTE = "checkout.execute"
    ORDER_TRACK = "order.track"
    RETURN_INITIATE = "return.initiate"
    RETURN_COMPLETE = "return.complete"
    SUBSCRIPTION_MANAGE = "subscription.manage"

    # === Travel & Hospitality ===
    AVAILABILITY_SEARCH = "availability.search"
    BOOKING_CREATE = "booking.create"
    BOOKING_MODIFY = "booking.modify"
    BOOKING_CANCEL = "booking.cancel"
    CLAIM_SUBMIT = "claim.submit"

    # === Financial Services ===
    ACCOUNT_READ = "account.read"
    QUOTE_REQUEST = "quote.request"
    PAYMENT_EXECUTE = "payment.execute"
    DISPUTE_FILE = "dispute.file"
    POLICY_MODIFY = "policy.modify"

    # === Government & Public Services ===
    APPOINTMENT_BOOK = "appointment.book"
    FORM_SUBMIT = "form.submit"
    DOCUMENT_REQUEST = "document.request"
    STATUS_CHECK = "status.check"

    # === Healthcare ===
    APPOINTMENT_SCHEDULE = "appointment.schedule"
    PRESCRIPTION_RENEW = "prescription.renew"
    RECORDS_ACCESS = "records.access"

    # Risk level mappings
    RISK_LEVELS = {
        # E-Commerce
        "catalog.browse": "low",
        "catalog.compare": "low",
        "cart.modify": "medium",
        "checkout.execute": "high",
        "order.track": "low",
        "return.initiate": "medium",
        "return.complete": "high",
        "subscription.manage": "high",
        # Travel
        "availability.search": "low",
        "booking.create": "high",
        "booking.modify": "high",
        "booking.cancel": "high",
        "claim.submit": "medium",
        # Financial
        "account.read": "medium",
        "quote.request": "low",
        "payment.execute": "critical",
        "dispute.file": "medium",
        "policy.modify": "high",
        # Government
        "appointment.book": "medium",
        "form.submit": "high",
        "document.request": "high",
        "status.check": "low",
        # Healthcare
        "appointment.schedule": "medium",
        "prescription.renew": "high",
        "records.access": "critical",
    }

    @classmethod
    def risk_level(cls, scope: str) -> str:
        """Get the default risk level for a scope."""
        return cls.RISK_LEVELS.get(scope, "medium")

    @classmethod
    def is_high_risk(cls, scope: str) -> bool:
        """Check if a scope is high or critical risk."""
        return cls.risk_level(scope) in ("high", "critical")

    @classmethod
    def ecommerce_read(cls) -> list[str]:
        """Common read-only e-commerce scopes."""
        return [cls.CATALOG_BROWSE, cls.CATALOG_COMPARE, cls.ORDER_TRACK]

    @classmethod
    def ecommerce_full(cls) -> list[str]:
        """Full e-commerce scopes including transactions."""
        return [
            cls.CATALOG_BROWSE, cls.CATALOG_COMPARE, cls.CART_MODIFY,
            cls.CHECKOUT_EXECUTE, cls.ORDER_TRACK,
            cls.RETURN_INITIATE, cls.RETURN_COMPLETE,
        ]

    @classmethod
    def travel_full(cls) -> list[str]:
        """Full travel scopes."""
        return [
            cls.AVAILABILITY_SEARCH, cls.BOOKING_CREATE,
            cls.BOOKING_MODIFY, cls.BOOKING_CANCEL, cls.CLAIM_SUBMIT,
        ]
