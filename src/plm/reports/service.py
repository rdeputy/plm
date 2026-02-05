"""
Report Service

Centralized reporting and analytics for PLM data.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional


@dataclass
class DashboardMetrics:
    """PLM dashboard overview metrics."""
    # Parts
    total_parts: int = 0
    parts_in_draft: int = 0
    parts_in_review: int = 0
    parts_released: int = 0
    parts_obsolete: int = 0

    # BOMs
    total_boms: int = 0
    boms_released: int = 0

    # Documents
    total_documents: int = 0
    documents_checked_out: int = 0
    documents_pending_review: int = 0

    # ECOs
    total_ecos: int = 0
    ecos_open: int = 0
    ecos_in_review: int = 0
    ecos_approved_pending: int = 0
    ecos_implemented: int = 0

    # Workflows
    active_workflows: int = 0
    pending_tasks: int = 0
    overdue_tasks: int = 0

    # Recent activity
    changes_today: int = 0
    changes_this_week: int = 0

    def to_dict(self) -> dict:
        return {
            "parts": {
                "total": self.total_parts,
                "draft": self.parts_in_draft,
                "in_review": self.parts_in_review,
                "released": self.parts_released,
                "obsolete": self.parts_obsolete,
            },
            "boms": {
                "total": self.total_boms,
                "released": self.boms_released,
            },
            "documents": {
                "total": self.total_documents,
                "checked_out": self.documents_checked_out,
                "pending_review": self.documents_pending_review,
            },
            "ecos": {
                "total": self.total_ecos,
                "open": self.ecos_open,
                "in_review": self.ecos_in_review,
                "approved_pending": self.ecos_approved_pending,
                "implemented": self.ecos_implemented,
            },
            "workflows": {
                "active": self.active_workflows,
                "pending_tasks": self.pending_tasks,
                "overdue_tasks": self.overdue_tasks,
            },
            "activity": {
                "today": self.changes_today,
                "this_week": self.changes_this_week,
            },
        }


@dataclass
class BOMCostReport:
    """BOM cost rollup report."""
    bom_id: str
    bom_number: str
    total_material_cost: Decimal = Decimal("0")
    total_labor_cost: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    item_count: int = 0
    items: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "bom_id": self.bom_id,
            "bom_number": self.bom_number,
            "total_material_cost": float(self.total_material_cost),
            "total_labor_cost": float(self.total_labor_cost),
            "total_cost": float(self.total_cost),
            "item_count": self.item_count,
            "items": self.items,
        }


@dataclass
class ECOImpactReport:
    """ECO impact analysis report."""
    eco_id: str
    eco_number: str
    affected_parts: list[dict] = field(default_factory=list)
    affected_boms: list[dict] = field(default_factory=list)
    affected_documents: list[dict] = field(default_factory=list)
    estimated_cost_impact: Decimal = Decimal("0")
    estimated_schedule_impact_days: int = 0
    risk_level: str = "low"

    def to_dict(self) -> dict:
        return {
            "eco_id": self.eco_id,
            "eco_number": self.eco_number,
            "affected_parts_count": len(self.affected_parts),
            "affected_boms_count": len(self.affected_boms),
            "affected_documents_count": len(self.affected_documents),
            "affected_parts": self.affected_parts,
            "affected_boms": self.affected_boms,
            "affected_documents": self.affected_documents,
            "estimated_cost_impact": float(self.estimated_cost_impact),
            "estimated_schedule_impact_days": self.estimated_schedule_impact_days,
            "risk_level": self.risk_level,
        }


@dataclass
class WhereUsedReport:
    """Where-used report for a part."""
    part_id: str
    part_number: str
    used_in_boms: list[dict] = field(default_factory=list)
    used_in_assemblies: list[dict] = field(default_factory=list)
    total_quantity: Decimal = Decimal("0")

    def to_dict(self) -> dict:
        return {
            "part_id": self.part_id,
            "part_number": self.part_number,
            "used_in_boms": self.used_in_boms,
            "used_in_assemblies": self.used_in_assemblies,
            "total_quantity": float(self.total_quantity),
            "usage_count": len(self.used_in_boms),
        }


class ReportService:
    """
    Service for generating PLM reports and analytics.
    """

    def __init__(self):
        # Would inject repositories in production
        pass

    def get_dashboard_metrics(self) -> DashboardMetrics:
        """Get overview metrics for PLM dashboard."""
        # In production, query actual database
        # For now, return sample data structure
        return DashboardMetrics(
            total_parts=0,
            parts_in_draft=0,
            parts_in_review=0,
            parts_released=0,
            parts_obsolete=0,
            total_boms=0,
            boms_released=0,
            total_documents=0,
            documents_checked_out=0,
            documents_pending_review=0,
            total_ecos=0,
            ecos_open=0,
            ecos_in_review=0,
            ecos_approved_pending=0,
            ecos_implemented=0,
            active_workflows=0,
            pending_tasks=0,
            overdue_tasks=0,
            changes_today=0,
            changes_this_week=0,
        )

    def get_bom_cost_report(self, bom_id: str) -> BOMCostReport:
        """
        Generate cost rollup report for a BOM.

        Aggregates:
        - Material costs from parts
        - Extended costs (qty * unit cost)
        - Nested BOM costs
        """
        # Would query BOM and calculate costs
        return BOMCostReport(
            bom_id=bom_id,
            bom_number=f"BOM-{bom_id[:8]}",
        )

    def get_eco_impact_report(self, eco_id: str) -> ECOImpactReport:
        """
        Generate impact analysis for an ECO.

        Analyzes:
        - Affected parts
        - Affected BOMs (where parts are used)
        - Affected documents
        - Cost and schedule impact estimates
        """
        # Would query ECO and related data
        return ECOImpactReport(
            eco_id=eco_id,
            eco_number=f"ECO-{eco_id[:8]}",
        )

    def get_where_used_report(self, part_id: str) -> WhereUsedReport:
        """
        Generate where-used report for a part.

        Shows all BOMs and assemblies that use this part.
        """
        # Would query BOM items
        return WhereUsedReport(
            part_id=part_id,
            part_number=f"PART-{part_id[:8]}",
        )

    def get_parts_by_status(self) -> dict[str, int]:
        """Get part counts by status."""
        return {
            "draft": 0,
            "in_review": 0,
            "released": 0,
            "obsolete": 0,
        }

    def get_eco_cycle_time(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Get ECO cycle time statistics.

        Measures time from submission to implementation.
        """
        return {
            "average_days": 0,
            "min_days": 0,
            "max_days": 0,
            "by_urgency": {},
        }

    def get_document_review_metrics(self) -> dict[str, Any]:
        """Get document review metrics."""
        return {
            "avg_review_days": 0,
            "pending_count": 0,
            "approved_this_month": 0,
            "rejected_this_month": 0,
        }

    def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get activity summary for a user."""
        return {
            "user_id": user_id,
            "period_days": days,
            "parts_created": 0,
            "documents_updated": 0,
            "ecos_submitted": 0,
            "approvals_completed": 0,
        }

    def get_project_summary(self, project_id: str) -> dict[str, Any]:
        """Get summary metrics for a project."""
        return {
            "project_id": project_id,
            "total_parts": 0,
            "total_boms": 0,
            "total_documents": 0,
            "open_ecos": 0,
            "completion_percentage": 0,
        }


# Singleton instance
_service: Optional[ReportService] = None


def get_report_service() -> ReportService:
    """Get the singleton report service instance."""
    global _service
    if _service is None:
        _service = ReportService()
    return _service
