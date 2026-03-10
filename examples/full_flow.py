"""
Example: Full PoD flow — issuing, presenting, and verifying a token.

This example demonstrates:
1. An agent platform generates a key pair
2. The platform issues PoD tokens for a user
3. A website verifies tokens and checks constraints
4. The website sends a confirmation challenge for high-risk actions
"""

from pod import PoDIssuer, PoDVerifier, Scopes
from pod.token import DelegationPayload
from pod.confirmation import ConfirmationChallenge


def main():
    # ===================================================
    # Step 1: Agent platform generates keys (done once)
    # ===================================================
    print("Generating key pair for agent platform...")
    private_pem, public_pem = PoDIssuer.generate_keypair()
    print("   Key pair generated\n")

    # ===================================================
    # Step 2: Agent platform issues PoD tokens
    # ===================================================
    print("Issuing PoD tokens...")
    issuer = PoDIssuer(
        platform_url="https://my-agent-platform.com",
        private_key_pem=private_pem,
        key_id="demo-key-2026",
    )

    user_hash = DelegationPayload.hash_user_id("user-12345")

    def make_token():
        return issuer.create_token(
            agent_session="session-abc123",
            audience="https://example-store.com",
            user_hash=user_hash,
            scopes=Scopes.ecommerce_full(),
            constraints={
                "max_transaction_amount": {"value": 500, "currency": "EUR"},
                "require_confirmation_above": {"value": 100, "currency": "EUR"},
            },
            ttl_seconds=3600,
        )

    token = make_token()
    print(f"   Token issued ({len(token)} chars)")
    print(f"   Scopes: {Scopes.ecommerce_full()}\n")

    # ===================================================
    # Step 3: Website verifies the tokens
    # ===================================================
    print("Website verifying tokens...")
    verifier = PoDVerifier()
    verifier.add_trusted_platform_pem("https://my-agent-platform.com", public_pem)

    # Scenario A: Agent wants to browse catalog (low risk)
    result = verifier.verify(
        token,
        required_scopes=["catalog.browse"],
        expected_audience="https://example-store.com",
    )
    print(f"   Browse catalog: {'ALLOWED' if result.valid else 'DENIED'}")

    # Each verification needs a fresh token (replay protection with jti)
    token_b = make_token()
    result = verifier.verify(
        token_b,
        required_scopes=["checkout.execute"],
        expected_audience="https://example-store.com",
    )
    needs_confirm = result.requires_confirmation(action_amount=50, currency="EUR")
    print(f"   Checkout 50 EUR: {'ALLOWED' if result.valid else 'DENIED'}"
          f" | Confirmation needed: {'Yes' if needs_confirm else 'No'}")

    # Scenario C: Agent wants to checkout 247.50 EUR (above confirmation threshold)
    token_c = make_token()
    result = verifier.verify(
        token_c,
        required_scopes=["checkout.execute"],
        expected_audience="https://example-store.com",
    )
    needs_confirm = result.requires_confirmation(action_amount=247.50, currency="EUR")
    print(f"   Checkout 247.50 EUR: {'ALLOWED' if result.valid else 'DENIED'}"
          f" | Confirmation needed: {'Yes' if needs_confirm else 'No'}")

    # Scenario D: Agent wants to checkout 600 EUR (above max amount)
    exceeds = result.exceeds_limit(action_amount=600, currency="EUR")
    print(f"   Checkout 600 EUR: Exceeds limit: {'YES' if exceeds else 'No'}\n")

    # ===================================================
    # Step 4: Site sends confirmation challenge
    # ===================================================
    print("Generating confirmation challenge for 247.50 EUR checkout...")
    challenge = ConfirmationChallenge.create(
        action="checkout",
        risk_level="high",
        ttl_seconds=300,
        display_to_user={
            "summary": "Purchase 3 items from ExampleStore",
            "total": "247.50 EUR",
            "items": [
                "Sony WH-1000XM5 Headphones - 189.00 EUR",
                "USB-C Cable 2-pack - 12.50 EUR",
                "Screen Protector - 46.00 EUR",
            ],
            "shipping": "Standard (3-5 business days)",
            "payment_method": "Visa ending 4242",
        },
    )
    print(f"   Challenge ID: {challenge.challenge_id}")
    print(f"   Display to user: {challenge.display_to_user['summary']}")
    print(f"   Total: {challenge.display_to_user['total']}")
    print(f"\n   -> Agent presents this to the user for approval")
    print(f"   -> User approves via {challenge.approval_methods}")
    print(f"   -> Agent returns signed confirmation to site")
    print(f"   -> Site completes the checkout\n")

    # ===================================================
    # Bonus: Check scope risk levels
    # ===================================================
    print("Scope risk levels:")
    for scope in Scopes.ecommerce_full():
        risk = Scopes.risk_level(scope)
        indicator = {"low": "[LOW]", "medium": "[MED]", "high": "[HIGH]", "critical": "[CRIT]"}.get(risk, "[?]")
        print(f"   {indicator} {scope}: {risk}")

    print("\nDone! This is what open agent authentication looks like.")


if __name__ == "__main__":
    main()
