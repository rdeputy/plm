"""
Tests for Costing Module

Tests CostElement, PartCost, BOMCostRollup, and related models.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from plm.costing.models import (
    CostElement,
    PartCost,
    BOMCostRollup,
    CostVariance,
    ShouldCostAnalysis,
    CostType,
    CostVarianceType,
    CostEstimateStatus,
)


class TestCostElementModel:
    """Tests for CostElement dataclass model."""

    def test_create_cost_element(self):
        """Test creating a cost element."""
        element = CostElement(
            id=str(uuid4()),
            cost_type=CostType.MATERIAL,
            description="Steel plate",
            unit_cost=Decimal("50.00"),
            quantity=Decimal("2"),
        )
        assert element.cost_type == CostType.MATERIAL
        assert element.unit_cost == Decimal("50.00")
        assert element.extended_cost == Decimal("100.00")  # 50 * 2

    def test_cost_element_to_dict(self):
        """Test converting cost element to dictionary."""
        element = CostElement(
            id="ce-001",
            cost_type=CostType.LABOR,
            description="Assembly labor",
            unit_cost=Decimal("25.00"),
            quantity=Decimal("4"),
            rate=Decimal("25.00"),
            unit_of_measure="HR",
        )
        data = element.to_dict()
        assert data["cost_type"] == "labor"
        assert data["unit_cost"] == 25.00
        assert data["quantity"] == 4.0
        assert data["extended_cost"] == 100.00

    def test_cost_type_enums(self):
        """Test cost type enums."""
        assert CostType.MATERIAL.value == "material"
        assert CostType.LABOR.value == "labor"
        assert CostType.OVERHEAD.value == "overhead"
        assert CostType.TOOLING.value == "tooling"
        assert CostType.PURCHASED.value == "purchased"
        assert CostType.SUBCONTRACT.value == "subcontract"


class TestPartCostModel:
    """Tests for PartCost dataclass model."""

    def test_create_part_cost(self):
        """Test creating a part cost."""
        cost = PartCost(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            status=CostEstimateStatus.DETAILED,
            material_cost=Decimal("100.00"),
            labor_cost=Decimal("50.00"),
            overhead_cost=Decimal("25.00"),
            total_cost=Decimal("175.00"),
        )
        assert cost.total_cost == Decimal("175.00")
        assert cost.status == CostEstimateStatus.DETAILED

    def test_part_cost_calculate_totals(self):
        """Test calculating totals from elements."""
        cost = PartCost(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            elements=[
                CostElement(
                    id="e1",
                    cost_type=CostType.MATERIAL,
                    unit_cost=Decimal("100"),
                    quantity=Decimal("1"),
                ),
                CostElement(
                    id="e2",
                    cost_type=CostType.LABOR,
                    unit_cost=Decimal("25"),
                    quantity=Decimal("2"),
                ),
                CostElement(
                    id="e3",
                    cost_type=CostType.OVERHEAD,
                    unit_cost=Decimal("15"),
                    quantity=Decimal("1"),
                ),
            ],
        )
        cost.calculate_totals()
        assert cost.material_cost == Decimal("100")
        assert cost.labor_cost == Decimal("50")
        assert cost.overhead_cost == Decimal("15")
        assert cost.total_cost == Decimal("165")

    def test_part_cost_margin_calculation(self):
        """Test margin percentage calculation."""
        cost = PartCost(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            total_cost=Decimal("80.00"),
            selling_price=Decimal("100.00"),
            elements=[
                CostElement(
                    id="e1",
                    cost_type=CostType.MATERIAL,
                    unit_cost=Decimal("80"),
                    quantity=Decimal("1"),
                ),
            ],
        )
        cost.calculate_totals()
        assert cost.margin_percent == 20.0  # (100 - 80) / 100 * 100

    def test_cost_estimate_status_enums(self):
        """Test cost estimate status enums."""
        assert CostEstimateStatus.DRAFT.value == "draft"
        assert CostEstimateStatus.PRELIMINARY.value == "preliminary"
        assert CostEstimateStatus.DETAILED.value == "detailed"
        assert CostEstimateStatus.APPROVED.value == "approved"

    def test_part_cost_to_dict(self):
        """Test converting part cost to dictionary."""
        cost = PartCost(
            id="pc-001",
            part_id="part-001",
            part_number="PART-12345",
            status=CostEstimateStatus.APPROVED,
            material_cost=Decimal("100.00"),
            labor_cost=Decimal("50.00"),
            overhead_cost=Decimal("25.00"),
            total_cost=Decimal("175.00"),
            target_cost=Decimal("180.00"),
            lot_size=100,
        )
        data = cost.to_dict()
        assert data["part_number"] == "PART-12345"
        assert data["status"] == "approved"
        assert data["total_cost"] == 175.00
        assert data["target_cost"] == 180.00
        assert data["lot_size"] == 100


class TestBOMCostRollup:
    """Tests for BOMCostRollup model."""

    def test_create_bom_cost_rollup(self):
        """Test creating a BOM cost rollup."""
        rollup = BOMCostRollup(
            bom_id="bom-001",
            bom_number="BOM-12345",
            part_id="part-001",
            part_number="PART-12345",
            material_cost=Decimal("500.00"),
            labor_cost=Decimal("200.00"),
            overhead_cost=Decimal("100.00"),
            total_cost=Decimal("800.00"),
            unit_cost=Decimal("8.00"),
            lot_size=100,
        )
        assert rollup.total_cost == Decimal("800.00")
        assert rollup.unit_cost == Decimal("8.00")

    def test_bom_cost_rollup_to_dict(self):
        """Test converting BOM cost rollup to dictionary."""
        rollup = BOMCostRollup(
            bom_id="bom-001",
            bom_number="BOM-12345",
            part_id="part-001",
            part_number="PART-12345",
            total_cost=Decimal("800.00"),
            coverage_percent=95.0,
            parts_without_cost=["PART-99999"],
        )
        data = rollup.to_dict()
        assert data["bom_number"] == "BOM-12345"
        assert data["total_cost"] == 800.00
        assert data["coverage_percent"] == 95.0
        assert len(data["parts_without_cost"]) == 1


class TestCostVariance:
    """Tests for CostVariance model."""

    def test_create_cost_variance(self):
        """Test creating a cost variance."""
        variance = CostVariance(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            period="2024-Q1",
            standard_cost=Decimal("100.00"),
            actual_cost=Decimal("95.00"),
            variance_type=CostVarianceType.MATERIAL_PRICE,
            quantity=Decimal("100"),
        )
        assert variance.variance == Decimal("-5.00")  # Favorable
        assert variance.favorable is True
        assert variance.total_variance == Decimal("-500.00")

    def test_unfavorable_variance(self):
        """Test unfavorable cost variance."""
        variance = CostVariance(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            period="2024-Q1",
            standard_cost=Decimal("100.00"),
            actual_cost=Decimal("110.00"),
        )
        assert variance.variance == Decimal("10.00")
        assert variance.favorable is False
        assert variance.variance_percent == 10.0

    def test_cost_variance_type_enums(self):
        """Test cost variance type enums."""
        assert CostVarianceType.MATERIAL_PRICE.value == "material_price"
        assert CostVarianceType.MATERIAL_USAGE.value == "material_usage"
        assert CostVarianceType.LABOR_RATE.value == "labor_rate"
        assert CostVarianceType.LABOR_EFFICIENCY.value == "labor_efficiency"
        assert CostVarianceType.DESIGN_CHANGE.value == "design_change"

    def test_cost_variance_to_dict(self):
        """Test converting cost variance to dictionary."""
        variance = CostVariance(
            id="cv-001",
            part_id="part-001",
            part_number="PART-12345",
            period="2024-Q1",
            standard_cost=Decimal("100.00"),
            actual_cost=Decimal("95.00"),
            variance_type=CostVarianceType.MATERIAL_PRICE,
        )
        data = variance.to_dict()
        assert data["period"] == "2024-Q1"
        assert data["standard_cost"] == 100.00
        assert data["actual_cost"] == 95.00
        assert data["variance"] == -5.00
        assert data["favorable"] is True


class TestShouldCostAnalysis:
    """Tests for ShouldCostAnalysis model."""

    def test_create_should_cost_analysis(self):
        """Test creating a should-cost analysis."""
        analysis = ShouldCostAnalysis(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            should_cost=Decimal("80.00"),
            current_price=Decimal("100.00"),
            methodology="bottom-up",
        )
        assert analysis.should_cost == Decimal("80.00")
        assert analysis.savings_opportunity == Decimal("20.00")
        assert analysis.savings_percent == 20.0

    def test_should_cost_to_dict(self):
        """Test converting should-cost analysis to dictionary."""
        analysis = ShouldCostAnalysis(
            id="sca-001",
            part_id="part-001",
            part_number="PART-12345",
            should_cost=Decimal("75.00"),
            current_price=Decimal("100.00"),
            raw_material=Decimal("40.00"),
            conversion_cost=Decimal("25.00"),
            profit_margin=Decimal("10.00"),
            methodology="parametric",
        )
        data = analysis.to_dict()
        assert data["should_cost"] == 75.00
        assert data["current_price"] == 100.00
        assert data["savings_opportunity"] == 25.00
        assert data["savings_percent"] == 25.0
        assert data["methodology"] == "parametric"
