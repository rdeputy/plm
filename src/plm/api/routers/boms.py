"""
BOM API Router

Bill of Materials CRUD, explosion, and cost rollup.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from plm.api.deps import get_db_session
from plm.db.models import BOMModel, BOMItemModel, PartModel
from plm.boms.models import BOMType, Effectivity
from plm.parts.models import PartStatus

router = APIRouter()


# ----- Pydantic Schemas -----


class BOMCreate(BaseModel):
    """Schema for creating a BOM."""

    bom_number: str
    name: str
    parent_part_id: str
    description: Optional[str] = None
    bom_type: str = "engineering"
    effectivity: str = "as_designed"
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    project_id: Optional[str] = None


class BOMUpdate(BaseModel):
    """Schema for updating a BOM."""

    name: Optional[str] = None
    description: Optional[str] = None
    bom_type: Optional[str] = None
    effectivity: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class BOMItemCreate(BaseModel):
    """Schema for adding an item to a BOM."""

    part_id: str
    quantity: float
    find_number: Optional[int] = None
    reference_designator: str = ""
    location: Optional[str] = None
    notes: Optional[str] = None
    is_optional: bool = False
    option_code: Optional[str] = None


class BOMItemResponse(BaseModel):
    """Schema for a BOM line item response."""

    id: str
    bom_id: str
    part_id: str
    part_number: str
    part_revision: str
    quantity: float
    unit_of_measure: str
    find_number: int
    reference_designator: str
    location: Optional[str]
    notes: Optional[str]
    is_optional: bool
    option_code: Optional[str]
    has_sub_bom: bool


class BOMResponse(BaseModel):
    """Schema for BOM response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    bom_number: str
    revision: str
    name: str
    description: Optional[str]
    parent_part_id: str
    parent_part_revision: str
    bom_type: str
    effectivity: str
    status: str
    item_count: int
    items: list[BOMItemResponse]
    effective_from: Optional[date]
    effective_to: Optional[date]
    project_id: Optional[str]


class ExplodedItemResponse(BaseModel):
    """Schema for an exploded BOM item."""

    part_id: str
    part_number: str
    part_name: str
    level: int
    path: str
    quantity: float
    unit_of_measure: str
    unit_cost: Optional[float]
    extended_cost: Optional[float]
    reference_designator: str
    is_leaf: bool


class CostRollupResponse(BaseModel):
    """Schema for cost rollup result."""

    total_material_cost: float
    by_category: dict[str, float]
    item_count: int


class WhereUsedResponse(BaseModel):
    """Schema for where-used query result."""

    bom_id: str
    bom_number: str
    name: str
    parent_part_id: str


# ----- Endpoints -----


@router.get("", response_model=list[BOMResponse])
async def list_boms(
    parent_part_id: Optional[str] = Query(None),
    bom_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
):
    """List BOMs with optional filters."""
    query = db.query(BOMModel)

    if parent_part_id:
        query = query.filter(BOMModel.parent_part_id == parent_part_id)
    if bom_type:
        query = query.filter(BOMModel.bom_type == bom_type)
    if status:
        query = query.filter(BOMModel.status == status)
    if project_id:
        query = query.filter(BOMModel.project_id == project_id)

    boms = query.offset(offset).limit(limit).all()
    return [_bom_to_response(b) for b in boms]


