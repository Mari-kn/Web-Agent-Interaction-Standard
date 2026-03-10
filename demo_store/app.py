"""Demo Store — PoD Token Verifier application."""

from __future__ import annotations

import os
import uuid
import time

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pod.confirmation import ConfirmationChallenge
from demo_store import products, cart
from demo_store.middleware import setup_verifier, verify_pod_token

app = FastAPI(title="WAIS Demo Store")

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="store-static",
)

# Pending confirmation challenges
_pending_challenges: dict[str, dict] = {}


@app.on_event("startup")
async def startup():
    await setup_verifier()


# ============ HTML Routes (Browser) ============

@app.get("/", response_class=HTMLResponse)
async def catalog_page(request: Request):
    return templates.TemplateResponse("catalog.html", {
        "request": request,
        "products": products.get_all(),
    })


@app.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request):
    # For browser, use a simple session cookie
    session_id = request.cookies.get("session_id", "browser")
    items = cart.get_cart(session_id)
    total = cart.cart_total(session_id)
    return templates.TemplateResponse("cart.html", {
        "request": request,
        "items": items,
        "total": total,
    })


@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    session_id = request.cookies.get("session_id", "browser")
    items = cart.get_cart(session_id)
    total = cart.cart_total(session_id)
    return templates.TemplateResponse("checkout.html", {
        "request": request,
        "items": items,
        "total": total,
    })


# ============ API Routes (Agents) ============

@app.get("/api/products")
async def api_products(request: Request):
    """Browse product catalog. Public or with PoD token."""
    # Allow browsing without token for demo purposes
    token_string = request.headers.get("X-WAIS-PoD")
    if token_string:
        verify_pod_token(request, required_scopes=["catalog.browse"])
    return {"products": products.get_all()}


@app.get("/api/products/{product_id}")
async def api_product_detail(product_id: str, request: Request):
    product = products.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.post("/api/cart")
async def api_add_to_cart(request: Request):
    result = verify_pod_token(request, required_scopes=["cart.modify"])
    session_id = result.token.sub

    body = await request.json()
    product_id = body.get("product_id")
    quantity = body.get("quantity", 1)

    if not product_id:
        raise HTTPException(status_code=400, detail="product_id is required")

    try:
        items = cart.add_to_cart(session_id, product_id, quantity)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "cart": items,
        "total": cart.cart_total(session_id),
    }


@app.get("/api/cart")
async def api_view_cart(request: Request):
    result = verify_pod_token(request, required_scopes=["cart.modify"])
    session_id = result.token.sub

    return {
        "cart": cart.get_cart(session_id),
        "total": cart.cart_total(session_id),
    }


@app.delete("/api/cart/{product_id}")
async def api_remove_from_cart(product_id: str, request: Request):
    result = verify_pod_token(request, required_scopes=["cart.modify"])
    session_id = result.token.sub

    items = cart.remove_from_cart(session_id, product_id)
    return {
        "cart": items,
        "total": cart.cart_total(session_id),
    }


@app.post("/api/checkout")
async def api_checkout(request: Request):
    result = verify_pod_token(request, required_scopes=["checkout.execute"])
    session_id = result.token.sub

    total = cart.cart_total(session_id)
    items = cart.get_cart(session_id)

    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Check if amount exceeds limit
    if result.exceeds_limit(total, "EUR"):
        raise HTTPException(
            status_code=403,
            detail=f"Transaction amount EUR {total:.2f} exceeds authorized limit",
        )

    # Check if confirmation is needed
    if result.requires_confirmation(total, "EUR"):
        challenge = ConfirmationChallenge.create(
            action="checkout",
            risk_level="high",
            ttl_seconds=300,
            display_to_user={
                "summary": f"Purchase {len(items)} item(s) from Demo Store",
                "total": f"EUR {total:.2f}",
                "items": [f"{i['name']} x{i['quantity']} — EUR {i['price'] * i['quantity']:.2f}" for i in items],
            },
        )
        _pending_challenges[challenge.challenge_id] = {
            "challenge": challenge,
            "session_id": session_id,
            "total": total,
            "items": items,
        }
        return JSONResponse(
            status_code=402,
            content=challenge.to_dict(),
        )

    # Complete checkout
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    cart.clear_cart(session_id)

    return {
        "status": "completed",
        "order_id": order_id,
        "total": f"EUR {total:.2f}",
        "items_count": len(items),
    }


@app.post("/api/checkout/confirm")
async def api_checkout_confirm(request: Request):
    result = verify_pod_token(request, required_scopes=["checkout.execute"])
    session_id = result.token.sub

    body = await request.json()
    challenge_id = body.get("challenge_id")

    if not challenge_id or challenge_id not in _pending_challenges:
        raise HTTPException(status_code=404, detail="Challenge not found or expired")

    pending = _pending_challenges[challenge_id]
    challenge = pending["challenge"]

    if challenge.is_expired:
        del _pending_challenges[challenge_id]
        raise HTTPException(status_code=410, detail="Challenge expired")

    if pending["session_id"] != session_id:
        raise HTTPException(status_code=403, detail="Challenge belongs to different session")

    # Complete the purchase
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    total = pending["total"]
    items = pending["items"]

    cart.clear_cart(session_id)
    del _pending_challenges[challenge_id]

    return {
        "status": "completed",
        "order_id": order_id,
        "total": f"EUR {total:.2f}",
        "items_count": len(items),
        "confirmed": True,
    }
