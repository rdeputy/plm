"""
PLM FastAPI Application

Main application factory and configuration.
"""

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_api_key
from .logging_config import RequestLoggingMiddleware, logger
from .metrics import MetricsMiddleware, get_metrics, get_metrics_content_type
from .rate_limit import RateLimitMiddleware
from .security_headers import SecurityHeadersMiddleware
from .routers import (
    parts,
    configurations,
    boms,
    changes,
    documents,
    ipc,
    workflows,
    audit,
    notifications,
    reports,
    integrations,
    requirements,
    suppliers,
    compliance,
    costing,
    service_bulletins,
    projects,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="PLM API",
        description="""
## Product Lifecycle Management API

A comprehensive API for managing product lifecycles across industries including:
- **DevOps** — Software and infrastructure components
- **PD&E** — Product development and engineering
- **AEC** — Architecture, engineering, and construction
- **Manufacturing** — Parts, BOMs, and change management

### Authentication

All `/api/v1/*` endpoints require authentication via:
- **API Key**: `X-API-Key` header
- **JWT Token**: `Authorization: Bearer <token>` header (Supabase)

### Rate Limiting

Default: 60 requests/minute per client IP. Configurable via `PLM_RATE_LIMIT_RPM`.

### Monitoring

- `/health` — Health check endpoint
- `/metrics` — Prometheus metrics endpoint
        """,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "Parts", "description": "Part master data and revisions"},
            {"name": "BOMs", "description": "Bill of Materials management"},
            {"name": "Documents", "description": "Document control with versioning and checkout"},
            {"name": "Changes", "description": "Engineering Change Orders (ECO/ECN)"},
            {"name": "Projects", "description": "Project management and tracking"},
            {"name": "Requirements", "description": "Requirements traceability"},
            {"name": "Workflows", "description": "Approval workflows and tasks"},
            {"name": "Compliance", "description": "Regulatory compliance tracking"},
            {"name": "Suppliers", "description": "Supplier and vendor management"},
            {"name": "Costing", "description": "Cost estimation and tracking"},
            {"name": "Notifications", "description": "User notifications and preferences"},
            {"name": "Audit", "description": "Audit trail and history"},
            {"name": "Reports", "description": "Reporting and analytics"},
            {"name": "Integrations", "description": "External system integrations"},
        ],
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        contact={
            "name": "PLM Support",
            "url": "https://github.com/rdeputy/plm",
        },
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

    # Security headers middleware (outermost)
    app.add_middleware(SecurityHeadersMiddleware)

    # Metrics middleware
    app.add_middleware(MetricsMiddleware)

    # Rate limiting middleware
    app.add_middleware(RateLimitMiddleware)

    # Request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    logger.info("PLM API starting", extra={"extra_data": {"version": "0.1.0"}})

    # Include routers — all /api/v1/* routes require API key
    api_deps = [Depends(require_api_key)]
    app.include_router(
        parts.router, prefix="/api/v1/parts", tags=["Parts"], dependencies=api_deps
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
    app.include_router(
        workflows.router, prefix="/api/v1/workflows", tags=["Workflows"], dependencies=api_deps
    )
    app.include_router(
        audit.router, prefix="/api/v1/audit", tags=["Audit"], dependencies=api_deps
    )
    app.include_router(
        notifications.router, prefix="/api/v1/notifications", tags=["Notifications"], dependencies=api_deps
    )
    app.include_router(
        reports.router, prefix="/api/v1/reports", tags=["Reports"], dependencies=api_deps
    )
    app.include_router(
        integrations.router, prefix="/api/v1/integrations", tags=["Integrations"], dependencies=api_deps
    )
    app.include_router(
        requirements.router, prefix="/api/v1/requirements", tags=["Requirements"], dependencies=api_deps
    )
    app.include_router(
        suppliers.router, prefix="/api/v1/suppliers", tags=["Suppliers"], dependencies=api_deps
    )
    app.include_router(
        compliance.router, prefix="/api/v1/compliance", tags=["Compliance"], dependencies=api_deps
    )
    app.include_router(
        costing.router, prefix="/api/v1/costing", tags=["Costing"], dependencies=api_deps
    )
    app.include_router(
        service_bulletins.router, prefix="/api/v1/bulletins", tags=["Service Bulletins"], dependencies=api_deps
    )
    app.include_router(
        projects.router, prefix="/api/v1/projects", tags=["Projects"], dependencies=api_deps
    )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "plm"}

    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        from fastapi.responses import Response
        return Response(
            content=get_metrics(),
            media_type=get_metrics_content_type(),
        )

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
