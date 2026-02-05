"""
Change Order API Router

Engineering Change Orders (ECOs), approvals, and impact analysis.
"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from plm.api.deps import get_db_session
from plm.db.models import (
    ChangeOrderModel,
    ChangeModel,
    ApprovalModel,
    ImpactAnalysisModel,
)
from plm.changes.models import ECOStatus, ChangeType, ChangeReason, ChangeUrgency

router = APIRouter()


# ----- Pydantic Schemas -----


class ECOCreate(BaseModel):
    """Schema for creating an ECO."""

    title: str
    description: str = ""
    reason: str = "customer_request"
    urgency: str = "standard"
    project_id: Optional[str] = None
    affected_parts: list[str] = []
    affected_boms: list[str] = []


class ECOUpdate(BaseModel):
    """Schema for updating an ECO."""

    title: Optional[str] = None
    description: Optional[str] = None
    reason: Optional[str] = None
    urgency: Optional[str] = None
    affected_parts: Optional[list[str]] = None
    affected_boms: Optional[list[str]] = None


class ChangeCreate(BaseModel):
    """Schema for adding a change to an ECO."""

    change_type: str  # add, remove, modify, replace
    entity_type: str  # part, bom_item, document
    entity_id: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    replaced_by_id: Optional[str] = None
    justification: str = ""
    notes: Optional[str] = None


class ApprovalCreate(BaseModel):
    """Schema for recording an approval."""

    approver_id: str
    approver_name: str
    approver_role: str
    decision: str  # approved, rejected, approved_with_conditions
    conditions: Optional[str] = None
    comments: Optional[str] = None


class ChangeResponse(BaseModel):
    """Schema for a change response."""

    id: str
    eco_id: str
    change_type: str
    entity_type: str
    entity_id: str
    field_name: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    replaced_by_id: Optional[str]
    justification: str
    notes: Optional[str]


class ApprovalResponse(BaseModel):
    """Schema for an approval response."""

    id: str
    eco_id: str
    approver_id: str
    approver_name: str
    approver_role: str
    decision: str
    conditions: Optional[str]
    comments: Optional[str]
    decided_at: datetime


class ImpactAnalysisResponse(BaseModel):
    """Schema for impact analysis response."""

    id: str
    material_cost_delta: float
    labor_cost_delta: float
    total_cost_delta: float
    schedule_delta_days: int
    critical_path_affected: bool
    arc_resubmission_required: bool
    permit_revision_required: bool
    risk_level: str
    recommendations: list[str]


class ECOResponse(BaseModel):
    """Schema for ECO response."""

    id: str
    eco_number: str
    title: str
    description: str
    reason: str
    urgency: str
    status: str
    project_id: Optional[str]
    affected_parts: list[str]
    affected_boms: list[str]
    changes: list[ChangeResponse]
    approvals: list[ApprovalResponse]
    impact_analysis: Optional[ImpactAnalysisResponse]
    submitted_by: Optional[str]
    submitted_at: Optional[datetime]
    implemented_by: Optional[str]
    implementation_date: Optional[date]
    implementation_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


# ----- ECO Endpoints -----


@router.get("", response_model=list[ECOResponse])
async def list_ecos(
    status: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
):
    """List ECOs with optional filters."""
    query = db.query(ChangeOrderModel)

    if status:
        query = query.filter(ChangeOrderModel.status == status)
    if project_id:
        query = query.filter(ChangeOrderModel.project_id == project_id)
    if urgency:
        query = query.filter(ChangeOrderModel.urgency == urgency)

    ecos = query.order_by(ChangeOrderModel.created_at.desc()).offset(offset).limit(limit).all()
    return [_eco_to_response(e) for e in ecos]


@router.post("", response_model=ECOResponse, status_code=201)
async def create_eco(
    eco: ECOCreate,
    db: Session = Depends(get_db_session),
):
    """Create a new Engineering Change Order."""
    from uuid import uuid4

    # Generate ECO number
    eco_count = db.query(ChangeOrderModel).count() + 1
    eco_number = f"ECO-{datetime.now().year}-{eco_count:04d}"

    model = ChangeOrderModel(
        id=str(uuid4()),
        eco_number=eco_number,
        title=eco.title,
        description=eco.description,
        reason=eco.reason,
        urgency=eco.urgency,
        project_id=eco.project_id,
        affected_parts=eco.affected_parts,
        affected_boms=eco.affected_boms,
        status=ECOStatus.DRAFT.value,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    return _eco_to_response(model)


@router.get("/{eco_id}", response_model=ECOResponse)
async def get_eco(
    eco_id: str,
    db: Session = Depends(get_db_session),
):
    """Get an ECO by ID."""
    eco = db.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")
    return _eco_to_response(eco)


@router.patch("/{eco_id}", response_model=ECOResponse)
async def update_eco(
    eco_id: str,
    updates: ECOUpdate,
    db: Session = Depends(get_db_session),
):
    """Update an ECO (only in draft status)."""
    eco = db.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    if eco.status != ECOStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail=f"Cannot modify ECO in status {eco.status}")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(eco, field, value)

    eco.updated_at = datetime.now()
    db.commit()
    db.refresh(eco)

    return _eco_to_response(eco)


# ----- Workflow Endpoints -----


@router.post("/{eco_id}/submit", response_model=ECOResponse)
async def submit_eco(
    eco_id: str,
    submitted_by: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Submit an ECO for review."""
    eco = db.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    if eco.status != ECOStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail=f"Cannot submit ECO in status {eco.status}")

    eco.status = ECOStatus.SUBMITTED.value
    eco.submitted_by = submitted_by
    eco.submitted_at = datetime.now()
    eco.updated_at = datetime.now()

    db.commit()
    db.refresh(eco)

    return _eco_to_response(eco)


