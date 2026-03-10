"""MCP Server — WAIS PoD Demo Store agent tools."""

from __future__ import annotations

import os
import json

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("wais-pod-demo")

STORE_URL = os.environ.get("STORE_URL", "http://localhost:8001")
POD_TOKEN = os.environ.get("POD_TOKEN", "")


def _client() -> httpx.Client:
    headers = {}
    if POD_TOKEN:
        headers["X-WAIS-PoD"] = POD_TOKEN
    return httpx.Client(base_url=STORE_URL, headers=headers, timeout=10.0)


@mcp.tool()
def browse_catalog() -> str:
    """Browse the demo store product catalog. Returns a list of available products with prices."""
    with _client() as client:
        resp = client.get("/api/products")
        resp.raise_for_status()
        data = resp.json()
    products = data.get("products", [])
    lines = []
    for p in products:
        lines.append(f"- {p['name']} ({p['id']}): {p['currency']} {p['price']:.2f} — {p['description']}")
    return "\n".join(lines) if lines else "No products found."


@mcp.tool()
def get_product_details(product_id: str) -> str:
    """Get detailed information about a specific product by its ID."""
    with _client() as client:
        resp = client.get(f"/api/products/{product_id}")
        if resp.status_code == 404:
            return f"Product not found: {product_id}"
        resp.raise_for_status()
    return json.dumps(resp.json(), indent=2)


@mcp.tool()
def add_to_cart(product_id: str, quantity: int = 1) -> str:
    """Add a product to the shopping cart. Requires cart.modify scope."""
    with _client() as client:
        resp = client.post("/api/cart", json={"product_id": product_id, "quantity": quantity})
        if resp.status_code == 403:
            return f"Permission denied: {resp.json().get('detail', 'Insufficient scopes')}"
        if resp.status_code == 401:
            return "Authentication required. Make sure POD_TOKEN is set."
        resp.raise_for_status()
        data = resp.json()
    total = data.get("total", 0)
    items = data.get("cart", [])
    lines = [f"Cart updated ({len(items)} item(s), total: EUR {total:.2f}):"]
    for item in items:
        lines.append(f"  - {item['name']} x{item['quantity']}: EUR {item['price'] * item['quantity']:.2f}")
    return "\n".join(lines)


@mcp.tool()
def view_cart() -> str:
    """View the current shopping cart contents and total."""
    with _client() as client:
        resp = client.get("/api/cart")
        if resp.status_code in (401, 403):
            return f"Access denied: {resp.json().get('detail', 'Token required')}"
        resp.raise_for_status()
        data = resp.json()
    items = data.get("cart", [])
    total = data.get("total", 0)
    if not items:
        return "Cart is empty."
    lines = [f"Shopping Cart (total: EUR {total:.2f}):"]
    for item in items:
        lines.append(f"  - {item['name']} x{item['quantity']}: EUR {item['price'] * item['quantity']:.2f}")
    return "\n".join(lines)


@mcp.tool()
def remove_from_cart(product_id: str) -> str:
    """Remove a product from the shopping cart by product ID."""
    with _client() as client:
        resp = client.delete(f"/api/cart/{product_id}")
        if resp.status_code in (401, 403):
            return f"Access denied: {resp.json().get('detail', 'Token required')}"
        resp.raise_for_status()
        data = resp.json()
    items = data.get("cart", [])
    total = data.get("total", 0)
    return f"Item removed. Cart now has {len(items)} item(s), total: EUR {total:.2f}"


@mcp.tool()
def checkout() -> str:
    """Attempt to checkout the current cart. May require confirmation for large amounts.

    If the total exceeds the confirmation threshold, a challenge will be returned.
    Use confirm_purchase with the challenge_id to complete the purchase.
    """
    with _client() as client:
        resp = client.post("/api/checkout")
        if resp.status_code == 400:
            return f"Cannot checkout: {resp.json().get('detail', 'Unknown error')}"
        if resp.status_code == 401:
            return "Authentication required."
        if resp.status_code == 403:
            return f"Denied: {resp.json().get('detail', 'Exceeds limit')}"
        if resp.status_code == 402:
            # Confirmation required
            data = resp.json()
            challenge = data.get("wais_confirmation", {})
            display = challenge.get("display_to_user", {})
            lines = [
                "CONFIRMATION REQUIRED",
                f"Action: {challenge.get('action', 'checkout')}",
                f"Risk level: {challenge.get('risk_level', 'high')}",
                f"Challenge ID: {challenge.get('challenge_id', '')}",
                "",
                f"Summary: {display.get('summary', '')}",
                f"Total: {display.get('total', '')}",
            ]
            for item in display.get("items", []):
                lines.append(f"  - {item}")
            lines.append("")
            lines.append("To complete this purchase, call confirm_purchase with the challenge_id above.")
            return "\n".join(lines)
        resp.raise_for_status()
        data = resp.json()
    return f"Order completed! Order ID: {data.get('order_id')} | Total: {data.get('total')}"


@mcp.tool()
def confirm_purchase(challenge_id: str) -> str:
    """Confirm a purchase after receiving a confirmation challenge from checkout."""
    with _client() as client:
        resp = client.post("/api/checkout/confirm", json={"challenge_id": challenge_id})
        if resp.status_code == 404:
            return "Challenge not found or expired. Try checking out again."
        if resp.status_code == 410:
            return "Challenge has expired. Please checkout again."
        if resp.status_code in (401, 403):
            return f"Access denied: {resp.json().get('detail', '')}"
        resp.raise_for_status()
        data = resp.json()
    return f"Purchase confirmed! Order ID: {data.get('order_id')} | Total: {data.get('total')}"


if __name__ == "__main__":
    mcp.run()
