"""
Tests for Parts Module

Tests Part model, dataclass, and database operations.
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from plm.parts.models import Part, PartType, PartStatus, UnitOfMeasure
from plm.db.models import PartModel


class TestPartModel:
    """Tests for Part dataclass model."""

    def test_create_part(self, sample_part):
        """Test creating a part."""
        assert sample_part.part_number == "LUMBER-2X4-8FT"
        assert sample_part.revision == "A"
        assert sample_part.part_type == PartType.RAW_MATERIAL
        assert sample_part.status == PartStatus.RELEASED
        assert sample_part.unit_cost == Decimal("8.99")

    def test_part_to_dict(self, sample_part):
        """Test converting part to dictionary."""
        data = sample_part.to_dict()
        assert data["part_number"] == "LUMBER-2X4-8FT"
        assert data["part_type"] == "raw_material"
        assert data["status"] == "released"
        assert data["unit_cost"] == 8.99  # float, not string

    def test_part_enums(self):
        """Test part type and status enums."""
        assert PartType.RAW_MATERIAL.value == "raw_material"
        assert PartType.COMPONENT.value == "component"
        assert PartType.ASSEMBLY.value == "assembly"
        assert PartType.PRODUCT.value == "product"

        assert PartStatus.DRAFT.value == "draft"
        assert PartStatus.RELEASED.value == "released"
        assert PartStatus.OBSOLETE.value == "obsolete"

    def test_unit_of_measure_enums(self):
        """Test unit of measure enums."""
        assert UnitOfMeasure.EACH.value == "EA"
        assert UnitOfMeasure.LINEAR_FEET.value == "LF"
        assert UnitOfMeasure.SQUARE_FEET.value == "SF"
        assert UnitOfMeasure.BOARD_FEET.value == "BF"


class TestPartDatabase:
    """Tests for Part database operations."""

    def test_persist_part(self, session, sample_part_model):
        """Test persisting a part to database."""
        found = session.query(PartModel).filter_by(id=sample_part_model.id).first()
        assert found is not None
        assert found.part_number == "LUMBER-2X4-8FT"
        assert found.status == PartStatus.RELEASED

    def test_query_parts_by_status(self, session, multiple_parts):
        """Test querying parts by status."""
        released = (
            session.query(PartModel).filter_by(status=PartStatus.RELEASED).all()
        )
        draft = session.query(PartModel).filter_by(status=PartStatus.DRAFT).all()

        assert len(released) == 2
        assert len(draft) == 1

    def test_query_parts_by_type(self, session, multiple_parts):
        """Test querying parts by type."""
        raw_materials = (
            session.query(PartModel).filter_by(part_type=PartType.RAW_MATERIAL).all()
        )
        assemblies = (
            session.query(PartModel).filter_by(part_type=PartType.ASSEMBLY).all()
        )

        assert len(raw_materials) == 2
        assert len(assemblies) == 1

    def test_update_part(self, session, sample_part_model):
        """Test updating a part."""
        sample_part_model.status = PartStatus.OBSOLETE
        sample_part_model.obsoleted_by = "test_user"
        session.commit()

        found = session.query(PartModel).filter_by(id=sample_part_model.id).first()
        assert found.status == PartStatus.OBSOLETE
        assert found.obsoleted_by == "test_user"

    def test_delete_part(self, session, sample_part_model):
        """Test deleting a part."""
        part_id = sample_part_model.id
        session.delete(sample_part_model)
        session.commit()

        found = session.query(PartModel).filter_by(id=part_id).first()
        assert found is None

    def test_part_with_attributes(self, session):
        """Test part with JSON attributes."""
        part = PartModel(
            id=str(uuid4()),
            part_number="SPECIAL-001",
            revision="A",
            name="Special Part",
            part_type=PartType.COMPONENT,
            status=PartStatus.DRAFT,
            unit_of_measure=UnitOfMeasure.EACH,
            attributes={"color": "blue", "weight_lbs": 5.5},
            tags=["special", "custom"],
        )
        session.add(part)
        session.commit()

        found = session.query(PartModel).filter_by(part_number="SPECIAL-001").first()
        assert found.attributes["color"] == "blue"
        assert "special" in found.tags


class TestPartRevision:
    """Tests for part revision handling."""

    def test_create_revision(self, session, sample_part_model):
        """Test creating a new part revision."""
        # Create revision B
        new_revision = PartModel(
            id=str(uuid4()),
            part_number=sample_part_model.part_number,
            revision="B",
            name=sample_part_model.name + " (Updated)",
            part_type=sample_part_model.part_type,
            status=PartStatus.DRAFT,
            unit_of_measure=sample_part_model.unit_of_measure,
            unit_cost=Decimal("9.49"),  # Price increase
        )
        session.add(new_revision)
        session.commit()

        # Query all revisions
        revisions = (
            session.query(PartModel)
            .filter_by(part_number="LUMBER-2X4-8FT")
            .order_by(PartModel.revision)
            .all()
        )

        assert len(revisions) == 2
        assert revisions[0].revision == "A"
        assert revisions[1].revision == "B"
        assert revisions[1].unit_cost == Decimal("9.49")
