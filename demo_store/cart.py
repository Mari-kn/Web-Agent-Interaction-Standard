"""In-memory shopping cart keyed by session (agent sub)."""

from __future__ import annotations

from demo_store.products import get_by_id

# Carts keyed by session ID (token sub field)
_carts: dict[str, list[dict]] = {}


def get_cart(session_id: str) -> list[dict]:
    return _carts.get(session_id, [])


def add_to_cart(session_id: str, product_id: str, quantity: int = 1) -> list[dict]:
    product = get_by_id(product_id)
    if not product:
        raise ValueError(f"Product not found: {product_id}")

    cart = _carts.setdefault(session_id, [])

    # Check if already in cart
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            return cart

    cart.append({
        "product_id": product_id,
        "name": product["name"],
        "price": product["price"],
        "currency": product["currency"],
        "quantity": quantity,
    })
    return cart


def remove_from_cart(session_id: str, product_id: str) -> list[dict]:
    cart = _carts.get(session_id, [])
    _carts[session_id] = [i for i in cart if i["product_id"] != product_id]
    return _carts[session_id]


def cart_total(session_id: str) -> float:
    cart = get_cart(session_id)
    return sum(item["price"] * item["quantity"] for item in cart)


def clear_cart(session_id: str) -> None:
    _carts.pop(session_id, None)
