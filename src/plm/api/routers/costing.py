"""
Costing API Router

Cost management, variance analysis, and should-cost.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from plm.api.deps import get_db_session
from plm.db.models import (
    PartCostModel,
    CostElementModel,
    CostVarianceModel,
    ShouldCostAnalysisModel,
)

router = APIRouter()


# ----- Pydantic Schemas -----


class CostElementCreate(BaseModel):
    cost_type: str
    description: Optional[str] = None
    unit_cost: float = 0
    quantity: float = 1
    source: Optional[str] = None
    vendor_id: Optional[str] = None


class CostElementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    cost_type: str
    description: Optional[str]
    unit_cost: float
    quantity: float
    extended_cost: float
    source: Optional[str]


class PartCostCreate(BaseModel):
    part_id: str
    part_number: str
    part_revision: str = ""
    lot_size: int = 1
    currency: str = "USD"


class PartCostUpdate(BaseModel):
    status: Optional[str] = None
    target_cost: Optional[float] = None
    selling_price: Optional[float] = None
    notes: Optional[str] = None


class PartCostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    part_id: str
    part_number: str
    part_revision: str
    status: str
    material_cost: float
    labor_cost: float
    overhead_cost: float
    total_cost: float
    target_cost: Optional[float]
    margin_percent: Optional[float]
    currency: str
    lot_size: int


class CostVarianceCreate(BaseModel):
    part_id: str
    part_number: str
    period: str
    standard_cost: float
    actual_cost: float
    variance_type: str = "material_price"
    quantity: float = 1


class CostVarianceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    part_id: str
    part_number: str
    period: str
    standard_cost: float
    actual_cost: float
    variance: float
    variance_percent: float
    variance_type: str
    favorable: bool


class ShouldCostCreate(BaseModel):
    part_id: str
    part_number: str
    methodology: str = "bottom-up"
    raw_material: float = 0
    material_processing: float = 0
    conversion_cost: float = 0
    profit_margin: float = 0
    logistics: float = 0
    current_price: Optional[float] = None
    analyst: Optional[str] = None


class ShouldCostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    part_id: str
    part_number: str
    analysis_date: str
    methodology: str
    should_cost: float
    current_price: Optional[float]
    savings_opportunity: Optional[float]
    savings_percent: Optional[float]


# ----- Part Cost Endpoints -----


@router.get("/parts/{part_id}/cost", response_model=PartCostResponse)
async def get_part_cost(part_id: str, db: Session = Depends(get_db_session)):
    """Get cost breakdown for a part."""
    cost = db.query(PartCostModel).filter(PartCostModel.part_id == part_id).first()
    if not cost:
        raise HTTPException(status_code=404, detail="No cost record found for this part")
    return cost


@router.post("/parts/{part_id}/cost", response_model=PartCostResponse, status_code=201)
async def create_part_cost(
    part_id: str,
    cost: PartCostCreate,
    db: Session = Depends(get_db_session),
):
    """Create a cost record for a part."""
    existing = db.query(PartCostModel).filter(PartCostModel.part_id == part_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cost record already exists for this part")

    model = PartCostModel(
        id=str(uuid4()),
        part_id=part_id,
        part_number=cost.part_number,
        part_revision=cost.part_revision,
        status="draft",
        lot_size=cost.lot_size,
        currency=cost.currency,
        material_cost=Decimal("0"),
        labor_cost=Decimal("0"),
        overhead_cost=Decimal("0"),
        total_cost=Decimal("0"),
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.patch("/parts/{part_id}/cost", response_model=PartCostResponse)
async def update_part_cost(
    part_id: str,
    updates: PartCostUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a part cost record."""
    cost = db.query(PartCostModel).filter(PartCostModel.part_id == part_id).first()
    if not cost:
        raise HTTPException(status_code=404, detail="Cost record not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is not None:
            if field in ["target_cost", "selling_price"]:
                setattr(cost, field, Decimal(str(value)))
            else:
                setattr(cost, field, value)

    db.commit()
    db.refresh(cost)
    return cost


# ----- Cost Element Endpoints -----


@router.get("/parts/{part_id}/cost/elements", response_model=list[CostElementResponse])
async def list_cost_elements(part_id: str, db: Session = Depends(get_db_session)):
    """List cost elements for a part."""
    cost = db.query(PartCostModel).filter(PartCostModel.part_id == part_id).first()
    if not cost:
        raise HTTPException(status_code=404, detail="Cost record not found")

    return db.query(CostElementModel).filter(CostElementModel.part_cost_id == cost.id).all()


@router.post("/parts/{part_id}/cost/elements", response_model=CostElementResponse, status_code=201)
async def add_cost_element(
    part_id: str,
    element: CostElementCreate,
    db: Session = Depends(get_db_session),
):
    """Add a cost element to a part."""
    cost = db.query(PartCostModel).filter(PartCostModel.part_id == part_id).first()
    if not cost:
        raise HTTPException(status_code=404, detail="Cost record not found")

    unit_cost = Decimal(str(element.unit_cost))
    quantity = Decimal(str(element.quantity))
    extended = unit_cost * quantity

    model = CostElementModel(
        id=str(uuid4()),
        part_cost_id=cost.id,
        cost_type=element.cost_type,
        description=element.description,
        unit_cost=unit_cost,
        quantity=quantity,
        extended_cost=extended,
        source=element.source,
        vendor_id=element.vendor_id,
    )
    db.add(model)

    # Update totals
    if element.cost_type in ["material", "purchased"]:
        cost.material_cost += extended
    elif element.cost_type == "labor":
        cost.labor_cost += extended
    elif element.cost_type == "overhead":
        cost.overhead_cost += extended
    cost.total_cost += extended

    db.commit()
    db.refresh(model)
    return model


@router.delete("/parts/{part_id}/cost/elements/{element_id}", status_code=204)
async def remove_cost_element(
    part_id: str,
    element_id: str,
    db: Session = Depends(get_db_session),
):
    """Remove a cost element."""
    cost = db.query(PartCostModel).filter(PartCostModel.part_id == part_id).first()
    if not cost:
        raise HTTPException(status_code=404, detail="Cost record not found")

    element = db.query(CostElementModel).filter(
        CostElementModel.id == element_id,
        CostElementModel.part_cost_id == cost.id,
    ).first()
    if not element:
        raise HTTPException(status_code=404, detail="Element not found")

    # Update totals
    if element.cost_type in ["material", "purchased"]:
        cost.material_cost -= element.extended_cost
    elif element.cost_type == "labor":
        cost.labor_cost -= element.extended_cost
    elif element.cost_type == "overhead":
        cost.overhead_cost -= element.extended_cost
    cost.total_cost -= element.extended_cost

    db.delete(element)
    db.commit()


# ----- Cost Variance Endpoints -----


@router.get("/variances", response_model=list[CostVarianceResponse])
async def list_cost_variances(
    part_id: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    variance_type: Optional[str] = Query(None),
    favorable: Optional[bool] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db_session),
):
    """List cost variances."""
    query = db.query(CostVarianceModel)

    if part_id:
        query = query.filter(CostVarianceModel.part_id == part_id)
    if period:
        query = query.filter(CostVarianceModel.period == period)
    if variance_type:
        query = query.filter(CostVarianceModel.variance_type == variance_type)
    if favorable is not None:
        query = query.filter(CostVarianceModel.favorable == favorable)

    return query.limit(limit).all()


