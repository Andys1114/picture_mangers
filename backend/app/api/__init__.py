"""API routers package — aggregates all routers under /api."""
from fastapi import APIRouter

from app.api import auth, health, posts

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(posts.router)

__all__ = ["api_router"]
