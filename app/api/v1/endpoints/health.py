from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Health check")
async def health_check() -> dict[str, str]:
    """Liveness endpoint used by load balancers and uptime monitors."""
    return {
        "status": "ok",
        "service": "api",
        "timestamp": datetime.now(UTC).isoformat(),
    }
