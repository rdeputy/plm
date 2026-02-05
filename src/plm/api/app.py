"""
PLM FastAPI Application

Main application factory and configuration.
"""

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_api_key
from .routers import parts, inventory, procurement, configurations, boms, changes, documents, ipc


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="PLM API",
        description="Product Lifecycle Management for Construction",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware — restrict origins via env var
    allowed_origins = os.getenv(
        "PLM_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:8001",
    ).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers — all /api/v1/* routes require API key
    api_deps = [Depends(require_api_key)]
    app.include_router(
        parts.router, prefix="/api/v1/parts", tags=["Parts"], dependencies=api_deps
    )
    app.include_router(
        inventory.router, prefix="/api/v1/inventory", tags=["Inventory"], dependencies=api_deps
    )
    app.include_router(
        procurement.router, prefix="/api/v1/procurement", tags=["Procurement"], dependencies=api_deps
    )
    app.include_router(
        configurations.router, prefix="/api/v1/configurations", tags=["Configurations"], dependencies=api_deps
    )
    app.include_router(
        boms.router, prefix="/api/v1/boms", tags=["BOMs"], dependencies=api_deps
    )
    app.include_router(
        changes.router, prefix="/api/v1/changes", tags=["Changes"], dependencies=api_deps
    )
    app.include_router(
        documents.router, prefix="/api/v1/documents", tags=["Documents"], dependencies=api_deps
    )
    app.include_router(
        ipc.router, prefix="/api/v1/ipc", tags=["IPC"], dependencies=api_deps
    )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "plm"}

    @app.get("/")
    async def root():
        """Root endpoint with API info."""
        return {
            "service": "PLM API",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app


# Application instance for uvicorn
app = create_app()
