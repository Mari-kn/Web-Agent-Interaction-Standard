"""Hardcoded product catalog for the demo store."""

from __future__ import annotations

PRODUCTS: list[dict] = [
    {
        "id": "headphones-1",
        "name": "Sony WH-1000XM5 Headphones",
        "price": 189.00,
        "currency": "EUR",
        "description": "Industry-leading noise cancellation with premium sound quality.",
        "category": "Audio",
    },
    {
        "id": "cable-1",
        "name": "USB-C Cable 2-Pack",
        "price": 12.50,
        "currency": "EUR",
        "description": "Braided 2m USB-C to USB-C cables with 100W PD support.",
        "category": "Accessories",
    },
    {
        "id": "protector-1",
        "name": "Screen Protector (iPhone 15)",
        "price": 46.00,
        "currency": "EUR",
        "description": "Tempered glass screen protector with 9H hardness.",
        "category": "Accessories",
    },
    {
        "id": "keyboard-1",
        "name": "Mechanical Keyboard TKL",
        "price": 79.00,
        "currency": "EUR",
        "description": "Tenkeyless mechanical keyboard with Cherry MX Brown switches.",
        "category": "Peripherals",
    },
    {
        "id": "mouse-1",
        "name": "Logitech MX Master 3S",
        "price": 99.00,
        "currency": "EUR",
        "description": "Ergonomic wireless mouse with MagSpeed scroll wheel.",
        "category": "Peripherals",
    },
    {
        "id": "stand-1",
        "name": "Laptop Stand Adjustable",
        "price": 34.00,
        "currency": "EUR",
        "description": "Aluminum laptop stand with adjustable height and angle.",
        "category": "Accessories",
    },
]

PRODUCTS_BY_ID: dict[str, dict] = {p["id"]: p for p in PRODUCTS}


def get_all() -> list[dict]:
    return PRODUCTS


def get_by_id(product_id: str) -> dict | None:
    return PRODUCTS_BY_ID.get(product_id)
