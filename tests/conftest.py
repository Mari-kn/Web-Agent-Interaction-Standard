"""Shared test fixtures."""

import pytest

from pod.issuer import PoDIssuer
from pod.verifier import PoDVerifier
from pod.token import DelegationPayload
from pod.scopes import Scopes


PLATFORM_URL = "https://test-platform.com"
AUDIENCE = "https://test-store.com"


@pytest.fixture
def keypair():
    return PoDIssuer.generate_keypair()


@pytest.fixture
def private_pem(keypair):
    return keypair[0]


@pytest.fixture
def public_pem(keypair):
    return keypair[1]


@pytest.fixture
def issuer(private_pem):
    return PoDIssuer(
        platform_url=PLATFORM_URL,
        private_key_pem=private_pem,
        key_id="test-key-1",
    )


@pytest.fixture
def verifier(public_pem):
    v = PoDVerifier()
    v.add_trusted_platform_pem(PLATFORM_URL, public_pem)
    return v


@pytest.fixture
def user_hash():
    return DelegationPayload.hash_user_id("user-test-123")


@pytest.fixture
def sample_token(issuer, user_hash):
    return issuer.create_token(
        agent_session="session-test",
        audience=AUDIENCE,
        user_hash=user_hash,
        scopes=Scopes.ecommerce_full(),
        constraints={
            "max_transaction_amount": {"value": 500, "currency": "EUR"},
            "require_confirmation_above": {"value": 100, "currency": "EUR"},
        },
        ttl_seconds=3600,
    )
