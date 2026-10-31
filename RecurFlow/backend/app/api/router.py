"""Main API routing assembly."""

from fastapi import APIRouter

from app.core.config import settings

api_router = APIRouter(prefix=settings.API_V1_PREFIX)


@api_router.get("/status", tags=["System"])
def api_status() -> dict[str, str]:
    """Basic API v1 health check."""
    return {"status": "online", "api_version": "v1"}
