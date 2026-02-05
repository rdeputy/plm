"""
Quality API Router

Endpoints for NCRs, CAPAs, inspections, and holds.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...quality import (
    CAPAStatus,
    CAPAType,
    NCRSeverity,
    NCRSource,
    NCRStatus,
    get_quality_service,
)
from ...quality.models import DispositionType

router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================


class NCRCreateRequest(BaseModel):
    """Create NCR request."""
    title: str
    description: str
    severity: str
    source: str
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    lot_number: Optional[str] = None
    quantity_affected: float = 1.0
    project_id: Optional[str] = None
    supplier_id: Optional[str] = None
    po_id: Optional[str] = None


class NCRResponse(BaseModel):
    """NCR response."""
    id: str
    ncr_number: str
    status: str
    severity: str
    source: str
    title: str
    description: str
    part_number: Optional[str] = None
    lot_number: Optional[str] = None
    quantity_affected: float
    disposition: Optional[str] = None
    root_cause: Optional[str] = None
    capa_id: Optional[str] = None
    capa_required: bool
    estimated_cost: float
    created_at: Optional[str] = None


class DispositionRequest(BaseModel):
    """Set disposition request."""
    disposition: str
    notes: Optional[str] = None


class CAPACreateRequest(BaseModel):
    """Create CAPA request."""
    title: str
    description: str
    capa_type: str
    problem_statement: str = ""
    ncr_ids: list[str] = Field(default_factory=list)
    priority: str = "medium"
    owner_id: str
    due_date: Optional[date] = None


class CAPAResponse(BaseModel):
    """CAPA response."""
    id: str
    capa_number: str
    capa_type: str
    status: str
    priority: str
    title: str
    description: str
    ncr_count: int
    root_causes: list[str]
    action_count: int
    owner_id: Optional[str] = None
    due_date: Optional[str] = None
    eco_id: Optional[str] = None
    created_at: Optional[str] = None


class ActionRequest(BaseModel):
    """Add action request."""
    action_type: str  # immediate, corrective, preventive
    description: str
    responsible: str
    due_date: Optional[date] = None


class RootCauseRequest(BaseModel):
    """Add root cause request."""
    root_cause: str
    analysis_method: str = ""


class VerifyRequest(BaseModel):
    """CAPA verification request."""
    method: str
    results: str


class InspectionCreateRequest(BaseModel):
    """Create inspection request."""
    inspection_type: str
    inspector_name: str
    part_number: Optional[str] = None
    lot_number: Optional[str] = None
    po_id: Optional[str] = None
    quantity_inspected: float = 0


class InspectionCompleteRequest(BaseModel):
    """Complete inspection request."""
    result: str  # pass, fail, conditional
    quantity_accepted: float
    quantity_rejected: float
    defects: list[dict] = Field(default_factory=list)
    measurements: list[dict] = Field(default_factory=list)
    create_ncr_if_failed: bool = True


class InspectionResponse(BaseModel):
    """Inspection response."""
    id: str
    inspection_number: str
    inspection_type: str
    part_number: Optional[str] = None
    lot_number: Optional[str] = None
    quantity_inspected: float
    quantity_accepted: float
    quantity_rejected: float
    result: str
    defect_count: int
    ncr_id: Optional[str] = None
    inspector_name: Optional[str] = None
    inspection_date: Optional[str] = None


class HoldCreateRequest(BaseModel):
    """Create hold request."""
    reason: str
    hold_type: str
    part_number: Optional[str] = None
    lot_number: Optional[str] = None
    quantity: float = 0
    ncr_id: Optional[str] = None
    location_id: Optional[str] = None


class HoldResponse(BaseModel):
    """Hold response."""
    id: str
    hold_number: str
    part_number: Optional[str] = None
    lot_number: Optional[str] = None
    quantity: float
    reason: str
    hold_type: str
    is_active: bool
    ncr_id: Optional[str] = None
    placed_by: Optional[str] = None
    placed_at: Optional[str] = None


class QualityMetricsResponse(BaseModel):
    """Quality metrics response."""
    ncrs: dict
    capas: dict
    inspections: dict
    holds: dict


# =============================================================================
# NCR Endpoints
# =============================================================================


@router.post("/ncrs", response_model=NCRResponse)
async def create_ncr(data: NCRCreateRequest, user_id: str = Query(...)):
    """Create a new NCR."""
    service = get_quality_service()

    try:
        severity = NCRSeverity(data.severity)
        source = NCRSource(data.source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ncr = service.create_ncr(
        title=data.title,
        description=data.description,
        severity=severity,
        source=source,
        created_by=user_id,
        part_id=data.part_id,
        part_number=data.part_number,
        lot_number=data.lot_number,
        quantity_affected=Decimal(str(data.quantity_affected)),
        project_id=data.project_id,
        supplier_id=data.supplier_id,
        po_id=data.po_id,
    )

    return _ncr_to_response(ncr)


@router.get("/ncrs", response_model=list[NCRResponse])
async def list_ncrs(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    part_number: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """List NCRs with filters."""
    service = get_quality_service()

    status_enum = NCRStatus(status) if status else None
    severity_enum = NCRSeverity(severity) if severity else None

    ncrs = service.list_ncrs(
        status=status_enum,
        severity=severity_enum,
        part_number=part_number,
        project_id=project_id,
        limit=limit,
    )

    return [_ncr_to_response(n) for n in ncrs]


@router.get("/ncrs/{ncr_id}", response_model=NCRResponse)
async def get_ncr(ncr_id: str):
    """Get an NCR by ID."""
    service = get_quality_service()
    ncr = service.get_ncr(ncr_id)

    if not ncr:
        raise HTTPException(status_code=404, detail="NCR not found")

    return _ncr_to_response(ncr)


@router.post("/ncrs/{ncr_id}/status")
async def update_ncr_status(
    ncr_id: str,
    status: str,
    user_id: str = Query(...),
    notes: Optional[str] = None,
):
    """Update NCR status."""
    service = get_quality_service()

    try:
        status_enum = NCRStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    ncr = service.update_ncr_status(ncr_id, status_enum, user_id, notes)
    if not ncr:
        raise HTTPException(status_code=404, detail="NCR not found")

    return _ncr_to_response(ncr)


@router.post("/ncrs/{ncr_id}/disposition", response_model=NCRResponse)
async def set_disposition(
    ncr_id: str,
    data: DispositionRequest,
    user_id: str = Query(...),
):
    """Set NCR disposition."""
    service = get_quality_service()

    try:
        disposition = DispositionType(data.disposition)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid disposition: {data.disposition}")

    ncr = service.set_disposition(ncr_id, disposition, user_id, data.notes)
    if not ncr:
        raise HTTPException(status_code=404, detail="NCR not found")

    return _ncr_to_response(ncr)


@router.post("/ncrs/{ncr_id}/link-capa")
async def link_capa_to_ncr(ncr_id: str, capa_id: str):
    """Link a CAPA to an NCR."""
    service = get_quality_service()

    ncr = service.link_capa(ncr_id, capa_id)
    if not ncr:
        raise HTTPException(status_code=404, detail="NCR not found")

    return {"status": "linked", "ncr_id": ncr_id, "capa_id": capa_id}


# =============================================================================
# CAPA Endpoints
# =============================================================================


@router.post("/capas", response_model=CAPAResponse)
async def create_capa(data: CAPACreateRequest, user_id: str = Query(...)):
    """Create a new CAPA."""
    service = get_quality_service()

    try:
        capa_type = CAPAType(data.capa_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid CAPA type: {data.capa_type}")

    capa = service.create_capa(
        title=data.title,
        description=data.description,
        capa_type=capa_type,
        initiated_by=user_id,
        owner_id=data.owner_id,
        problem_statement=data.problem_statement,
        ncr_ids=data.ncr_ids,
        priority=data.priority,
        due_date=data.due_date,
    )

    return _capa_to_response(capa)


@router.get("/capas", response_model=list[CAPAResponse])
async def list_capas(
    status: Optional[str] = None,
    capa_type: Optional[str] = None,
    owner_id: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """List CAPAs with filters."""
    service = get_quality_service()

    status_enum = CAPAStatus(status) if status else None
    type_enum = CAPAType(capa_type) if capa_type else None

    capas = service.list_capas(
        status=status_enum,
        capa_type=type_enum,
        owner_id=owner_id,
        limit=limit,
    )

    return [_capa_to_response(c) for c in capas]


@router.get("/capas/{capa_id}", response_model=CAPAResponse)
async def get_capa(capa_id: str):
    """Get a CAPA by ID."""
    service = get_quality_service()
    capa = service.get_capa(capa_id)

    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")

    return _capa_to_response(capa)


@router.post("/capas/{capa_id}/status")
async def update_capa_status(
    capa_id: str,
    status: str,
    user_id: str = Query(...),
):
    """Update CAPA status."""
    service = get_quality_service()

    try:
        status_enum = CAPAStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    capa = service.update_capa_status(capa_id, status_enum, user_id)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")

    return _capa_to_response(capa)


@router.post("/capas/{capa_id}/root-cause", response_model=CAPAResponse)
async def add_root_cause(capa_id: str, data: RootCauseRequest):
    """Add a root cause to CAPA."""
    service = get_quality_service()

    capa = service.add_root_cause(capa_id, data.root_cause, data.analysis_method)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")

    return _capa_to_response(capa)


@router.post("/capas/{capa_id}/action", response_model=CAPAResponse)
async def add_action(capa_id: str, data: ActionRequest):
    """Add an action to CAPA."""
    service = get_quality_service()

    capa = service.add_action(
        capa_id,
        data.action_type,
        data.description,
        data.responsible,
        data.due_date,
    )
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")

    return _capa_to_response(capa)


@router.post("/capas/{capa_id}/verify", response_model=CAPAResponse)
async def verify_capa(capa_id: str, data: VerifyRequest, user_id: str = Query(...)):
    """Record CAPA verification."""
    service = get_quality_service()

    capa = service.verify_capa(capa_id, user_id, data.method, data.results)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")

    return _capa_to_response(capa)


# =============================================================================
# Inspection Endpoints
# =============================================================================


@router.post("/inspections", response_model=InspectionResponse)
async def create_inspection(data: InspectionCreateRequest, user_id: str = Query(...)):
    """Create a new inspection record."""
    service = get_quality_service()

    inspection = service.create_inspection(
        inspection_type=data.inspection_type,
        inspector_id=user_id,
        inspector_name=data.inspector_name,
        part_number=data.part_number,
        lot_number=data.lot_number,
        po_id=data.po_id,
        quantity_inspected=Decimal(str(data.quantity_inspected)),
    )

    return _inspection_to_response(inspection)


@router.post("/inspections/{inspection_id}/complete", response_model=InspectionResponse)
async def complete_inspection(
    inspection_id: str,
    data: InspectionCompleteRequest,
    user_id: str = Query(...),
):
    """Complete an inspection with results."""
    service = get_quality_service()

    try:
        inspection = service.complete_inspection(
            inspection_id=inspection_id,
            result=data.result,
            quantity_accepted=Decimal(str(data.quantity_accepted)),
            quantity_rejected=Decimal(str(data.quantity_rejected)),
            defects=data.defects,
            measurements=data.measurements,
            create_ncr_if_failed=data.create_ncr_if_failed,
            inspector_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return _inspection_to_response(inspection)


@router.get("/inspections", response_model=list[InspectionResponse])
async def list_inspections(
    inspection_type: Optional[str] = None,
    result: Optional[str] = None,
    part_number: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """List inspections with filters."""
    service = get_quality_service()

    inspections = service.list_inspections(
        inspection_type=inspection_type,
        result=result,
        part_number=part_number,
        limit=limit,
    )

    return [_inspection_to_response(i) for i in inspections]


# =============================================================================
# Hold Endpoints
# =============================================================================


@router.post("/holds", response_model=HoldResponse)
async def create_hold(data: HoldCreateRequest, user_id: str = Query(...)):
    """Create a quality hold."""
    service = get_quality_service()

    hold = service.create_hold(
        reason=data.reason,
        hold_type=data.hold_type,
        placed_by=user_id,
        part_number=data.part_number,
        lot_number=data.lot_number,
        quantity=Decimal(str(data.quantity)),
        ncr_id=data.ncr_id,
        location_id=data.location_id,
    )

    return _hold_to_response(hold)


@router.post("/holds/{hold_id}/release", response_model=HoldResponse)
async def release_hold(
    hold_id: str,
    user_id: str = Query(...),
    notes: Optional[str] = None,
):
    """Release a quality hold."""
    service = get_quality_service()

    hold = service.release_hold(hold_id, user_id, notes)
    if not hold:
        raise HTTPException(status_code=404, detail="Hold not found")

    return _hold_to_response(hold)


@router.get("/holds", response_model=list[HoldResponse])
async def list_holds(
    active_only: bool = False,
    part_number: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """List quality holds."""
    service = get_quality_service()

    holds = service.list_holds(
        active_only=active_only,
        part_number=part_number,
        limit=limit,
    )

    return [_hold_to_response(h) for h in holds]


# =============================================================================
# Metrics
# =============================================================================


@router.get("/metrics", response_model=QualityMetricsResponse)
async def get_quality_metrics():
    """Get quality metrics summary."""
    service = get_quality_service()
    return service.get_quality_metrics()


# =============================================================================
# Helper Functions
# =============================================================================


def _ncr_to_response(ncr) -> NCRResponse:
    return NCRResponse(
        id=ncr.id,
        ncr_number=ncr.ncr_number,
        status=ncr.status.value,
        severity=ncr.severity.value,
        source=ncr.source.value,
        title=ncr.title,
        description=ncr.description,
        part_number=ncr.part_number,
        lot_number=ncr.lot_number,
        quantity_affected=float(ncr.quantity_affected),
        disposition=ncr.disposition.value if ncr.disposition else None,
        root_cause=ncr.root_cause,
        capa_id=ncr.capa_id,
        capa_required=ncr.capa_required,
        estimated_cost=float(ncr.estimated_cost),
        created_at=ncr.created_at.isoformat() if ncr.created_at else None,
    )


def _capa_to_response(capa) -> CAPAResponse:
    return CAPAResponse(
        id=capa.id,
        capa_number=capa.capa_number,
        capa_type=capa.capa_type.value,
        status=capa.status.value,
        priority=capa.priority,
        title=capa.title,
        description=capa.description,
        ncr_count=len(capa.ncr_ids),
        root_causes=capa.root_causes,
        action_count=len(capa.corrective_actions) + len(capa.preventive_actions),
        owner_id=capa.owner_id,
        due_date=capa.due_date.isoformat() if capa.due_date else None,
        eco_id=capa.eco_id,
        created_at=capa.created_at.isoformat() if capa.created_at else None,
    )


def _inspection_to_response(inspection) -> InspectionResponse:
    return InspectionResponse(
        id=inspection.id,
        inspection_number=inspection.inspection_number,
        inspection_type=inspection.inspection_type,
        part_number=inspection.part_number,
        lot_number=inspection.lot_number,
        quantity_inspected=float(inspection.quantity_inspected),
        quantity_accepted=float(inspection.quantity_accepted),
        quantity_rejected=float(inspection.quantity_rejected),
        result=inspection.result,
        defect_count=len(inspection.defects_found),
        ncr_id=inspection.ncr_id,
        inspector_name=inspection.inspector_name,
        inspection_date=inspection.inspection_date.isoformat() if inspection.inspection_date else None,
    )


def _hold_to_response(hold) -> HoldResponse:
    return HoldResponse(
        id=hold.id,
        hold_number=hold.hold_number,
        part_number=hold.part_number,
        lot_number=hold.lot_number,
        quantity=float(hold.quantity),
        reason=hold.reason,
        hold_type=hold.hold_type,
        is_active=hold.is_active,
        ncr_id=hold.ncr_id,
        placed_by=hold.placed_by,
        placed_at=hold.placed_at.isoformat() if hold.placed_at else None,
    )
