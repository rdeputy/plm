"""
Test Configuration and Fixtures

Provides database fixtures and test data for PLM tests.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from plm.db.base import Base
from plm.db.models import (
    PartModel,
    BOMModel,
    BOMItemModel,
    ChangeOrderModel,
)
from plm.parts.models import Part, PartType, PartStatus, UnitOfMeasure
from plm.boms.models import BOM, BOMItem, BOMType, Effectivity


@pytest.fixture(scope="function")
def engine():
    """Create a fresh in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def session(engine):
    """Create a new database session for each test."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# =============================================================================
# Part Fixtures
# =============================================================================


@pytest.fixture
def sample_part() -> Part:
    """Create a sample part."""
    return Part(
        id=str(uuid4()),
        part_number="LUMBER-2X4-8FT",
        revision="A",
        name="2x4x8 Lumber",
        description="Dimensional lumber, 2x4x8 feet, SPF #2",
        part_type=PartType.RAW_MATERIAL,
        status=PartStatus.RELEASED,
        category="06 - Wood",
        csi_code="06 11 00",
        unit_of_measure=UnitOfMeasure.EACH,
        unit_cost=Decimal("8.99"),
        manufacturer="Generic",
        lead_time_days=3,
        created_by="test",
    )


@pytest.fixture
def sample_part_model(session, sample_part) -> PartModel:
    """Create and persist a sample part model."""
    model = PartModel(
        id=sample_part.id,
        part_number=sample_part.part_number,
        revision=sample_part.revision,
        name=sample_part.name,
        description=sample_part.description,
        part_type=sample_part.part_type,
        status=sample_part.status,
        category=sample_part.category,
        csi_code=sample_part.csi_code,
        unit_of_measure=sample_part.unit_of_measure,
        unit_cost=sample_part.unit_cost,
        manufacturer=sample_part.manufacturer,
        lead_time_days=sample_part.lead_time_days,
        created_by=sample_part.created_by,
    )
    session.add(model)
    session.commit()
    return model


@pytest.fixture
def multiple_parts(session) -> list[PartModel]:
    """Create multiple parts for testing."""
    parts = [
        PartModel(
            id=str(uuid4()),
            part_number="LUMBER-2X4-8FT",
            revision="A",
            name="2x4x8 Lumber",
            part_type=PartType.RAW_MATERIAL,
            status=PartStatus.RELEASED,
            category="06 - Wood",
            unit_of_measure=UnitOfMeasure.EACH,
            unit_cost=Decimal("8.99"),
        ),
        PartModel(
            id=str(uuid4()),
            part_number="NAIL-16D-BOX",
            revision="A",
            name="16d Framing Nails (Box)",
            part_type=PartType.RAW_MATERIAL,
            status=PartStatus.RELEASED,
            category="05 - Metals",
            unit_of_measure=UnitOfMeasure.EACH,
            unit_cost=Decimal("45.00"),
        ),
        PartModel(
            id=str(uuid4()),
            part_number="WALL-ASSY-EXT-8FT",
            revision="A",
            name="Exterior Wall Assembly 8ft",
            part_type=PartType.ASSEMBLY,
            status=PartStatus.DRAFT,
            category="06 - Wood",
            unit_of_measure=UnitOfMeasure.LINEAR_FEET,
        ),
    ]
    session.add_all(parts)
    session.commit()
    return parts


# =============================================================================
# BOM Fixtures
# =============================================================================


@pytest.fixture
def sample_bom(multiple_parts, session) -> BOMModel:
    """Create a sample BOM with items."""
    assembly = multiple_parts[2]  # Wall assembly
    lumber = multiple_parts[0]
    nails = multiple_parts[1]

    bom = BOMModel(
        id=str(uuid4()),
        bom_number="BOM-WALL-EXT-001",
        revision="A",
        name="8ft Exterior Wall BOM",
        description="Bill of materials for 8ft exterior wall section",
        parent_part_id=assembly.id,
        parent_part_revision="A",
        bom_type=BOMType.ENGINEERING,
        effectivity=Effectivity.AS_DESIGNED,
        status=PartStatus.DRAFT,
        created_by="test",
    )
    session.add(bom)
    session.flush()

    items = [
        BOMItemModel(
            id=str(uuid4()),
            bom_id=bom.id,
            part_id=lumber.id,
            part_number=lumber.part_number,
            part_revision="A",
            quantity=Decimal("12"),
            unit_of_measure=UnitOfMeasure.EACH,
            find_number=10,
            reference_designator="STUD-01-12",
        ),
        BOMItemModel(
            id=str(uuid4()),
            bom_id=bom.id,
            part_id=nails.id,
            part_number=nails.part_number,
            part_revision="A",
            quantity=Decimal("0.5"),
            unit_of_measure=UnitOfMeasure.EACH,
            find_number=20,
            reference_designator="FASTENER-01",
        ),
    ]
    session.add_all(items)
    session.commit()

    return bom
