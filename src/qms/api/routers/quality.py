"""
Quality Management API Router

Endpoints for NCRs, CAPAs, inspections, and quality holds.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from qms.quality import (
    get_quality_service,
    NCRStatus,
    NCRSeverity,
    NCRSource,
    DispositionType,
    CAPAType,
    CAPAStatus,
)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class NCRCreate(BaseModel):
    """Create NCR request."""
    title: str
    description: str
    severity: NCRSeverity = NCRSeverity.MINOR
    source: NCRSource = NCRSource.IN_PROCESS
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    part_revision: Optional[str] = None
    lot_number: Optional[str] = None
    serial_numbers: list[str] = []
    quantity_affected: Decimal = Decimal("1")
    detected_by: Optional[str] = None
    project_id: Optional[str] = None


class NCRDisposition(BaseModel):
    """NCR disposition request."""
    disposition: DispositionType
    disposition_notes: str = ""
    disposition_by: str


class NCRInvestigation(BaseModel):
    """NCR investigation update."""
    root_cause: Optional[str] = None
    immediate_action: Optional[str] = None
    containment_action: Optional[str] = None


class CAPACreate(BaseModel):
    """Create CAPA request."""
    title: str
    description: str
    capa_type: CAPAType
    priority: str = "medium"
    problem_statement: str = ""
    ncr_ids: list[str] = []
    owner_id: Optional[str] = None
    due_date: Optional[date] = None


class CAPARootCause(BaseModel):
    """CAPA root cause analysis."""
    root_cause_method: str
    root_cause_analysis: str
    root_causes: list[str] = []
    contributing_factors: list[str] = []


class CAPAAction(BaseModel):
    """CAPA action item."""
    description: str
    action_type: str  # immediate, corrective, preventive
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None


class InspectionCreate(BaseModel):
    """Create inspection record."""
    inspection_type: str = "receiving"
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    lot_number: Optional[str] = None
    po_id: Optional[str] = None
    quantity_inspected: Decimal
    sample_size: Optional[int] = None


class InspectionResult(BaseModel):
    """Record inspection results."""
    result: str  # pass, fail, conditional
    quantity_accepted: Decimal
    quantity_rejected: Decimal = Decimal("0")
    inspector_id: str
    inspector_name: str
    defects_found: list[dict] = []
    measurements: list[dict] = []


class HoldCreate(BaseModel):
    """Create quality hold."""
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    lot_number: Optional[str] = None
    serial_numbers: list[str] = []
    quantity: Decimal
    reason: str
    hold_type: str = "pending_inspection"
    location_id: Optional[str] = None


class HoldRelease(BaseModel):
    """Release quality hold."""
    released_by: str
    release_notes: str = ""


# =============================================================================
# NCR Endpoints
# =============================================================================

@router.post("/ncrs", tags=["NCRs"])
async def create_ncr(data: NCRCreate):
    """Create a new Non-Conformance Report."""
    service = get_quality_service()
    ncr = service.create_ncr(
        title=data.title,
        description=data.description,
        severity=data.severity,
        source=data.source,
        part_id=data.part_id,
        part_number=data.part_number,
        part_revision=data.part_revision,
        lot_number=data.lot_number,
        serial_numbers=data.serial_numbers,
        quantity_affected=data.quantity_affected,
        detected_by=data.detected_by,
        project_id=data.project_id,
    )
    return ncr.to_dict()


@router.get("/ncrs", tags=["NCRs"])
async def list_ncrs(
    status: Optional[NCRStatus] = None,
    severity: Optional[NCRSeverity] = None,
    source: Optional[NCRSource] = None,
    part_number: Optional[str] = None,
    project_id: Optional[str] = None,
):
    """List NCRs with optional filters."""
    service = get_quality_service()
    ncrs = service.list_ncrs(
        status=status,
        severity=severity,
        source=source,
        part_number=part_number,
        project_id=project_id,
    )
    return [n.to_dict() for n in ncrs]


@router.get("/ncrs/{ncr_id}", tags=["NCRs"])
async def get_ncr(ncr_id: str):
    """Get NCR by ID."""
    service = get_quality_service()
    ncr = service.get_ncr(ncr_id)
    if not ncr:
        raise HTTPException(status_code=404, detail="NCR not found")
    return ncr.to_dict()


@router.post("/ncrs/{ncr_id}/open", tags=["NCRs"])
async def open_ncr(ncr_id: str):
    """Open an NCR for investigation."""
    service = get_quality_service()
    ncr = service.open_ncr(ncr_id)
    if not ncr:
        raise HTTPException(status_code=404, detail="NCR not found")
    return ncr.to_dict()


@router.post("/ncrs/{ncr_id}/investigate", tags=["NCRs"])
async def update_investigation(ncr_id: str, data: NCRInvestigation):
    """Update NCR investigation details."""
    service = get_quality_service()
    ncr = service.update_investigation(
        ncr_id=ncr_id,
        root_cause=data.root_cause,
        immediate_action=data.immediate_action,
        containment_action=data.containment_action,
    )
    if not ncr:
        raise HTTPException(status_code=404, detail="NCR not found")
    return ncr.to_dict()


@router.post("/ncrs/{ncr_id}/disposition", tags=["NCRs"])
async def disposition_ncr(ncr_id: str, data: NCRDisposition):
    """Set disposition for NCR."""
    service = get_quality_service()
    ncr = service.disposition_ncr(
        ncr_id=ncr_id,
        disposition=data.disposition,
        disposition_notes=data.disposition_notes,
        disposition_by=data.disposition_by,
    )
    if not ncr:
        raise HTTPException(status_code=404, detail="NCR not found")
    return ncr.to_dict()


@router.post("/ncrs/{ncr_id}/close", tags=["NCRs"])
async def close_ncr(ncr_id: str, closed_by: str = Query(...)):
    """Close an NCR."""
    service = get_quality_service()
    ncr = service.close_ncr(ncr_id, closed_by)
    if not ncr:
        raise HTTPException(status_code=404, detail="NCR not found")
    return ncr.to_dict()


@router.post("/ncrs/{ncr_id}/create-capa", tags=["NCRs"])
async def create_capa_from_ncr(
    ncr_id: str,
    capa_type: CAPAType = Query(...),
    owner_id: Optional[str] = None,
):
    """Create a CAPA from an NCR."""
    service = get_quality_service()
    capa = service.create_capa_from_ncr(ncr_id, capa_type, owner_id)
    if not capa:
        raise HTTPException(status_code=404, detail="NCR not found")
    return capa.to_dict()


# =============================================================================
# CAPA Endpoints
# =============================================================================

@router.post("/capas", tags=["CAPAs"])
async def create_capa(data: CAPACreate):
    """Create a new CAPA."""
    service = get_quality_service()
    capa = service.create_capa(
        title=data.title,
        description=data.description,
        capa_type=data.capa_type,
        priority=data.priority,
        problem_statement=data.problem_statement,
        ncr_ids=data.ncr_ids,
        owner_id=data.owner_id,
        due_date=data.due_date,
    )
    return capa.to_dict()


@router.get("/capas", tags=["CAPAs"])
async def list_capas(
    status: Optional[CAPAStatus] = None,
    capa_type: Optional[CAPAType] = None,
    priority: Optional[str] = None,
    owner_id: Optional[str] = None,
):
    """List CAPAs with optional filters."""
    service = get_quality_service()
    capas = service.list_capas(
        status=status,
        capa_type=capa_type,
        priority=priority,
        owner_id=owner_id,
    )
    return [c.to_dict() for c in capas]


@router.get("/capas/{capa_id}", tags=["CAPAs"])
async def get_capa(capa_id: str):
    """Get CAPA by ID."""
    service = get_quality_service()
    capa = service.get_capa(capa_id)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    return capa.to_dict()


@router.post("/capas/{capa_id}/root-cause", tags=["CAPAs"])
async def update_root_cause(capa_id: str, data: CAPARootCause):
    """Update CAPA root cause analysis."""
    service = get_quality_service()
    capa = service.update_root_cause(
        capa_id=capa_id,
        root_cause_method=data.root_cause_method,
        root_cause_analysis=data.root_cause_analysis,
        root_causes=data.root_causes,
        contributing_factors=data.contributing_factors,
    )
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    return capa.to_dict()


@router.post("/capas/{capa_id}/actions", tags=["CAPAs"])
async def add_capa_action(capa_id: str, data: CAPAAction):
    """Add action to CAPA."""
    service = get_quality_service()
    capa = service.add_action(
        capa_id=capa_id,
        action_type=data.action_type,
        description=data.description,
        assigned_to=data.assigned_to,
        due_date=data.due_date,
    )
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    return capa.to_dict()


@router.post("/capas/{capa_id}/verify", tags=["CAPAs"])
async def verify_capa(
    capa_id: str,
    verified_by: str = Query(...),
    verification_results: str = Query(...),
):
    """Verify CAPA implementation."""
    service = get_quality_service()
    capa = service.verify_capa(capa_id, verified_by, verification_results)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    return capa.to_dict()


@router.post("/capas/{capa_id}/effectiveness", tags=["CAPAs"])
async def review_effectiveness(
    capa_id: str,
    effective: bool = Query(...),
    result: str = Query(...),
):
    """Record effectiveness review."""
    service = get_quality_service()
    capa = service.review_effectiveness(capa_id, effective, result)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    return capa.to_dict()


@router.post("/capas/{capa_id}/close", tags=["CAPAs"])
async def close_capa(capa_id: str, closed_by: str = Query(...)):
    """Close a CAPA."""
    service = get_quality_service()
    capa = service.close_capa(capa_id, closed_by)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    return capa.to_dict()


# =============================================================================
# Inspection Endpoints
# =============================================================================

@router.post("/inspections", tags=["Inspections"])
async def create_inspection(data: InspectionCreate):
    """Create a new inspection record."""
    service = get_quality_service()
    inspection = service.create_inspection(
        inspection_type=data.inspection_type,
        part_id=data.part_id,
        part_number=data.part_number,
        lot_number=data.lot_number,
        po_id=data.po_id,
        quantity_inspected=data.quantity_inspected,
        sample_size=data.sample_size,
    )
    return inspection.to_dict()


@router.get("/inspections", tags=["Inspections"])
async def list_inspections(
    inspection_type: Optional[str] = None,
    result: Optional[str] = None,
    part_number: Optional[str] = None,
    lot_number: Optional[str] = None,
):
    """List inspections with optional filters."""
    service = get_quality_service()
    inspections = service.list_inspections(
        inspection_type=inspection_type,
        result=result,
        part_number=part_number,
        lot_number=lot_number,
    )
    return [i.to_dict() for i in inspections]


@router.get("/inspections/{inspection_id}", tags=["Inspections"])
async def get_inspection(inspection_id: str):
    """Get inspection by ID."""
    service = get_quality_service()
    inspection = service.get_inspection(inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return inspection.to_dict()


@router.post("/inspections/{inspection_id}/complete", tags=["Inspections"])
async def complete_inspection(inspection_id: str, data: InspectionResult):
    """Complete an inspection with results."""
    service = get_quality_service()
    inspection = service.complete_inspection(
        inspection_id=inspection_id,
        result=data.result,
        quantity_accepted=data.quantity_accepted,
        quantity_rejected=data.quantity_rejected,
        inspector_id=data.inspector_id,
        inspector_name=data.inspector_name,
        defects_found=data.defects_found,
        measurements=data.measurements,
    )
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return inspection.to_dict()


# =============================================================================
# Quality Hold Endpoints
# =============================================================================

@router.post("/holds", tags=["Holds"])
async def create_hold(data: HoldCreate, placed_by: str = Query(...)):
    """Create a quality hold."""
    service = get_quality_service()
    hold = service.create_hold(
        part_id=data.part_id,
        part_number=data.part_number,
        lot_number=data.lot_number,
        serial_numbers=data.serial_numbers,
        quantity=data.quantity,
        reason=data.reason,
        hold_type=data.hold_type,
        location_id=data.location_id,
        placed_by=placed_by,
    )
    return hold.to_dict()


@router.get("/holds", tags=["Holds"])
async def list_holds(
    active_only: bool = True,
    part_number: Optional[str] = None,
    lot_number: Optional[str] = None,
    hold_type: Optional[str] = None,
):
    """List quality holds."""
    service = get_quality_service()
    holds = service.list_holds(
        active_only=active_only,
        part_number=part_number,
        lot_number=lot_number,
        hold_type=hold_type,
    )
    return [h.to_dict() for h in holds]


@router.get("/holds/{hold_id}", tags=["Holds"])
async def get_hold(hold_id: str):
    """Get hold by ID."""
    service = get_quality_service()
    hold = service.get_hold(hold_id)
    if not hold:
        raise HTTPException(status_code=404, detail="Hold not found")
    return hold.to_dict()


@router.post("/holds/{hold_id}/release", tags=["Holds"])
async def release_hold(hold_id: str, data: HoldRelease):
    """Release a quality hold."""
    service = get_quality_service()
    hold = service.release_hold(
        hold_id=hold_id,
        released_by=data.released_by,
        release_notes=data.release_notes,
    )
    if not hold:
        raise HTTPException(status_code=404, detail="Hold not found")
    return hold.to_dict()


# =============================================================================
# Statistics
# =============================================================================

@router.get("/statistics", tags=["Statistics"])
async def get_quality_statistics():
    """Get quality management statistics."""
    service = get_quality_service()
    return service.get_statistics()
