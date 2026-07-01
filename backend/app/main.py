"""FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.config import settings
from app.services.errors import AppError, app_error_handler, unhandled_exception_handler

app = FastAPI(title="Picture Mangers API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Static image storage — served at /media/* (same-origin via the Next.js
# rewrite). The directory is created on startup if missing so a fresh dev
# checkout doesn't 500 before any post is imported.
_media_dir = settings.media_path
_media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")

# Unified error envelope: AppError subclasses + a catch-all for unexpected faults.
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get("/")
def root() -> dict:
    return {"name": "Picture Mangers API", "docs": "/docs"}
