"""
API Key Authentication — FastAPI dependency for shared-secret auth.

When API_KEY is set in .env, every protected endpoint requires:
    X-API-Key: <value>

When API_KEY is empty the check is skipped (development mode only).
A CRITICAL warning is emitted at startup in that case.
"""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from config.settings import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(x_api_key: str | None = Security(_api_key_header)) -> None:
    """Dependency: validate the X-API-Key header.

    Raises HTTP 401 if a key is configured but the request does not supply
    the correct value.  No-ops when API_KEY is empty (dev mode).
    """
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