@router.post("/{eco_id}/start-review", response_model=ECOResponse)
async def start_review(
    eco_id: str,
    db: Session = Depends(get_db_session),
):
    """Move ECO from submitted to in-review."""
    eco = db.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    if eco.status != ECOStatus.SUBMITTED.value:
        raise HTTPException(status_code=400, detail=f"Cannot start review for ECO in status {eco.status}")

    eco.status = ECOStatus.IN_REVIEW.value
    eco.updated_at = datetime.now()

    db.commit()
    db.refresh(eco)

    return _eco_to_response(eco)


@router.post("/{eco_id}/approve", response_model=ECOResponse)
async def approve_eco(
    eco_id: str,
    db: Session = Depends(get_db_session),
):
    """Move ECO to approved status."""
    eco = db.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    if eco.status != ECOStatus.IN_REVIEW.value:
        raise HTTPException(status_code=400, detail=f"Cannot approve ECO in status {eco.status}")

    eco.status = ECOStatus.APPROVED.value
    eco.updated_at = datetime.now()

    db.commit()
    db.refresh(eco)

    return _eco_to_response(eco)


@router.post("/{eco_id}/implement", response_model=ECOResponse)
async def implement_eco(
    eco_id: str,
    implemented_by: str = Query(...),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """Mark ECO as implemented."""
    eco = db.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    if eco.status != ECOStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail=f"Cannot implement ECO in status {eco.status}")

    eco.status = ECOStatus.IMPLEMENTED.value
    eco.implemented_by = implemented_by
    eco.implementation_date = date.today()
    eco.implementation_notes = notes
    eco.updated_at = datetime.now()

    db.commit()
    db.refresh(eco)

    return _eco_to_response(eco)


@router.post("/{eco_id}/close", response_model=ECOResponse)
async def close_eco(
    eco_id: str,
    db: Session = Depends(get_db_session),
):
    """Close an implemented ECO."""
    eco = db.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    if eco.status != ECOStatus.IMPLEMENTED.value:
        raise HTTPException(status_code=400, detail=f"Cannot close ECO in status {eco.status}")

    eco.status = ECOStatus.CLOSED.value
    eco.closed_at = datetime.now()
    eco.updated_at = datetime.now()

    db.commit()
    db.refresh(eco)

    return _eco_to_response(eco)


