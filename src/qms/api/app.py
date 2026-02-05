"""
QMS FastAPI Application

Quality Management System - separate from PLM but integrated.
"""

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_api_key
from .routers import quality, warranty


def create_app() -> FastAPI:
    """Create and configure the QMS FastAPI application."""
    app = FastAPI(
        title="QMS API",
        description="Quality Management System",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware — restrict origins via env var
    allowed_origins = os.getenv(
        "QMS_CORS_ORIGINS",
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
        quality.router, prefix="/api/v1/quality", tags=["Quality"], dependencies=api_deps
    )
    app.include_router(
        warranty.router, prefix="/api/v1/warranty", tags=["Warranty"], dependencies=api_deps
    )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "qms"}

    @app.get("/")
    async def root():
        """Root endpoint with API info."""
        return {
            "service": "QMS API",
            "version": "0.1.0",
            "docs": "/docs",
            "modules": ["quality", "warranty"],
        }

    return app


# Application instance for uvicorn
app = create_app()
