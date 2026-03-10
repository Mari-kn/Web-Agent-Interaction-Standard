"""
Confirmation Protocol.

Handles the challenge-response flow for high-risk actions
that require explicit user approval.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConfirmationChallenge:
    """A confirmation challenge sent by a site to an agent."""

    challenge_id: str = field(default_factory=lambda: f"conf_{uuid.uuid4().hex[:12]}")
    action: str = ""
    risk_level: str = "high"  # "medium", "high", "critical"
    expires_at: int = 0
    display_to_user: dict = field(default_factory=dict)
    approval_methods: list[str] = field(default_factory=lambda: ["user_confirm"])

    @classmethod
    def create(
        cls,
        action: str,
        risk_level: str = "high",
        ttl_seconds: int = 300,
        display_to_user: Optional[dict] = None,
        approval_methods: Optional[list[str]] = None,
    ) -> "ConfirmationChallenge":
        return cls(
            action=action,
            risk_level=risk_level,
            expires_at=int(time.time()) + ttl_seconds,
            display_to_user=display_to_user or {},
            approval_methods=approval_methods or ["user_confirm"],
        )

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "wais_confirmation": {
                "challenge_id": self.challenge_id,
                "action": self.action,
                "risk_level": self.risk_level,
                "expires_at": self.expires_at,
                "display_to_user": self.display_to_user,
                "approval_methods": self.approval_methods,
            }
        }


@dataclass
class ConfirmationResponse:
    """A signed confirmation response from an agent platform."""

    challenge_id: str = ""
    approved: bool = False
    approval_method: str = "user_confirm"
    approved_at: int = 0
    user_hash: str = ""
    platform_signature: str = ""

    @property
    def is_valid(self) -> bool:
        return (
            bool(self.challenge_id)
            and self.approved
            and bool(self.user_hash)
            and bool(self.platform_signature)
        )

    def to_dict(self) -> dict:
        return {
            "wais_confirmation_response": {
                "challenge_id": self.challenge_id,
                "approved": self.approved,
                "approval_method": self.approval_method,
                "approved_at": self.approved_at,
                "user_hash": self.user_hash,
                "platform_signature": self.platform_signature,
            }
        }
