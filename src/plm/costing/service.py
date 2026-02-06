"""
Costing Service

Business logic for cost management and analysis.
"""

from typing import Optional
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from plm.costing.repository import (
    PartCostRepository,
    CostElementRepository,
    CostVarianceRepository,
    ShouldCostRepository,
)
from plm.db.models import (
    PartCostModel,
    CostElementModel,
    CostVarianceModel,
    ShouldCostAnalysisModel,
)


@dataclass
class CostBreakdown:
    """Cost breakdown for a part."""

    part_id: str
    material_cost: Decimal
    labor_cost: Decimal
    overhead_cost: Decimal
    total_cost: Decimal
    margin_percent: Optional[float]
    element_count: int


@dataclass
class CostingStats:
    """Overall costing statistics."""

    parts_with_costs: int
    total_material: Decimal
    total_labor: Decimal
    total_overhead: Decimal
    average_margin: float
    unfavorable_variances: int


class CostingService:
    """Service for cost management."""

    def __init__(self, session: Session):
        self.session = session
        self.costs = PartCostRepository(session)
        self.elements = CostElementRepository(session)
        self.variances = CostVarianceRepository(session)
        self.should_costs = ShouldCostRepository(session)

    def create_part_cost(
        self,
        part_id: str,
        part_number: str = "",
        currency: str = "USD",
    ) -> PartCostModel:
        """Create cost record for a part."""
        return self.costs.create(
            part_id=part_id,
            part_number=part_number,
            currency=currency,
            material_cost=Decimal("0"),
            labor_cost=Decimal("0"),
            overhead_cost=Decimal("0"),
            total_cost=Decimal("0"),
            status="draft",
        )

    def get_part_cost(self, part_id: str) -> Optional[PartCostModel]:
        """Get cost record for a part."""
        return self.costs.get_for_part(part_id)

    def add_cost_element(
        self,
        part_cost_id: str,
        cost_type: str,
        description: str,
        quantity: Decimal = Decimal("1"),
        unit_cost: Decimal = Decimal("0"),
        uom: str = "EA",
    ) -> CostElementModel:
        """Add a cost element to a part cost."""
        from plm.costing.models import CostType as CostTypeEnum
        extended_cost = quantity * unit_cost

        # Convert string to enum if needed
        if isinstance(cost_type, str):
            cost_type_enum = CostTypeEnum(cost_type)
        else:
            cost_type_enum = cost_type

        element = self.elements.create(
            part_cost_id=part_cost_id,
            cost_type=cost_type_enum,
            description=description,
            quantity=quantity,
            unit_cost=unit_cost,
            extended_cost=extended_cost,
            unit_of_measure=uom,
        )

        self.costs.recalculate_totals(part_cost_id)
        return element

    def update_cost_element(
        self,
        element_id: str,
        quantity: Optional[Decimal] = None,
        unit_cost: Optional[Decimal] = None,
    ) -> Optional[CostElementModel]:
        """Update a cost element."""
        element = self.elements.get(element_id)
        if not element:
            return None

        if quantity is not None:
            element.quantity = quantity
        if unit_cost is not None:
            element.unit_cost = unit_cost

        element.extended_cost = element.quantity * element.unit_cost
        self.session.flush()

        self.costs.recalculate_totals(element.part_cost_id)
        return element

    def get_cost_breakdown(self, part_id: str) -> Optional[CostBreakdown]:
        """Get cost breakdown for a part."""
        cost = self.costs.get_for_part(part_id)
        if not cost:
            return None

        elements = self.elements.list_for_cost(cost.id)

        return CostBreakdown(
            part_id=part_id,
            material_cost=cost.material_cost or Decimal("0"),
            labor_cost=cost.labor_cost or Decimal("0"),
            overhead_cost=cost.overhead_cost or Decimal("0"),
            total_cost=cost.total_cost or Decimal("0"),
            margin_percent=cost.margin_percent,
            element_count=len(elements),
        )

    def record_variance(
        self,
        part_id: str,
        part_number: str,
        period: str,
        standard_cost: Decimal,
        actual_cost: Decimal,
        quantity: Decimal = Decimal("1"),
    ) -> CostVarianceModel:
        """Record cost variance."""
        variance = actual_cost - standard_cost
        variance_percent = float(variance / standard_cost * 100) if standard_cost else 0
        favorable = variance <= 0

        return self.variances.create(
            part_id=part_id,
            part_number=part_number,
            period=period,
            standard_cost=standard_cost,
            actual_cost=actual_cost,
            quantity=quantity,
            variance=variance,
            variance_percent=variance_percent,
            favorable=favorable,
        )

    def get_part_variances(
        self,
        part_id: str,
        period: Optional[str] = None,
    ) -> list[CostVarianceModel]:
        """Get variances for a part."""
        return self.variances.list_for_part(part_id, period)

    def get_period_total_variance(self, period: str) -> Decimal:
        """Get total variance for a period."""
        return self.variances.get_total_variance(period)

    def get_unfavorable_variances(
        self,
        period: Optional[str] = None,
    ) -> list[CostVarianceModel]:
        """Get unfavorable variances."""
        return self.variances.list_unfavorable(period)

    def create_should_cost_analysis(
        self,
        part_id: str,
        current_cost: Decimal,
        target_cost: Decimal,
        methodology: str = "bottom_up",
        analyzed_by: Optional[str] = None,
        findings: str = "",
        recommendations: str = "",
    ) -> ShouldCostAnalysisModel:
        """Create should-cost analysis."""
        potential_savings = current_cost - target_cost
        savings_percent = float(potential_savings / current_cost * 100) if current_cost else 0

        return self.should_costs.create(
            part_id=part_id,
            current_cost=current_cost,
            should_cost=target_cost,
            potential_savings=potential_savings,
            savings_percent=savings_percent,
            methodology=methodology,
            analyzed_by=analyzed_by,
            findings=findings,
            recommendations=recommendations,
            status="draft",
        )

    def get_latest_should_cost(
        self,
        part_id: str,
    ) -> Optional[ShouldCostAnalysisModel]:
        """Get most recent should-cost analysis for a part."""
        return self.should_costs.get_latest(part_id)

    def get_savings_opportunities(
        self,
        min_savings_percent: float = 5,
    ) -> list[ShouldCostAnalysisModel]:
        """Get parts with savings opportunities."""
        return self.should_costs.list_with_savings(min_savings_percent)

    def get_stats(self) -> CostingStats:
        """Get overall costing statistics."""
        all_costs = self.costs.list(limit=10000)
        unfavorable = self.variances.list_unfavorable()

        total_material = Decimal("0")
        total_labor = Decimal("0")
        total_overhead = Decimal("0")
        margins = []

        for cost in all_costs:
            total_material += cost.material_cost or Decimal("0")
            total_labor += cost.labor_cost or Decimal("0")
            total_overhead += cost.overhead_cost or Decimal("0")
            if cost.margin_percent is not None:
                margins.append(cost.margin_percent)

        avg_margin = sum(margins) / len(margins) if margins else 0

        return CostingStats(
            parts_with_costs=len(all_costs),
            total_material=total_material,
            total_labor=total_labor,
            total_overhead=total_overhead,
            average_margin=avg_margin,
            unfavorable_variances=len(unfavorable),
        )

    def commit(self):
        """Commit transaction."""
        self.session.commit()