@router.post("", response_model=BOMResponse, status_code=201)
async def create_bom(
    bom: BOMCreate,
    db: Session = Depends(get_db_session),
):
    """Create a new BOM."""
    # Verify parent part exists
    parent = db.query(PartModel).filter(PartModel.id == bom.parent_part_id).first()
    if not parent:
        raise HTTPException(status_code=400, detail="Parent part not found")

    # Check for duplicate bom_number
    existing = db.query(BOMModel).filter(BOMModel.bom_number == bom.bom_number).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"BOM number {bom.bom_number} already exists")

    from uuid import uuid4
    from datetime import datetime

    model = BOMModel(
        id=str(uuid4()),
        bom_number=bom.bom_number,
        revision="A",
        name=bom.name,
        description=bom.description,
        parent_part_id=bom.parent_part_id,
        parent_part_revision=parent.revision,
        bom_type=bom.bom_type,
        effectivity=bom.effectivity,
        status=PartStatus.DRAFT.value,
        effective_from=bom.effective_from,
        effective_to=bom.effective_to,
        project_id=bom.project_id,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    return _bom_to_response(model)


@router.get("/{bom_id}", response_model=BOMResponse)
async def get_bom(
    bom_id: str,
    db: Session = Depends(get_db_session),
):
    """Get a BOM by ID."""
    bom = db.query(BOMModel).filter(BOMModel.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")
    return _bom_to_response(bom)


@router.patch("/{bom_id}", response_model=BOMResponse)
async def update_bom(
    bom_id: str,
    updates: BOMUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a BOM."""
    bom = db.query(BOMModel).filter(BOMModel.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")

    if bom.status == PartStatus.RELEASED.value:
        raise HTTPException(status_code=400, detail="Cannot modify released BOM — create new revision")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(bom, field, value)

    db.commit()
    db.refresh(bom)

    return _bom_to_response(bom)


@router.post("/{bom_id}/release", response_model=BOMResponse)
async def release_bom(
    bom_id: str,
    released_by: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Release a BOM for use."""
    bom = db.query(BOMModel).filter(BOMModel.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")

    if bom.status not in [PartStatus.DRAFT.value, PartStatus.IN_REVIEW.value]:
        raise HTTPException(status_code=400, detail=f"Cannot release BOM in status {bom.status}")

    if not bom.items:
        raise HTTPException(status_code=400, detail="Cannot release BOM with no items")

    from datetime import datetime

    bom.status = PartStatus.RELEASED.value
    bom.released_by = released_by
    bom.released_at = datetime.now()

    db.commit()
    db.refresh(bom)

    return _bom_to_response(bom)


# ----- Item Endpoints -----


@router.post("/{bom_id}/items", response_model=BOMItemResponse, status_code=201)
async def add_bom_item(
    bom_id: str,
    item: BOMItemCreate,
    db: Session = Depends(get_db_session),
):
    """Add an item to a BOM."""
    bom = db.query(BOMModel).filter(BOMModel.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")

    if bom.status == PartStatus.RELEASED.value:
        raise HTTPException(status_code=400, detail="Cannot modify released BOM")

    part = db.query(PartModel).filter(PartModel.id == item.part_id).first()
    if not part:
        raise HTTPException(status_code=400, detail="Part not found")

    from uuid import uuid4

    # Auto-assign find number if not provided
    find_number = item.find_number
    if find_number is None:
        max_find = max((i.find_number for i in bom.items), default=0) if bom.items else 0
        find_number = max_find + 10

    # Check if part has its own BOM
    has_sub = db.query(BOMModel).filter(BOMModel.parent_part_id == item.part_id).first() is not None

    item_model = BOMItemModel(
        id=str(uuid4()),
        bom_id=bom_id,
        part_id=item.part_id,
        part_number=part.part_number,
        part_revision=part.revision,
        quantity=Decimal(str(item.quantity)),
        unit_of_measure=part.unit_of_measure,
        find_number=find_number,
        reference_designator=item.reference_designator,
        location=item.location,
        notes=item.notes,
        is_optional=item.is_optional,
        option_code=item.option_code,
        has_sub_bom=has_sub,
    )
    db.add(item_model)
    db.commit()
    db.refresh(item_model)

    return _item_to_response(item_model)


@router.delete("/{bom_id}/items/{item_id}", status_code=204)
async def remove_bom_item(
    bom_id: str,
    item_id: str,
    db: Session = Depends(get_db_session),
):
    """Remove an item from a BOM."""
    bom = db.query(BOMModel).filter(BOMModel.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")

    if bom.status == PartStatus.RELEASED.value:
        raise HTTPException(status_code=400, detail="Cannot modify released BOM")

    item = (
        db.query(BOMItemModel)
        .filter(BOMItemModel.id == item_id, BOMItemModel.bom_id == bom_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="BOM item not found")

    db.delete(item)
    db.commit()


# ----- Explosion & Cost Rollup -----


@router.get("/{bom_id}/explode", response_model=list[ExplodedItemResponse])
async def explode_bom(
    bom_id: str,
    levels: int = Query(-1, description="Number of levels to explode (-1 = all)"),
    db: Session = Depends(get_db_session),
):
    """Explode a BOM to show all components."""
    bom = db.query(BOMModel).filter(BOMModel.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")

    result: list[dict] = []
    _explode_recursive(db, bom, result, level=0, max_levels=levels, parent_qty=Decimal("1"), path="")

    return result


@router.get("/{bom_id}/cost-rollup", response_model=CostRollupResponse)
async def cost_rollup(
    bom_id: str,
    db: Session = Depends(get_db_session),
):
    """Calculate total material cost by rolling up BOM."""
    bom = db.query(BOMModel).filter(BOMModel.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")

    exploded: list[dict] = []
    _explode_recursive(db, bom, exploded, level=0, max_levels=-1, parent_qty=Decimal("1"), path="")

    total_material = Decimal("0")
    by_category: dict[str, Decimal] = {}

    for item in exploded:
        if item["is_leaf"] and item["extended_cost"]:
            cost = Decimal(str(item["extended_cost"]))
            total_material += cost
            part = db.query(PartModel).filter(PartModel.id == item["part_id"]).first()
            if part and part.category:
                by_category[part.category] = by_category.get(part.category, Decimal("0")) + cost

    return CostRollupResponse(
        total_material_cost=float(total_material),
        by_category={k: float(v) for k, v in by_category.items()},
        item_count=len(exploded),
    )


@router.get("/where-used/{part_id}", response_model=list[WhereUsedResponse])
async def where_used(
    part_id: str,
    db: Session = Depends(get_db_session),
):
    """Find all BOMs that reference a part."""
    items = db.query(BOMItemModel).filter(BOMItemModel.part_id == part_id).all()
    bom_ids = {item.bom_id for item in items}

    if not bom_ids:
        return []

    boms = db.query(BOMModel).filter(BOMModel.id.in_(bom_ids)).all()
    return [
        WhereUsedResponse(
            bom_id=b.id,
            bom_number=b.bom_number,
            name=b.name,
            parent_part_id=b.parent_part_id,
        )
        for b in boms
    ]


# ----- Helpers -----


def _explode_recursive(
    db: Session,
    bom_model: BOMModel,
    result: list[dict],
    level: int,
    max_levels: int,
    parent_qty: Decimal,
    path: str,
) -> None:
    """Recursively explode BOM into flat list."""
    if max_levels >= 0 and level > max_levels:
        return

    for item in bom_model.items:
        part = db.query(PartModel).filter(PartModel.id == item.part_id).first()
        if not part:
            continue

        extended_qty = item.quantity * parent_qty
        item_path = f"{path}/{part.part_number}" if path else part.part_number

        child_bom = db.query(BOMModel).filter(BOMModel.parent_part_id == item.part_id).first()
        is_leaf = child_bom is None

        extended_cost = None
        if part.unit_cost:
            extended_cost = float(part.unit_cost * extended_qty)

        result.append(
            ExplodedItemResponse(
                part_id=item.part_id,
                part_number=part.part_number,
                part_name=part.name,
                level=level,
                path=item_path,
                quantity=float(extended_qty),
                unit_of_measure=part.unit_of_measure,
                unit_cost=float(part.unit_cost) if part.unit_cost else None,
                extended_cost=extended_cost,
                reference_designator=item.reference_designator,
                is_leaf=is_leaf,
            ).model_dump()
        )

        if child_bom and (max_levels < 0 or level < max_levels):
            _explode_recursive(
                db, child_bom, result, level + 1, max_levels,
                extended_qty, item_path,
            )


def _bom_to_response(model: BOMModel) -> BOMResponse:
    """Convert DB model to response."""
    return BOMResponse(
        id=model.id,
        bom_number=model.bom_number,
        revision=model.revision,
        name=model.name,
        description=model.description,
        parent_part_id=model.parent_part_id,
        parent_part_revision=model.parent_part_revision,
        bom_type=model.bom_type,
        effectivity=model.effectivity,
        status=model.status,
        item_count=len(model.items) if model.items else 0,
        items=[_item_to_response(i) for i in (model.items or [])],
        effective_from=model.effective_from,
        effective_to=model.effective_to,
        project_id=model.project_id,
    )


def _item_to_response(model: BOMItemModel) -> BOMItemResponse:
    """Convert DB model to response."""
    return BOMItemResponse(
        id=model.id,
        bom_id=model.bom_id,
        part_id=model.part_id,
        part_number=model.part_number,
        part_revision=model.part_revision,
        quantity=float(model.quantity),
        unit_of_measure=model.unit_of_measure,
        find_number=model.find_number,
        reference_designator=model.reference_designator,
        location=model.location,
        notes=model.notes,
        is_optional=model.is_optional,
        option_code=model.option_code,
        has_sub_bom=model.has_sub_bom,
    )
