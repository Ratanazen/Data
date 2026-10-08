"""
Health & System Status API route
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from ...config import settings
from ..schemas import HealthResponse

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Returns application health status, version, runtime mode, and storage availability."""
    storage_ok = settings.GOLD_PATH.exists() and any(settings.GOLD_PATH.iterdir())
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        mode=settings.MODE,
        environment=settings.APP_ENV,
        storage_status="operational" if storage_ok else "initializing",
        kafka_status="ready" if settings.MODE == "streaming" else "disabled_in_local_mode",
        timestamp=datetime.now(timezone.utc).isoformat()
    )
