"""PoD Platform — Token Issuer application."""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Optional

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from pod.issuer import PoDIssuer
from pod.token import DelegationPayload
from pod.scopes import Scopes
from pod_platform import models
from pod_platform.auth import oauth, setup_oauth, get_current_user
from pod_platform.keys import generate_or_load_keypair, get_jwks_document

app = FastAPI(title="WAIS PoD Platform")

# --- State (populated at startup) ---
_issuer: Optional[PoDIssuer] = None
_public_pem: bytes = b""
_kid: str = ""
_jwks: dict = {}
_platform_url: str = ""

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)

# Session middleware
secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.add_middleware(SessionMiddleware, secret_key=secret_key)


@app.on_event("startup")
async def startup():
    global _issuer, _public_pem, _kid, _jwks, _platform_url

    _platform_url = os.environ.get("PLATFORM_URL", "http://localhost:8000")
    private_pem, _public_pem, _kid = generate_or_load_keypair()
    _issuer = PoDIssuer(
        platform_url=_platform_url,
        private_key_pem=private_pem,
        key_id=_kid,
    )
    _jwks = get_jwks_document(_public_pem, _kid)
    setup_oauth()


# ============ JWKS (Public) ============

@app.get("/.well-known/jwks.json")
async def jwks():
    return JSONResponse(_jwks)


# ============ Auth Routes ============

@app.get("/auth/login")
async def auth_login(request: Request):
    redirect_uri = f"{_platform_url}/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo", {})
    email = userinfo.get("email", "")
    name = userinfo.get("name", email)
    picture = userinfo.get("picture", "")
    sub = userinfo.get("sub", "")

    models.upsert_user(email=email, name=name, picture=picture, google_sub=sub)
    request.session["user_email"] = email
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/auth/logout")
async def auth_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)


# ============ HTML Routes ============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)
    user_tokens = models.get_user_tokens(user["email"])
    highlight_jti = request.query_params.get("highlight")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "tokens": user_tokens,
        "highlight_jti": highlight_jti,
        "now": int(time.time()),
    })


@app.get("/tokens/create", response_class=HTMLResponse)
async def create_token_form(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)

    scopes_by_vertical = {
        "E-Commerce": [
            Scopes.CATALOG_BROWSE, Scopes.CATALOG_COMPARE, Scopes.CART_MODIFY,
            Scopes.CHECKOUT_EXECUTE, Scopes.ORDER_TRACK,
            Scopes.RETURN_INITIATE, Scopes.RETURN_COMPLETE,
        ],
        "Travel": [
            Scopes.AVAILABILITY_SEARCH, Scopes.BOOKING_CREATE,
            Scopes.BOOKING_MODIFY, Scopes.BOOKING_CANCEL,
        ],
        "Financial": [
            Scopes.ACCOUNT_READ, Scopes.QUOTE_REQUEST,
            Scopes.PAYMENT_EXECUTE,
        ],
    }
    return templates.TemplateResponse("create_token.html", {
        "request": request,
        "user": user,
        "scopes_by_vertical": scopes_by_vertical,
    })


@app.post("/tokens/create")
async def create_token_submit(
    request: Request,
    audience: str = Form(...),
    ttl: int = Form(3600),
    max_amount: float = Form(0),
    confirm_above: float = Form(0),
    currency: str = Form("EUR"),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)

    form_data = await request.form()
    scopes = form_data.getlist("scopes")

    constraints = {}
    if max_amount > 0:
        constraints["max_transaction_amount"] = {"value": max_amount, "currency": currency}
    if confirm_above > 0:
        constraints["require_confirmation_above"] = {"value": confirm_above, "currency": currency}

    user_hash = DelegationPayload.hash_user_id(user["email"])

    token_string = _issuer.create_token(
        agent_session=f"web-{uuid.uuid4().hex[:8]}",
        audience=audience,
        user_hash=user_hash,
        scopes=scopes,
        constraints=constraints,
        ttl_seconds=ttl,
    )

    # Extract jti from token
    import base64
    parts = token_string.split(".")
    payload_b64 = parts[1]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    jti = payload["jti"]
    iat = payload["iat"]
    exp = payload["exp"]

    models.store_token(
        jti=jti,
        email=user["email"],
        token_string=token_string,
        audience=audience,
        scopes=scopes,
        constraints=constraints,
        iat=iat,
        exp=exp,
    )

    return RedirectResponse(url=f"/dashboard?highlight={jti}", status_code=302)


@app.post("/tokens/{jti}/revoke")
async def revoke_token_html(jti: str, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)
    models.revoke_token(jti)
    return RedirectResponse(url="/dashboard", status_code=302)


# ============ API Routes ============

def _require_api_user(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@app.post("/api/tokens")
async def api_create_token(request: Request):
    user = _require_api_user(request)
    body = await request.json()

    audience = body.get("audience", "")
    scopes = body.get("scopes", [])
    constraints = body.get("constraints", {})
    ttl = body.get("ttl_seconds", 3600)

    user_hash = DelegationPayload.hash_user_id(user["email"])
    token_string = _issuer.create_token(
        agent_session=f"api-{uuid.uuid4().hex[:8]}",
        audience=audience,
        user_hash=user_hash,
        scopes=scopes,
        constraints=constraints,
        ttl_seconds=ttl,
    )

    import base64
    parts = token_string.split(".")
    payload_b64 = parts[1]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))

    models.store_token(
        jti=payload["jti"],
        email=user["email"],
        token_string=token_string,
        audience=audience,
        scopes=scopes,
        constraints=constraints,
        iat=payload["iat"],
        exp=payload["exp"],
    )

    return {"token": token_string, "jti": payload["jti"]}


@app.get("/api/tokens")
async def api_list_tokens(request: Request):
    user = _require_api_user(request)
    return {"tokens": models.get_user_tokens(user["email"])}


@app.delete("/api/tokens/{jti}")
async def api_revoke_token(jti: str, request: Request):
    user = _require_api_user(request)
    if models.revoke_token(jti):
        return {"status": "revoked"}
    raise HTTPException(status_code=404, detail="Token not found")
