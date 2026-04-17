import os
import json
import logging
import firebase_admin
from firebase_admin import auth as fb_auth, credentials
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# ── Initialize Firebase Admin SDK ────────────────────────────────────────────
# Priority: FIREBASE_SERVICE_ACCOUNT_JSON env var (Railway) >
#           GOOGLE_APPLICATION_CREDENTIALS file > project ID only
if not firebase_admin._apps:
    sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        cred = credentials.Certificate(json.loads(sa_json))
        firebase_admin.initialize_app(cred)
    else:
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            project_id = os.getenv("FIREBASE_PROJECT_ID", "ace1-a42fc")
            firebase_admin.initialize_app(options={"projectId": project_id})


def _verify(token: str) -> dict:
    try:
        return fb_auth.verify_id_token(token)
    except fb_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except fb_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except Exception as e:
        logger.error("Firebase token verification failed: %s", e)
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Dependency: verifies Bearer token, returns decoded claims dict (uid, email, …)."""
    if not creds:
        raise HTTPException(status_code=401, detail="Authorization header required")
    decoded = _verify(creds.credentials)

    # Block unverified email/password users — Google sign-in is always verified
    if not decoded.get("email_verified", False):
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please check your inbox.",
        )

    return decoded


async def get_optional_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> dict | None:
    """Like get_current_user but returns None instead of 401 when no token is present."""
    if not creds:
        return None
    try:
        return _verify(creds.credentials)
    except HTTPException:
        return None