@router.post("/variances", response_model=CostVarianceResponse, status_code=201)
async def create_cost_variance(
    var: CostVarianceCreate,
    db: Session = Depends(get_db_session),
):
    """Create a cost variance record."""
    standard = Decimal(str(var.standard_cost))
    actual = Decimal(str(var.actual_cost))
    variance = actual - standard
    favorable = variance < 0
    variance_percent = float(variance / standard * 100) if standard else 0

    model = CostVarianceModel(
        id=str(uuid4()),
        part_id=var.part_id,
        part_number=var.part_number,
        period=var.period,
        standard_cost=standard,
        actual_cost=actual,
        variance=variance,
        variance_percent=variance_percent,
        variance_type=var.variance_type,
        favorable=favorable,
        quantity=Decimal(str(var.quantity)),
        total_variance=variance * Decimal(str(var.quantity)),
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


# ----- Should-Cost Analysis Endpoints -----


@router.get("/parts/{part_id}/should-cost", response_model=list[ShouldCostResponse])
async def list_should_cost_analyses(part_id: str, db: Session = Depends(get_db_session)):
    """List should-cost analyses for a part."""
    return db.query(ShouldCostAnalysisModel).filter(
        ShouldCostAnalysisModel.part_id == part_id
    ).order_by(ShouldCostAnalysisModel.analysis_date.desc()).all()


@router.post("/parts/{part_id}/should-cost", response_model=ShouldCostResponse, status_code=201)
async def create_should_cost_analysis(
    part_id: str,
    analysis: ShouldCostCreate,
    db: Session = Depends(get_db_session),
):
    """Create a should-cost analysis."""
    raw = Decimal(str(analysis.raw_material))
    processing = Decimal(str(analysis.material_processing))
    conversion = Decimal(str(analysis.conversion_cost))
    margin = Decimal(str(analysis.profit_margin))
    logistics = Decimal(str(analysis.logistics))
    should_cost = raw + processing + conversion + margin + logistics

    current = Decimal(str(analysis.current_price)) if analysis.current_price else None
    savings = None
    savings_pct = None
    if current:
        savings = current - should_cost
        savings_pct = float(savings / current * 100)

    model = ShouldCostAnalysisModel(
        id=str(uuid4()),
        part_id=part_id,
        part_number=analysis.part_number,
        analysis_date=date.today(),
        analyst=analysis.analyst,
        methodology=analysis.methodology,
        should_cost=should_cost,
        raw_material=raw,
        material_processing=processing,
        conversion_cost=conversion,
        profit_margin=margin,
        logistics=logistics,
        current_price=current,
        savings_opportunity=savings,
        savings_percent=savings_pct,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model
