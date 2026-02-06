"""
API Authentication

Hybrid authentication supporting both API keys and Supabase JWT tokens.
"""

import os
import secrets
from typing import Optional, Union

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from .supabase_auth import User, decode_supabase_jwt

# API key read from environment — fail fast if not set in production
_PLM_API_KEY = os.getenv("PLM_API_KEY")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def require_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    FastAPI dependency that enforces API key authentication.

    If PLM_API_KEY is not set, authentication is disabled (dev mode).
    """
    if not _PLM_API_KEY:
        # No key configured — allow (dev/test mode)
        return "dev"

    if not api_key or not secrets.compare_digest(api_key, _PLM_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key


async def require_auth(
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Union[str, User]:
    """
    Hybrid authentication dependency that accepts either:
    - API key via X-API-Key header
    - Supabase JWT via Authorization: Bearer header

    In dev mode (no PLM_API_KEY set), allows unauthenticated access.

    Returns:
        Either the API key string or a User object from JWT
    """
    # Dev mode — no auth configured
    if not _PLM_API_KEY and not os.getenv("SUPABASE_JWT_SECRET"):
        return "dev"

    # Try API key first
    if api_key:
        if _PLM_API_KEY and secrets.compare_digest(api_key, _PLM_API_KEY):
            return api_key

    # Try JWT bearer token
    if bearer:
        try:
            payload = decode_supabase_jwt(bearer.credentials)
            return User.from_jwt_payload(payload)
        except HTTPException:
            pass  # Fall through to error

    # Neither worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_user_id(auth: Union[str, User] = Depends(require_auth)) -> Optional[str]:
    """
    Extract user ID from authentication result.

    Returns:
        User ID if JWT auth, None if API key auth
    """
    if isinstance(auth, User):
        return auth.id
    return None
