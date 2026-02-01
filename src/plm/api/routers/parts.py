"""
Parts API Router

CRUD operations for parts and revisions.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from plm.api.deps import get_db_session
from plm.db.models import PartModel, PartRevisionModel
from plm.parts.models import PartType, PartStatus

router = APIRouter()


# ----- Pydantic Schemas -----


class PartCreate(BaseModel):
    """Schema for creating a part."""

    part_number: str
    revision: str = "A"
    name: str
    description: Optional[str] = None
    part_type: str = "component"
    category: Optional[str] = None
    csi_code: Optional[str] = None
    uniformat_code: Optional[str] = None
    unit_of_measure: str = "EA"
    unit_cost: Optional[float] = None
    manufacturer: Optional[str] = None
    manufacturer_pn: Optional[str] = None
    lead_time_days: Optional[int] = None


class PartUpdate(BaseModel):
    """Schema for updating a part."""

    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    csi_code: Optional[str] = None
    uniformat_code: Optional[str] = None
    unit_cost: Optional[float] = None
    manufacturer: Optional[str] = None
    manufacturer_pn: Optional[str] = None
    lead_time_days: Optional[int] = None


class PartResponse(BaseModel):
    """Schema for part response."""

    id: str
    part_number: str
    revision: str
    name: str
    description: Optional[str]
    part_type: str
    status: str
    category: Optional[str]
    csi_code: Optional[str]
    uniformat_code: Optional[str]
    unit_of_measure: str
    unit_cost: Optional[float]
    manufacturer: Optional[str]
    manufacturer_pn: Optional[str]
    lead_time_days: Optional[int]

    class Config:
        from_attributes = True


# ----- Endpoints -----


@router.get("", response_model=list[PartResponse])
async def list_parts(
    part_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
):
    """List parts with optional filters."""
    query = db.query(PartModel)

    if part_type:
        query = query.filter(PartModel.part_type == part_type)
    if status:
        query = query.filter(PartModel.status == status)
    if category:
        query = query.filter(PartModel.category == category)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (PartModel.part_number.ilike(search_term))
            | (PartModel.name.ilike(search_term))
        )

    parts = query.offset(offset).limit(limit).all()
    return [_part_to_response(p) for p in parts]


@router.post("", response_model=PartResponse, status_code=201)
async def create_part(
    part: PartCreate,
    db: Session = Depends(get_db_session),
):
    """Create a new part."""
    # Check for existing part number
    existing = (
        db.query(PartModel)
        .filter(PartModel.part_number == part.part_number)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Part number {part.part_number} already exists",
        )

    from uuid import uuid4
    from datetime import datetime
    from decimal import Decimal

    model = PartModel(
        id=str(uuid4()),
        part_number=part.part_number,
        revision=part.revision,
        name=part.name,
        description=part.description,
        part_type=part.part_type,
        status=PartStatus.DRAFT.value,
        category=part.category,
        csi_code=part.csi_code,
        uniformat_code=part.uniformat_code,
        unit_of_measure=part.unit_of_measure,
        unit_cost=Decimal(str(part.unit_cost)) if part.unit_cost else None,
        manufacturer=part.manufacturer,
        manufacturer_pn=part.manufacturer_pn,
        lead_time_days=part.lead_time_days,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    return _part_to_response(model)


@router.get("/{part_id}", response_model=PartResponse)
async def get_part(
    part_id: str,
    db: Session = Depends(get_db_session),
):
    """Get a part by ID."""
    part = db.query(PartModel).filter(PartModel.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    return _part_to_response(part)


@router.patch("/{part_id}", response_model=PartResponse)
async def update_part(
    part_id: str,
    updates: PartUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a part."""
    part = db.query(PartModel).filter(PartModel.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    if part.status == PartStatus.RELEASED.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot modify released part - create new revision",
        )

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(part, field, value)

    db.commit()
    db.refresh(part)

    return _part_to_response(part)


@router.post("/{part_id}/release", response_model=PartResponse)
async def release_part(
    part_id: str,
    released_by: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Release a part for use."""
    part = db.query(PartModel).filter(PartModel.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    if part.status not in [PartStatus.DRAFT.value, PartStatus.IN_REVIEW.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot release part in status {part.status}",
        )

    from datetime import datetime

    part.status = PartStatus.RELEASED.value
    part.released_by = released_by
    part.released_at = datetime.now()

    db.commit()
    db.refresh(part)

    return _part_to_response(part)


@router.post("/{part_id}/revise", response_model=PartResponse)
async def create_revision(
    part_id: str,
    created_by: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Create a new revision of a released part."""
    part = db.query(PartModel).filter(PartModel.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    if part.status != PartStatus.RELEASED.value:
        raise HTTPException(
            status_code=400,
            detail="Can only revise released parts",
        )

    from uuid import uuid4
    from datetime import datetime
    from plm.parts.models import increment_revision

    new_revision = increment_revision(part.revision)

    new_part = PartModel(
        id=str(uuid4()),
        part_number=part.part_number,
        revision=new_revision,
        name=part.name,
        description=part.description,
        part_type=part.part_type,
        status=PartStatus.DRAFT.value,
        category=part.category,
        csi_code=part.csi_code,
        uniformat_code=part.uniformat_code,
        unit_of_measure=part.unit_of_measure,
        unit_cost=part.unit_cost,
        manufacturer=part.manufacturer,
        manufacturer_pn=part.manufacturer_pn,
        lead_time_days=part.lead_time_days,
        created_by=created_by,
        created_at=datetime.now(),
    )
    db.add(new_part)
    db.commit()
    db.refresh(new_part)

    return _part_to_response(new_part)


def _part_to_response(model: PartModel) -> PartResponse:
    """Convert DB model to response."""
    return PartResponse(
        id=model.id,
        part_number=model.part_number,
        revision=model.revision,
        name=model.name,
        description=model.description,
        part_type=model.part_type,
        status=model.status,
        category=model.category,
        csi_code=model.csi_code,
        uniformat_code=model.uniformat_code,
        unit_of_measure=model.unit_of_measure,
        unit_cost=float(model.unit_cost) if model.unit_cost else None,
        manufacturer=model.manufacturer,
        manufacturer_pn=model.manufacturer_pn,
        lead_time_days=model.lead_time_days,
    )
