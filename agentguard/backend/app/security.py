import secrets
from fastapi import Header, HTTPException
from app.config import settings


def require_access(x_api_key: str | None = Header(default=None)) -> None:
    if settings.demo_mode:
        return  # ONLY for loopback/local development; never expose this mode publicly.
    if not settings.agentguard_api_key:
        raise HTTPException(status_code=503, detail="API authentication not configured")
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.agentguard_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
