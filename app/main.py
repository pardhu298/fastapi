from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.config import settings


def create_application() -> FastAPI:
    """Application factory for easier testing and future scaling."""
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Keep API versioning explicit from day one.
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_application()