@router.post("/{eco_id}/cancel", response_model=ECOResponse)
async def cancel_eco(
    eco_id: str,
    reason: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Cancel an ECO."""
    eco = db.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    if eco.status in [ECOStatus.IMPLEMENTED.value, ECOStatus.CLOSED.value]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel ECO in status {eco.status}")

    eco.status = ECOStatus.CANCELLED.value
    eco.implementation_notes = reason
    eco.updated_at = datetime.now()

    db.commit()
    db.refresh(eco)

    return _eco_to_response(eco)


# ----- Change Detail Endpoints -----


@router.post("/{eco_id}/changes", response_model=ChangeResponse, status_code=201)
async def add_change(
    eco_id: str,
    change: ChangeCreate,
    db: Session = Depends(get_db_session),
):
    """Add a change detail to an ECO."""
    eco = db.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    if eco.status in [ECOStatus.IMPLEMENTED.value, ECOStatus.CLOSED.value, ECOStatus.CANCELLED.value]:
        raise HTTPException(status_code=400, detail=f"Cannot add changes to ECO in status {eco.status}")

    from uuid import uuid4

    model = ChangeModel(
        id=str(uuid4()),
        eco_id=eco_id,
        change_type=change.change_type,
        entity_type=change.entity_type,
        entity_id=change.entity_id,
        field_name=change.field_name,
        old_value=change.old_value,
        new_value=change.new_value,
        replaced_by_id=change.replaced_by_id,
        justification=change.justification,
        notes=change.notes,
    )
    db.add(model)

    eco.updated_at = datetime.now()
    db.commit()
    db.refresh(model)

    return _change_to_response(model)


# ----- Approval Endpoints -----


@router.post("/{eco_id}/approvals", response_model=ApprovalResponse, status_code=201)
async def add_approval(
    eco_id: str,
    approval: ApprovalCreate,
    db: Session = Depends(get_db_session),
):
    """Record an approval decision on an ECO."""
    eco = db.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    if eco.status not in [ECOStatus.SUBMITTED.value, ECOStatus.IN_REVIEW.value]:
        raise HTTPException(
            status_code=400, detail=f"Cannot add approvals to ECO in status {eco.status}"
        )

    from uuid import uuid4

    model = ApprovalModel(
        id=str(uuid4()),
        eco_id=eco_id,
        approver_id=approval.approver_id,
        approver_name=approval.approver_name,
        approver_role=approval.approver_role,
        decision=approval.decision,
        conditions=approval.conditions,
        comments=approval.comments,
        decided_at=datetime.now(),
    )
    db.add(model)

    eco.updated_at = datetime.now()
    db.commit()
    db.refresh(model)

    return _approval_to_response(model)


# ----- Helpers -----


def _eco_to_response(model: ChangeOrderModel) -> ECOResponse:
    """Convert DB model to response."""
    impact = None
    if model.impact_analysis:
        ia = model.impact_analysis
        impact = ImpactAnalysisResponse(
            id=ia.id,
            material_cost_delta=float(ia.material_cost_delta),
            labor_cost_delta=float(ia.labor_cost_delta),
            total_cost_delta=float(ia.total_cost_delta),
            schedule_delta_days=ia.schedule_delta_days,
            critical_path_affected=ia.critical_path_affected,
            arc_resubmission_required=ia.arc_resubmission_required,
            permit_revision_required=ia.permit_revision_required,
            risk_level=ia.risk_level,
            recommendations=ia.recommendations or [],
        )

    return ECOResponse(
        id=model.id,
        eco_number=model.eco_number,
        title=model.title,
        description=model.description,
        reason=model.reason,
        urgency=model.urgency,
        status=model.status,
        project_id=model.project_id,
        affected_parts=model.affected_parts or [],
        affected_boms=model.affected_boms or [],
        changes=[_change_to_response(c) for c in (model.changes or [])],
        approvals=[_approval_to_response(a) for a in (model.approvals or [])],
        impact_analysis=impact,
        submitted_by=model.submitted_by,
        submitted_at=model.submitted_at,
        implemented_by=model.implemented_by,
        implementation_date=model.implementation_date,
        implementation_notes=model.implementation_notes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _change_to_response(model: ChangeModel) -> ChangeResponse:
    """Convert DB model to response."""
    return ChangeResponse(
        id=model.id,
        eco_id=model.eco_id,
        change_type=model.change_type,
        entity_type=model.entity_type,
        entity_id=model.entity_id,
        field_name=model.field_name,
        old_value=model.old_value,
        new_value=model.new_value,
        replaced_by_id=model.replaced_by_id,
        justification=model.justification,
        notes=model.notes,
    )


def _approval_to_response(model: ApprovalModel) -> ApprovalResponse:
    """Convert DB model to response."""
    return ApprovalResponse(
        id=model.id,
        eco_id=model.eco_id,
        approver_id=model.approver_id,
        approver_name=model.approver_name,
        approver_role=model.approver_role,
        decision=model.decision,
        conditions=model.conditions,
        comments=model.comments,
        decided_at=model.decided_at,
    )
