"""
Tests for BOM Module

Tests Bill of Materials model and database operations.
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from plm.boms.models import BOM, BOMItem, BOMType, Effectivity
from plm.parts.models import PartStatus, UnitOfMeasure
from plm.db.models import BOMModel, BOMItemModel, PartModel


class TestBOMModel:
    """Tests for BOM dataclass model."""

    def test_create_bom(self):
        """Test creating a BOM."""
        bom = BOM(
            id=str(uuid4()),
            bom_number="BOM-TEST-001",
            revision="A",
            name="Test BOM",
            bom_type=BOMType.ENGINEERING,
            effectivity=Effectivity.AS_DESIGNED,
        )
        assert bom.bom_number == "BOM-TEST-001"
        assert bom.bom_type == BOMType.ENGINEERING
        assert bom.effectivity == Effectivity.AS_DESIGNED

    def test_bom_to_dict(self):
        """Test converting BOM to dictionary."""
        bom = BOM(
            id="test-id",
            bom_number="BOM-TEST-001",
            revision="A",
            name="Test BOM",
            bom_type=BOMType.MANUFACTURING,
            effectivity=Effectivity.AS_BUILT,
        )
        data = bom.to_dict()
        assert data["bom_number"] == "BOM-TEST-001"
        assert data["bom_type"] == "manufacturing"
        assert data["effectivity"] == "as_built"

    def test_bom_item_to_dict(self):
        """Test converting BOM item to dictionary."""
        item = BOMItem(
            id="item-id",
            bom_id="bom-id",
            part_id="part-id",
            part_number="PART-001",
            part_revision="A",
            quantity=Decimal("5"),
            find_number=10,
            reference_designator="REF-01",
        )
        data = item.to_dict()
        # quantity might be float or string depending on to_dict impl
        assert float(data["quantity"]) == 5.0
        assert data["find_number"] == 10


class TestBOMDatabase:
    """Tests for BOM database operations."""

    def test_persist_bom(self, session, sample_bom):
        """Test persisting a BOM to database."""
        found = session.query(BOMModel).filter_by(id=sample_bom.id).first()
        assert found is not None
        assert found.bom_number == "BOM-WALL-EXT-001"

    def test_bom_items(self, session, sample_bom):
        """Test retrieving BOM items."""
        items = session.query(BOMItemModel).filter_by(bom_id=sample_bom.id).all()
        assert len(items) == 2

        # Check quantities
        lumber_item = next(i for i in items if i.part_number == "LUMBER-2X4-8FT")
        assert lumber_item.quantity == Decimal("12")

    def test_bom_cost_rollup(self, session, sample_bom):
        """Test calculating total BOM cost."""
        items = session.query(BOMItemModel).filter_by(bom_id=sample_bom.id).all()

        total_cost = Decimal("0")
        for item in items:
            part = session.query(PartModel).filter_by(id=item.part_id).first()
            if part and part.unit_cost:
                total_cost += item.quantity * part.unit_cost

        # 12 * 8.99 + 0.5 * 45.00 = 107.88 + 22.50 = 130.38
        assert total_cost == Decimal("130.38")

    def test_add_bom_item(self, session, sample_bom, multiple_parts):
        """Test adding an item to a BOM."""
        new_item = BOMItemModel(
            id=str(uuid4()),
            bom_id=sample_bom.id,
            part_id=multiple_parts[0].id,
            part_number=multiple_parts[0].part_number,
            part_revision="A",
            quantity=Decimal("2"),
            unit_of_measure=UnitOfMeasure.EACH,
            find_number=30,
            reference_designator="PLATE-01-02",
        )
        session.add(new_item)
        session.commit()

        items = session.query(BOMItemModel).filter_by(bom_id=sample_bom.id).all()
        assert len(items) == 3

    def test_remove_bom_item(self, session, sample_bom):
        """Test removing an item from a BOM."""
        items = session.query(BOMItemModel).filter_by(bom_id=sample_bom.id).all()
        session.delete(items[0])
        session.commit()

        remaining = session.query(BOMItemModel).filter_by(bom_id=sample_bom.id).all()
        assert len(remaining) == 1

    def test_bom_effectivity(self, session, sample_bom):
        """Test BOM effectivity states."""
        # Create multiple BOM versions with different effectivities
        as_approved = BOMModel(
            id=str(uuid4()),
            bom_number=sample_bom.bom_number,
            revision="B",
            name=sample_bom.name,
            parent_part_id=sample_bom.parent_part_id,
            parent_part_revision="A",
            bom_type=BOMType.ENGINEERING,
            effectivity=Effectivity.AS_APPROVED,
            status=PartStatus.RELEASED,
        )
        session.add(as_approved)
        session.commit()

        # Query by effectivity
        designed = (
            session.query(BOMModel)
            .filter_by(effectivity=Effectivity.AS_DESIGNED)
            .all()
        )
        approved = (
            session.query(BOMModel)
            .filter_by(effectivity=Effectivity.AS_APPROVED)
            .all()
        )

        assert len(designed) == 1
        assert len(approved) == 1


class TestBOMHierarchy:
    """Tests for multi-level BOM structures."""

    def test_nested_bom(self, session, multiple_parts):
        """Test creating nested BOMs (sub-assemblies)."""
        # Create sub-assembly BOM
        sub_assy = multiple_parts[2]  # Wall assembly

        sub_bom = BOMModel(
            id=str(uuid4()),
            bom_number="BOM-SUB-001",
            revision="A",
            name="Sub-Assembly BOM",
            parent_part_id=sub_assy.id,
            parent_part_revision="A",
            bom_type=BOMType.ENGINEERING,
            status=PartStatus.RELEASED,
        )
        session.add(sub_bom)
        session.flush()

        # Add items to sub-BOM
        sub_item = BOMItemModel(
            id=str(uuid4()),
            bom_id=sub_bom.id,
            part_id=multiple_parts[0].id,
            part_number=multiple_parts[0].part_number,
            part_revision="A",
            quantity=Decimal("4"),
            has_sub_bom=False,
        )
        session.add(sub_item)

        # Create parent BOM that includes sub-assembly
        parent_bom = BOMModel(
            id=str(uuid4()),
            bom_number="BOM-PARENT-001",
            revision="A",
            name="Parent Product BOM",
            parent_part_id="",
            parent_part_revision="",
            bom_type=BOMType.ENGINEERING,
            status=PartStatus.DRAFT,
        )
        session.add(parent_bom)
        session.flush()

        # Add sub-assembly to parent
        parent_item = BOMItemModel(
            id=str(uuid4()),
            bom_id=parent_bom.id,
            part_id=sub_assy.id,
            part_number=sub_assy.part_number,
            part_revision="A",
            quantity=Decimal("4"),  # 4 wall sections
            has_sub_bom=True,  # Indicates this part has its own BOM
        )
        session.add(parent_item)
        session.commit()

        # Verify structure
        parent_items = (
            session.query(BOMItemModel).filter_by(bom_id=parent_bom.id).all()
        )
        assert len(parent_items) == 1
        assert parent_items[0].has_sub_bom is True
