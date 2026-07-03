"""API routers package — aggregates all routers under /api."""
from fastapi import APIRouter

from app.api import auth, favorites, health, import_, posts, tags

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(posts.router)
api_router.include_router(tags.router)
api_router.include_router(favorites.router)
api_router.include_router(import_.router)

__all__ = ["api_router"]
