from fastapi import APIRouter



from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.db_health import router as db_health_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.products import router as products_router
from app.api.v1.endpoints.cart import router as cart_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(db_health_router, tags=["db-health"])
api_v1_router.include_router(auth_router, tags=["auth"])
api_v1_router.include_router(products_router, tags=["products"])
api_v1_router.include_router(cart_router, tags=["cart"])
