"""
PLM FastAPI Application

Main application factory and configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import parts, inventory, procurement, configurations


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="PLM API",
        description="Product Lifecycle Management for Construction",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(parts.router, prefix="/api/v1/parts", tags=["Parts"])
    app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])
    app.include_router(procurement.router, prefix="/api/v1/procurement", tags=["Procurement"])
    app.include_router(
        configurations.router, prefix="/api/v1/configurations", tags=["Configurations"]
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
