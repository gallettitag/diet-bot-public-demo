"""
Diet Intelligence Platform — FastAPI application entry point.

Full service implementation is maintained privately.
This file demonstrates application structure, middleware configuration,
and lifespan management.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes database connection pool and embedding provider on startup.
    Cleanly closes all connections on shutdown.
    """
    # startup: initialize db pool, embedding provider, warm rule cache
    yield
    # shutdown: close connections


def create_app() -> FastAPI:
    app = FastAPI(
        title="Diet Intelligence Platform",
        description="Clinical diet reasoning engine with deterministic safety evaluation",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers registered here in full implementation
    # app.include_router(analysis_router, prefix="/api/v1")
    # app.include_router(ingest_router, prefix="/api/v1")
    # app.include_router(recipe_router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
