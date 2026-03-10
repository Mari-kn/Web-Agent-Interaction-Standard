"""
PoD Token data models.

Defines the structure of a Proof of Delegation token,
including the delegation payload, constraints, and scopes.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Constraints:
    """Authorization constraints on the delegation."""

    max_transaction_amount: Optional[dict] = None  # {"value": 500, "currency": "EUR"}
    require_confirmation_above: Optional[dict] = None
    allowed_domains: Optional[list[str]] = None
    geo_restrictions: Optional[list[str]] = None  # ISO country codes

    def exceeds_amount(self, amount: float, currency: str) -> bool:
        """Check if an amount exceeds the max transaction limit."""
        if self.max_transaction_amount is None:
            return False
        if self.max_transaction_amount.get("currency") != currency:
            return True  # Different currency = require confirmation
        return amount > self.max_transaction_amount.get("value", 0)

    def needs_confirmation(self, amount: float, currency: str) -> bool:
        """Check if an amount requires user confirmation."""
        if self.require_confirmation_above is None:
            return False
        if self.require_confirmation_above.get("currency") != currency:
            return True
        return amount > self.require_confirmation_above.get("value", 0)

    def to_dict(self) -> dict:
        result = {}
        if self.max_transaction_amount:
            result["max_transaction_amount"] = self.max_transaction_amount
        if self.require_confirmation_above:
            result["require_confirmation_above"] = self.require_confirmation_above
        if self.allowed_domains:
            result["allowed_domains"] = self.allowed_domains
        if self.geo_restrictions:
            result["geo_restrictions"] = self.geo_restrictions
        return result


@dataclass
class DelegationPayload:
    """The delegation section of a PoD token."""

    user_hash: str
    user_verified: bool
    consent_timestamp: int
    scopes: list[str]
    constraints: Constraints = field(default_factory=Constraints)

    @staticmethod
    def hash_user_id(user_id: str) -> str:
        """Create a privacy-preserving hash of a user identifier."""
        return f"sha256:{hashlib.sha256(user_id.encode()).hexdigest()}"

    def has_scope(self, scope: str) -> bool:
        """Check if the delegation includes a specific scope."""
        # Support wildcard: "catalog.*" matches "catalog.browse"
        for s in self.scopes:
            if s == scope:
                return True
            if s.endswith(".*"):
                prefix = s[:-2]
                if scope.startswith(prefix + "."):
                    return True
        return False

    def has_all_scopes(self, scopes: list[str]) -> bool:
        """Check if the delegation includes all specified scopes."""
        return all(self.has_scope(s) for s in scopes)

    def to_dict(self) -> dict:
        return {
            "user_hash": self.user_hash,
            "user_verified": self.user_verified,
            "consent_timestamp": self.consent_timestamp,
            "scopes": self.scopes,
            "constraints": self.constraints.to_dict(),
        }


@dataclass
class PoDToken:
    """A complete Proof of Delegation token."""

    # Header
    alg: str = "ES256"
    typ: str = "WAIS-PoD"
    kid: Optional[str] = None

    # Standard JWT claims
    iss: str = ""  # Issuer (agent platform URL)
    sub: str = ""  # Subject (agent session ID)
    aud: str = ""  # Audience (target website)
    iat: int = 0  # Issued at
    exp: int = 0  # Expiration
    jti: Optional[str] = None  # Token ID for replay protection

    # PoD-specific
    delegation: DelegationPayload = field(default_factory=lambda: DelegationPayload(
        user_hash="", user_verified=False, consent_timestamp=0, scopes=[]
    ))

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return time.time() > self.exp

    @property
    def header(self) -> dict:
        h = {"alg": self.alg, "typ": self.typ}
        if self.kid:
            h["kid"] = self.kid
        return h

    @property
    def payload(self) -> dict:
        p = {
            "iss": self.iss,
            "sub": self.sub,
            "aud": self.aud,
            "iat": self.iat,
            "exp": self.exp,
            "jti": self.jti,
            "delegation": self.delegation.to_dict(),
        }
        return p

    def to_dict(self) -> dict:
        return {
            "header": self.header,
            "payload": self.payload,
        }
