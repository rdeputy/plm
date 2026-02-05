"""
Cost Management Models

Target costing, should-cost analysis, and cost tracking.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class CostType(str, Enum):
    """Types of costs."""
    MATERIAL = "material"           # Raw material cost
    LABOR = "labor"                 # Direct labor
    OVERHEAD = "overhead"           # Manufacturing overhead
    TOOLING = "tooling"             # Tooling amortization
    PURCHASED = "purchased"         # Purchased components
    SUBCONTRACT = "subcontract"     # Subcontracted operations
    FREIGHT = "freight"             # Inbound freight
    PACKAGING = "packaging"
    OTHER = "other"


class CostVarianceType(str, Enum):
    """Types of cost variance."""
    MATERIAL_PRICE = "material_price"
    MATERIAL_USAGE = "material_usage"
    LABOR_RATE = "labor_rate"
    LABOR_EFFICIENCY = "labor_efficiency"
    OVERHEAD = "overhead"
    VOLUME = "volume"
    DESIGN_CHANGE = "design_change"
    SCRAP = "scrap"


class CostEstimateStatus(str, Enum):
    """Cost estimate status."""
    DRAFT = "draft"
    PRELIMINARY = "preliminary"
    DETAILED = "detailed"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


@dataclass
class CostElement:
    """
    A single cost element within a cost breakdown.
    """
    id: str
    cost_type: CostType
    description: str = ""

    # Cost values
    unit_cost: Decimal = Decimal("0")
    quantity: Decimal = Decimal("1")
    extended_cost: Decimal = Decimal("0")

    # Basis
    rate: Optional[Decimal] = None      # $/hr, $/lb, etc.
    unit_of_measure: str = "EA"
    basis: str = ""                     # How cost was determined

    # Source
    source: str = ""                    # Quote, catalog, estimate
    vendor_id: Optional[str] = None
    quote_number: Optional[str] = None
    quote_date: Optional[date] = None

    # Variance
    target_cost: Optional[Decimal] = None
    variance: Optional[Decimal] = None
    variance_percent: Optional[float] = None

    def __post_init__(self):
        if self.extended_cost == Decimal("0"):
            self.extended_cost = self.unit_cost * self.quantity

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cost_type": self.cost_type.value,
            "description": self.description,
            "unit_cost": float(self.unit_cost),
            "quantity": float(self.quantity),
            "extended_cost": float(self.extended_cost),
            "target_cost": float(self.target_cost) if self.target_cost else None,
            "variance": float(self.variance) if self.variance else None,
        }


@dataclass
class PartCost:
    """
    Complete cost breakdown for a part.
    """
    id: str
    part_id: str
    part_number: str
    part_revision: str = ""

    # Status
    status: CostEstimateStatus = CostEstimateStatus.DRAFT

    # Cost elements
    elements: list[CostElement] = field(default_factory=list)

    # Summary costs
    material_cost: Decimal = Decimal("0")
    labor_cost: Decimal = Decimal("0")
    overhead_cost: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")

    # Targets
    target_cost: Optional[Decimal] = None
    should_cost: Optional[Decimal] = None  # Analytical should-cost

    # Margin
    selling_price: Optional[Decimal] = None
    margin_percent: Optional[float] = None

    # Lot size basis
    lot_size: int = 1
    annual_volume: Optional[int] = None

    # Currency
    currency: str = "USD"
    exchange_rate: Decimal = Decimal("1")

    # Lifecycle
    effective_date: Optional[date] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None

    notes: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def calculate_totals(self):
        """Recalculate summary totals from elements."""
        self.material_cost = sum(
            e.extended_cost for e in self.elements
            if e.cost_type in [CostType.MATERIAL, CostType.PURCHASED]
        )
        self.labor_cost = sum(
            e.extended_cost for e in self.elements
            if e.cost_type == CostType.LABOR
        )
        self.overhead_cost = sum(
            e.extended_cost for e in self.elements
            if e.cost_type == CostType.OVERHEAD
        )
        self.total_cost = sum(e.extended_cost for e in self.elements)

        if self.selling_price and self.total_cost:
            margin = self.selling_price - self.total_cost
            self.margin_percent = float(margin / self.selling_price * 100)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "part_id": self.part_id,
            "part_number": self.part_number,
            "status": self.status.value,
            "material_cost": float(self.material_cost),
            "labor_cost": float(self.labor_cost),
            "overhead_cost": float(self.overhead_cost),
            "total_cost": float(self.total_cost),
            "target_cost": float(self.target_cost) if self.target_cost else None,
            "should_cost": float(self.should_cost) if self.should_cost else None,
            "margin_percent": self.margin_percent,
            "currency": self.currency,
            "lot_size": self.lot_size,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
        }


@dataclass
class BOMCostRollup:
    """
    Cost rollup for a BOM.
    """
    bom_id: str
    bom_number: str
    part_id: str
    part_number: str

    # Rolled up costs
    material_cost: Decimal = Decimal("0")
    labor_cost: Decimal = Decimal("0")
    overhead_cost: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")

    # Per unit
    unit_cost: Decimal = Decimal("0")
    lot_size: int = 1

    # Breakdown by level
    level_costs: list[dict] = field(default_factory=list)
    component_costs: list[dict] = field(default_factory=list)

    # Missing costs
    parts_without_cost: list[str] = field(default_factory=list)
    coverage_percent: float = 100.0

    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "bom_id": self.bom_id,
            "bom_number": self.bom_number,
            "part_number": self.part_number,
            "material_cost": float(self.material_cost),
            "labor_cost": float(self.labor_cost),
            "overhead_cost": float(self.overhead_cost),
            "total_cost": float(self.total_cost),
            "unit_cost": float(self.unit_cost),
            "lot_size": self.lot_size,
            "coverage_percent": self.coverage_percent,
            "parts_without_cost": self.parts_without_cost,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class CostVariance:
    """
    Cost variance analysis record.
    """
    id: str
    part_id: str
    part_number: str
    period: str                     # "2024-Q1", "2024-01"

    # Costs
    standard_cost: Decimal
    actual_cost: Decimal
    variance: Decimal = Decimal("0")
    variance_percent: float = 0.0

    # Breakdown
    variance_type: CostVarianceType = CostVarianceType.MATERIAL_PRICE
    favorable: bool = True          # True if actual < standard

    # Analysis
    root_cause: str = ""
    corrective_action: str = ""

    # Volume
    quantity: Decimal = Decimal("1")
    total_variance: Decimal = Decimal("0")

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        self.variance = self.actual_cost - self.standard_cost
        self.favorable = self.variance < 0
        if self.standard_cost:
            self.variance_percent = float(self.variance / self.standard_cost * 100)
        self.total_variance = self.variance * self.quantity

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "part_id": self.part_id,
            "part_number": self.part_number,
            "period": self.period,
            "standard_cost": float(self.standard_cost),
            "actual_cost": float(self.actual_cost),
            "variance": float(self.variance),
            "variance_percent": self.variance_percent,
            "variance_type": self.variance_type.value,
            "favorable": self.favorable,
            "total_variance": float(self.total_variance),
        }


@dataclass
class ShouldCostAnalysis:
    """
    Should-cost analysis for a part.

    Analytical breakdown of what a part should cost
    based on material, process, and market data.
    """
    id: str
    part_id: str
    part_number: str

    # Analysis details
    analysis_date: date = field(default_factory=date.today)
    analyst: str = ""
    methodology: str = ""           # "parametric", "bottom-up", "analogous"

    # Calculated should-cost
    should_cost: Decimal = Decimal("0")

    # Breakdown
    raw_material: Decimal = Decimal("0")
    material_processing: Decimal = Decimal("0")
    conversion_cost: Decimal = Decimal("0")
    profit_margin: Decimal = Decimal("0")
    logistics: Decimal = Decimal("0")

    # Comparison
    current_price: Optional[Decimal] = None
    savings_opportunity: Optional[Decimal] = None
    savings_percent: Optional[float] = None

    # Assumptions
    assumptions: list[str] = field(default_factory=list)
    data_sources: list[str] = field(default_factory=list)

    notes: str = ""

    def __post_init__(self):
        if self.current_price and self.should_cost:
            self.savings_opportunity = self.current_price - self.should_cost
            if self.current_price:
                self.savings_percent = float(
                    self.savings_opportunity / self.current_price * 100
                )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "part_id": self.part_id,
            "part_number": self.part_number,
            "analysis_date": self.analysis_date.isoformat(),
            "should_cost": float(self.should_cost),
            "current_price": float(self.current_price) if self.current_price else None,
            "savings_opportunity": float(self.savings_opportunity) if self.savings_opportunity else None,
            "savings_percent": self.savings_percent,
            "methodology": self.methodology,
        }
