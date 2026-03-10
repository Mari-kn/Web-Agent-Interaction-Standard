"""In-memory data store for users and tokens."""

from __future__ import annotations

from typing import Optional

# In-memory stores
users: dict[str, dict] = {}
tokens: dict[str, dict] = {}


def upsert_user(email: str, name: str, picture: str = "", google_sub: str = "") -> dict:
    """Create or update a user."""
    user = {
        "email": email,
        "name": name,
        "picture": picture,
        "google_sub": google_sub,
    }
    users[email] = user
    return user


def get_user(email: str) -> Optional[dict]:
    """Get a user by email."""
    return users.get(email)


def store_token(
    jti: str,
    email: str,
    token_string: str,
    audience: str,
    scopes: list[str],
    constraints: dict,
    iat: int,
    exp: int,
) -> dict:
    """Store a token with metadata."""
    entry = {
        "jti": jti,
        "email": email,
        "token_string": token_string,
        "audience": audience,
        "scopes": scopes,
        "constraints": constraints,
        "iat": iat,
        "exp": exp,
        "revoked": False,
    }
    tokens[jti] = entry
    return entry


def get_user_tokens(email: str) -> list[dict]:
    """Get all tokens for a user, most recent first."""
    user_tokens = [t for t in tokens.values() if t["email"] == email]
    return sorted(user_tokens, key=lambda t: t["iat"], reverse=True)


def revoke_token(jti: str) -> bool:
    """Revoke a token by jti. Returns True if found."""
    if jti in tokens:
        tokens[jti]["revoked"] = True
        return True
    return False
