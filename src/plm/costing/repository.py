"""
Costing Repository

Database operations for costs, variances, and should-cost analyses.
"""

from typing import Optional
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from plm.db.repository import BaseRepository
from plm.db.models import (
    PartCostModel,
    CostElementModel,
    CostVarianceModel,
    ShouldCostAnalysisModel,
)


class PartCostRepository(BaseRepository[PartCostModel]):
    """Repository for part costs."""

    def __init__(self, session: Session):
        super().__init__(session, PartCostModel)

    def get_for_part(self, part_id: str) -> Optional[PartCostModel]:
        """Get cost record for a part."""
        return self.get_by(part_id=part_id)

    def list_by_status(self, status: str) -> list[PartCostModel]:
        """List costs by status."""
        return self.list(status=status)

    def recalculate_totals(self, part_cost_id: str) -> Optional[PartCostModel]:
        """Recalculate cost totals from elements."""
        cost = self.get(part_cost_id)
        if not cost:
            return None

        elements = self.session.execute(
            select(CostElementModel).filter(CostElementModel.part_cost_id == part_cost_id)
        ).scalars().all()

        material = Decimal("0")
        labor = Decimal("0")
        overhead = Decimal("0")
        total = Decimal("0")

        for e in elements:
            total += e.extended_cost or Decimal("0")
            if e.cost_type in ("material", "purchased"):
                material += e.extended_cost or Decimal("0")
            elif e.cost_type == "labor":
                labor += e.extended_cost or Decimal("0")
            elif e.cost_type == "overhead":
                overhead += e.extended_cost or Decimal("0")

        cost.material_cost = material
        cost.labor_cost = labor
        cost.overhead_cost = overhead
        cost.total_cost = total

        if cost.selling_price and cost.total_cost:
            margin = cost.selling_price - cost.total_cost
            cost.margin_percent = float(margin / cost.selling_price * 100)

        return cost


class CostElementRepository(BaseRepository[CostElementModel]):
    """Repository for cost elements."""

    def __init__(self, session: Session):
        super().__init__(session, CostElementModel)

    def list_for_cost(self, part_cost_id: str) -> list[CostElementModel]:
        """List elements for a cost record."""
        return self.list(part_cost_id=part_cost_id)

    def list_by_type(
        self,
        part_cost_id: str,
        cost_type: str,
    ) -> list[CostElementModel]:
        """List elements by type."""
        return self.list(part_cost_id=part_cost_id, cost_type=cost_type)


class CostVarianceRepository(BaseRepository[CostVarianceModel]):
    """Repository for cost variances."""

    def __init__(self, session: Session):
        super().__init__(session, CostVarianceModel)

    def list_for_part(
        self,
        part_id: str,
        period: Optional[str] = None,
    ) -> list[CostVarianceModel]:
        """List variances for a part."""
        return self.list(part_id=part_id, period=period, order_by="period")

    def list_unfavorable(self, period: Optional[str] = None) -> list[CostVarianceModel]:
        """List unfavorable variances."""
        return self.list(favorable=False, period=period)

    def get_total_variance(self, period: str) -> Decimal:
        """Get total variance for a period."""
        stmt = select(func.sum(CostVarianceModel.total_variance)).filter(
            CostVarianceModel.period == period
        )
        result = self.session.execute(stmt).scalar()
        return result or Decimal("0")


class ShouldCostRepository(BaseRepository[ShouldCostAnalysisModel]):
    """Repository for should-cost analyses."""

    def __init__(self, session: Session):
        super().__init__(session, ShouldCostAnalysisModel)

    def list_for_part(self, part_id: str) -> list[ShouldCostAnalysisModel]:
        """List analyses for a part."""
        return self.list(part_id=part_id, order_by="analysis_date")

    def get_latest(self, part_id: str) -> Optional[ShouldCostAnalysisModel]:
        """Get most recent analysis for a part."""
        stmt = (
            select(self.model_class)
            .filter(ShouldCostAnalysisModel.part_id == part_id)
            .order_by(ShouldCostAnalysisModel.analysis_date.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_with_savings(
        self,
        min_savings_percent: float = 0,
    ) -> list[ShouldCostAnalysisModel]:
        """List analyses with savings opportunities."""
        stmt = select(self.model_class).filter(
            ShouldCostAnalysisModel.savings_percent.isnot(None),
            ShouldCostAnalysisModel.savings_percent >= min_savings_percent,
        ).order_by(ShouldCostAnalysisModel.savings_percent.desc())
        return list(self.session.execute(stmt).scalars().all())
