"""Login with bcrypt-hashed passwords and cookie sessions."""

import secrets
import time

import bcrypt
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.mcp_server.db import fetch_password_hash

COOKIE_NAME = "session"
SESSION_SECONDS = 8 * 60 * 60
MAX_PASSWORD_BYTES = 72  # bcrypt's limit

_PUBLIC_PATHS = {"/api/auth/login", "/api/auth/logout"}
_DOC_PATHS = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}

# token -> (email, expiry). In memory, so a server restart signs everyone out.
_sessions: dict[str, tuple[str, float]] = {}

# Checked when the email is unknown, so both failures take the same time.
_DUMMY_HASH = bcrypt.hashpw(b"unused", bcrypt.gensalt())

router = APIRouter(prefix="/api/auth")


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=MAX_PASSWORD_BYTES)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    encoded = password.encode()
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    stored = password_hash.encode() if password_hash else _DUMMY_HASH
    return bcrypt.checkpw(encoded, stored) and password_hash is not None


def current_user(request: Request) -> str | None:
    session = _sessions.get(request.cookies.get(COOKIE_NAME, ""))
    if session is None or session[1] < time.time():
        return None
    return session[0]


async def require_login(request: Request, call_next):
    """Reject every API and docs request without a valid session."""
    path = request.scope["path"]
    protected = path.startswith("/api/") or path in _DOC_PATHS
    if protected and path not in _PUBLIC_PATHS and current_user(request) is None:
        return JSONResponse({"detail": "Please sign in."}, status_code=401)
    return await call_next(request)


# A plain def, so the slow bcrypt check runs off the event loop.
@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    email = body.email.strip().lower()
    if not verify_password(body.password, fetch_password_hash(email)):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    now = time.time()
    for token, (_, expiry) in list(_sessions.items()):
        if expiry < now:
            _sessions.pop(token, None)

    token = secrets.token_urlsafe(32)
    _sessions[token] = (email, now + SESSION_SECONDS)

    # Azure terminates HTTPS in front of the container and reports it in a header.
    secure = "https" in (request.url.scheme, request.headers.get("x-forwarded-proto"))
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=secure,
        samesite="strict",
    )
    return {"email": email}


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict:
    _sessions.pop(request.cookies.get(COOKIE_NAME, ""), None)
    response.delete_cookie(COOKIE_NAME)
    return {"status": "signed_out"}


@router.get("/me")
async def me(request: Request) -> dict:
    return {"email": current_user(request)}
