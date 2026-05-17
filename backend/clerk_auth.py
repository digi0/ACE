import os
import logging
from functools import lru_cache
from typing import Optional

from fastapi import Request, HTTPException
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _clerk() -> Clerk:
    key = os.getenv("CLERK_SECRET_KEY")
    if not key:
        raise RuntimeError("CLERK_SECRET_KEY env var is not set")
    return Clerk(bearer_auth=key)


def _authorized_parties() -> Optional[list[str]]:
    raw = os.getenv("ALLOWED_ORIGINS", "")
    parties = [p.strip() for p in raw.split(",") if p.strip()]
    return parties or None


def _authenticate(request: Request):
    return _clerk().authenticate_request(
        request,
        AuthenticateRequestOptions(authorized_parties=_authorized_parties()),
    )


def _payload_to_user(payload: dict) -> dict:
    """Map a Clerk JWT payload to the shape the rest of the app expects.

    Note: the default Clerk session JWT only carries `sub`. Email / name are
    fetched separately via fetch_user_details() in /auth/sync and persisted
    to our User row, so downstream endpoints only need `uid`.
    """
    return {
        "uid": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name"),
    }


async def get_current_user(request: Request) -> dict:
    """Dependency: verifies Clerk session token, returns {uid, email?, name?}."""
    state = _authenticate(request)
    if not state.is_signed_in:
        reason = getattr(state, "reason", None) or "Not authenticated"
        raise HTTPException(status_code=401, detail=str(reason))
    return _payload_to_user(state.payload or {})


async def get_optional_user(request: Request) -> Optional[dict]:
    """Like get_current_user but returns None instead of 401 when missing/invalid."""
    try:
        state = _authenticate(request)
    except Exception as exc:
        logger.debug("optional auth failed: %s", exc)
        return None
    if not state.is_signed_in:
        return None
    return _payload_to_user(state.payload or {})


async def get_current_user_any(request: Request) -> dict:
    """Kept for API parity with the old firebase_auth module. Clerk enforces
    email verification at sign-in time, so there's no separate unverified
    state to allow through — this is identical to get_current_user."""
    return await get_current_user(request)


def fetch_user_details(uid: str) -> dict:
    """One-shot call to Clerk's user API to grab email + display name. Used by
    /auth/sync to hydrate the User row; downstream endpoints don't need this."""
    user = _clerk().users.get(user_id=uid)
    primary_email = None
    for addr in (user.email_addresses or []):
        if addr.id == user.primary_email_address_id:
            primary_email = addr.email_address
            break
    if primary_email is None and user.email_addresses:
        primary_email = user.email_addresses[0].email_address
    name = " ".join(p for p in [user.first_name, user.last_name] if p).strip()
    if not name:
        name = user.username or None
    return {"email": primary_email, "name": name}
