"""
Reports API Router

Endpoints for PLM reports and dashboards.
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ...reports import get_report_service

router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================


class DashboardResponse(BaseModel):
    """Dashboard metrics response."""
    parts: dict[str, int]
    boms: dict[str, int]
    documents: dict[str, int]
    ecos: dict[str, int]
    workflows: dict[str, int]
    activity: dict[str, int]


class BOMCostResponse(BaseModel):
    """BOM cost report response."""
    bom_id: str
    bom_number: str
    total_material_cost: float
    total_labor_cost: float
    total_cost: float
    item_count: int
    items: list[dict] = Field(default_factory=list)


class ECOImpactResponse(BaseModel):
    """ECO impact report response."""
    eco_id: str
    eco_number: str
    affected_parts_count: int
    affected_boms_count: int
    affected_documents_count: int
    affected_parts: list[dict] = Field(default_factory=list)
    affected_boms: list[dict] = Field(default_factory=list)
    affected_documents: list[dict] = Field(default_factory=list)
    estimated_cost_impact: float
    estimated_schedule_impact_days: int
    risk_level: str


class WhereUsedResponse(BaseModel):
    """Where-used report response."""
    part_id: str
    part_number: str
    used_in_boms: list[dict] = Field(default_factory=list)
    used_in_assemblies: list[dict] = Field(default_factory=list)
    total_quantity: float
    usage_count: int


class CycleTimeResponse(BaseModel):
    """ECO cycle time response."""
    average_days: float
    min_days: int
    max_days: int
    by_urgency: dict[str, float]


class UserActivityResponse(BaseModel):
    """User activity summary response."""
    user_id: str
    period_days: int
    parts_created: int
    documents_updated: int
    ecos_submitted: int
    approvals_completed: int


class ProjectSummaryResponse(BaseModel):
    """Project summary response."""
    project_id: str
    total_parts: int
    total_boms: int
    total_documents: int
    open_ecos: int
    completion_percentage: float


# =============================================================================
# Dashboard Endpoints
# =============================================================================


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard():
    """Get PLM dashboard overview metrics."""
    service = get_report_service()
    metrics = service.get_dashboard_metrics()
    return DashboardResponse(**metrics.to_dict())


@router.get("/parts/status-summary")
async def get_parts_by_status():
    """Get part counts grouped by status."""
    service = get_report_service()
    return service.get_parts_by_status()


# =============================================================================
# BOM Reports
# =============================================================================


@router.get("/bom/{bom_id}/cost", response_model=BOMCostResponse)
async def get_bom_cost_report(bom_id: str):
    """Get cost rollup report for a BOM."""
    service = get_report_service()
    report = service.get_bom_cost_report(bom_id)
    return BOMCostResponse(**report.to_dict())


@router.get("/part/{part_id}/where-used", response_model=WhereUsedResponse)
async def get_where_used(part_id: str):
    """Get where-used report showing all BOMs containing a part."""
    service = get_report_service()
    report = service.get_where_used_report(part_id)
    return WhereUsedResponse(**report.to_dict())


# =============================================================================
# ECO Reports
# =============================================================================


@router.get("/eco/{eco_id}/impact", response_model=ECOImpactResponse)
async def get_eco_impact(eco_id: str):
    """Get impact analysis report for an ECO."""
    service = get_report_service()
    report = service.get_eco_impact_report(eco_id)
    return ECOImpactResponse(**report.to_dict())


@router.get("/eco/cycle-time", response_model=CycleTimeResponse)
async def get_eco_cycle_time(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
):
    """Get ECO cycle time statistics."""
    service = get_report_service()
    stats = service.get_eco_cycle_time(from_date, to_date)
    return CycleTimeResponse(**stats)


# =============================================================================
# Document Reports
# =============================================================================


@router.get("/documents/review-metrics")
async def get_document_review_metrics():
    """Get document review metrics."""
    service = get_report_service()
    return service.get_document_review_metrics()


# =============================================================================
# User/Project Reports
# =============================================================================


@router.get("/user/{user_id}/activity", response_model=UserActivityResponse)
async def get_user_activity(
    user_id: str,
    days: int = Query(30, le=365),
):
    """Get activity summary for a user."""
    service = get_report_service()
    summary = service.get_user_activity_summary(user_id, days)
    return UserActivityResponse(**summary)


@router.get("/project/{project_id}/summary", response_model=ProjectSummaryResponse)
async def get_project_summary(project_id: str):
    """Get summary metrics for a project."""
    service = get_report_service()
    summary = service.get_project_summary(project_id)
    return ProjectSummaryResponse(**summary)
