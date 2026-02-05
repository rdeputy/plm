"""
Warranty Management API Router

Endpoints for warranty registration, claims, and RMAs.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from plm.warranty import (
    get_warranty_service,
    WarrantyType,
    WarrantyStatus,
    ClaimStatus,
    ClaimType,
    RMAStatus,
    DispositionAction,
    FailureCategory,
)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class WarrantyRegistrationCreate(BaseModel):
    """Create warranty registration."""
    part_id: str
    part_number: str
    serial_number: str
    customer_name: str
    purchase_date: date
    warranty_months: int = 12
    warranty_type: WarrantyType = WarrantyType.STANDARD
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    lot_number: Optional[str] = None
    invoice_number: Optional[str] = None
    terms: str = ""


class WarrantyExtend(BaseModel):
    """Extend warranty request."""
    additional_months: int
    extended_terms: str = ""


class WarrantyTransfer(BaseModel):
    """Transfer warranty to new owner."""
    new_customer_name: str
    new_customer_email: Optional[str] = None
    new_customer_phone: Optional[str] = None
    new_customer_address: Optional[str] = None


class ClaimCreate(BaseModel):
    """Create warranty claim."""
    warranty_id: str
    title: str
    description: str
    claim_type: ClaimType = ClaimType.DEFECT
    priority: str = "medium"
    contact_name: str = ""
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    failure_date: Optional[date] = None


class ClaimReview(BaseModel):
    """Review claim."""
    reviewer_id: str
    notes: str = ""


class ClaimDecision(BaseModel):
    """Approve or deny claim."""
    decision: str = Field(..., pattern="^(approved|denied)$")
    decider_id: str
    reason: str = ""
    estimated_cost: Optional[Decimal] = None


class ClaimClose(BaseModel):
    """Close a claim."""
    resolution: str
    closed_by: str
    actual_cost: Optional[Decimal] = None
    labor_cost: Optional[Decimal] = None
    parts_cost: Optional[Decimal] = None
    shipping_cost: Optional[Decimal] = None


class RMACreate(BaseModel):
    """Create RMA."""
    claim_id: str
    ship_to_address: str
    quantity: int = 1


class RMAShipping(BaseModel):
    """Update shipping info."""
    carrier: str
    tracking_number: str
    shipped_date: Optional[date] = None


class RMAReceive(BaseModel):
    """Receive RMA item."""
    received_by: str
    condition: str = ""


class RMAInspection(BaseModel):
    """Record inspection results."""
    inspector_id: str
    failure_confirmed: bool
    failure_category: Optional[FailureCategory] = None
    failure_description: str = ""
    root_cause: str = ""
    inspection_notes: str = ""


class RMADisposition(BaseModel):
    """Set RMA disposition."""
    disposition: DispositionAction
    disposition_by: str
    notes: str = ""
    replacement_serial: Optional[str] = None
    refund_amount: Optional[Decimal] = None
    credit_amount: Optional[Decimal] = None


class RMARepairComplete(BaseModel):
    """Complete repair."""
    labor_cost: Decimal
    parts_cost: Decimal


class RMAShipBack(BaseModel):
    """Ship item back to customer."""
    carrier: str
    tracking_number: str
    shipping_cost: Decimal = Decimal("0")


class PolicyCreate(BaseModel):
    """Create warranty policy."""
    policy_code: str
    name: str
    duration_months: int
    warranty_type: WarrantyType = WarrantyType.STANDARD
    coverage_description: str = ""
    exclusions: str = ""
    part_id: Optional[str] = None
    part_category: Optional[str] = None
    transferable: bool = False


# =============================================================================
# Warranty Registration Endpoints
# =============================================================================

@router.post("/registrations", tags=["Registrations"])
async def register_warranty(data: WarrantyRegistrationCreate):
    """Register a new warranty for a serialized product."""
    service = get_warranty_service()
    reg = service.register_warranty(
        part_id=data.part_id,
        part_number=data.part_number,
        serial_number=data.serial_number,
        customer_name=data.customer_name,
        purchase_date=data.purchase_date,
        warranty_months=data.warranty_months,
        warranty_type=data.warranty_type,
        customer_email=data.customer_email,
        customer_phone=data.customer_phone,
        customer_address=data.customer_address,
        lot_number=data.lot_number,
        invoice_number=data.invoice_number,
        terms=data.terms,
    )
    return reg.to_dict()


@router.get("/registrations", tags=["Registrations"])
async def list_registrations(
    status: Optional[WarrantyStatus] = None,
    customer_name: Optional[str] = None,
    part_number: Optional[str] = None,
    expiring_within_days: Optional[int] = None,
):
    """List warranty registrations with optional filters."""
    service = get_warranty_service()
    regs = service.list_registrations(
        status=status,
        customer_name=customer_name,
        part_number=part_number,
        expiring_within_days=expiring_within_days,
    )
    return [r.to_dict() for r in regs]


@router.get("/registrations/{registration_id}", tags=["Registrations"])
async def get_registration(registration_id: str):
    """Get warranty registration by ID."""
    service = get_warranty_service()
    reg = service.get_registration(registration_id)
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    return reg.to_dict()


@router.get("/check/{serial_number}", tags=["Registrations"])
async def check_warranty_status(serial_number: str):
    """
    Check warranty status by serial number.

    Public endpoint for customers to verify warranty coverage.
    """
    service = get_warranty_service()
    return service.check_warranty_status(serial_number)


@router.post("/registrations/{registration_id}/extend", tags=["Registrations"])
async def extend_warranty(registration_id: str, data: WarrantyExtend):
    """Add extended warranty coverage."""
    service = get_warranty_service()
    reg = service.extend_warranty(
        registration_id=registration_id,
        additional_months=data.additional_months,
        extended_terms=data.extended_terms,
    )
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    return reg.to_dict()


@router.post("/registrations/{registration_id}/transfer", tags=["Registrations"])
async def transfer_warranty(registration_id: str, data: WarrantyTransfer):
    """Transfer warranty to new owner."""
    service = get_warranty_service()
    reg = service.transfer_warranty(
        registration_id=registration_id,
        new_customer_name=data.new_customer_name,
        new_customer_email=data.new_customer_email,
        new_customer_phone=data.new_customer_phone,
        new_customer_address=data.new_customer_address,
    )
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    return reg.to_dict()


@router.post("/registrations/{registration_id}/void", tags=["Registrations"])
async def void_registration(registration_id: str, reason: str = Query(...)):
    """Void a warranty registration."""
    service = get_warranty_service()
    reg = service.void_registration(registration_id, reason)
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    return reg.to_dict()


# =============================================================================
# Warranty Claims Endpoints
# =============================================================================

@router.post("/claims", tags=["Claims"])
async def create_claim(data: ClaimCreate):
    """Create a new warranty claim."""
    service = get_warranty_service()
    claim = service.create_claim(
        warranty_id=data.warranty_id,
        title=data.title,
        description=data.description,
        claim_type=data.claim_type,
        priority=data.priority,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        failure_date=data.failure_date,
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Warranty registration not found")
    return claim.to_dict()


@router.get("/claims", tags=["Claims"])
async def list_claims(
    warranty_id: Optional[str] = None,
    status: Optional[ClaimStatus] = None,
    claim_type: Optional[ClaimType] = None,
    priority: Optional[str] = None,
    part_number: Optional[str] = None,
):
    """List warranty claims with optional filters."""
    service = get_warranty_service()
    claims = service.list_claims(
        warranty_id=warranty_id,
        status=status,
        claim_type=claim_type,
        priority=priority,
        part_number=part_number,
    )
    return [c.to_dict() for c in claims]


@router.get("/claims/{claim_id}", tags=["Claims"])
async def get_claim(claim_id: str):
    """Get claim by ID."""
    service = get_warranty_service()
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim.to_dict()


@router.post("/claims/{claim_id}/review", tags=["Claims"])
async def review_claim(claim_id: str, data: ClaimReview):
    """Mark claim as under review."""
    service = get_warranty_service()
    claim = service.review_claim(
        claim_id=claim_id,
        reviewer_id=data.reviewer_id,
        notes=data.notes,
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim.to_dict()


@router.post("/claims/{claim_id}/decide", tags=["Claims"])
async def decide_claim(claim_id: str, data: ClaimDecision):
    """Approve or deny a claim."""
    service = get_warranty_service()

    if data.decision == "approved":
        claim = service.approve_claim(
            claim_id=claim_id,
            approver_id=data.decider_id,
            reason=data.reason,
            estimated_cost=data.estimated_cost,
        )
    else:
        claim = service.deny_claim(
            claim_id=claim_id,
            denier_id=data.decider_id,
            reason=data.reason,
        )

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim.to_dict()


@router.post("/claims/{claim_id}/close", tags=["Claims"])
async def close_claim(claim_id: str, data: ClaimClose):
    """Close a resolved claim."""
    service = get_warranty_service()
    claim = service.close_claim(
        claim_id=claim_id,
        resolution=data.resolution,
        closed_by=data.closed_by,
        actual_cost=data.actual_cost,
        labor_cost=data.labor_cost,
        parts_cost=data.parts_cost,
        shipping_cost=data.shipping_cost,
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim.to_dict()


# =============================================================================
# RMA Endpoints
# =============================================================================

@router.post("/rmas", tags=["RMAs"])
async def create_rma(data: RMACreate):
    """Create RMA for an approved claim."""
    service = get_warranty_service()
    rma = service.create_rma(
        claim_id=data.claim_id,
        ship_to_address=data.ship_to_address,
        quantity=data.quantity,
    )
    if not rma:
        raise HTTPException(status_code=404, detail="Claim not found")
    return rma.to_dict()


@router.get("/rmas", tags=["RMAs"])
async def list_rmas(
    claim_id: Optional[str] = None,
    status: Optional[RMAStatus] = None,
    part_number: Optional[str] = None,
):
    """List RMAs with optional filters."""
    service = get_warranty_service()
    rmas = service.list_rmas(
        claim_id=claim_id,
        status=status,
        part_number=part_number,
    )
    return [r.to_dict() for r in rmas]


@router.get("/rmas/{rma_id}", tags=["RMAs"])
async def get_rma(rma_id: str):
    """Get RMA by ID."""
    service = get_warranty_service()
    rma = service.get_rma(rma_id)
    if not rma:
        raise HTTPException(status_code=404, detail="RMA not found")
    return rma.to_dict()


@router.post("/rmas/{rma_id}/shipping", tags=["RMAs"])
async def update_rma_shipping(rma_id: str, data: RMAShipping):
    """Update RMA with customer shipping info."""
    service = get_warranty_service()
    rma = service.update_rma_shipping(
        rma_id=rma_id,
        carrier=data.carrier,
        tracking_number=data.tracking_number,
        shipped_date=data.shipped_date,
    )
    if not rma:
        raise HTTPException(status_code=404, detail="RMA not found")
    return rma.to_dict()


@router.post("/rmas/{rma_id}/receive", tags=["RMAs"])
async def receive_rma(rma_id: str, data: RMAReceive):
    """Record receipt of RMA item."""
    service = get_warranty_service()
    rma = service.receive_rma(
        rma_id=rma_id,
        received_by=data.received_by,
        condition=data.condition,
    )
    if not rma:
        raise HTTPException(status_code=404, detail="RMA not found")
    return rma.to_dict()


@router.post("/rmas/{rma_id}/inspect", tags=["RMAs"])
async def inspect_rma(rma_id: str, data: RMAInspection):
    """Record inspection results."""
    service = get_warranty_service()
    rma = service.inspect_rma(
        rma_id=rma_id,
        inspector_id=data.inspector_id,
        failure_confirmed=data.failure_confirmed,
        failure_category=data.failure_category,
        failure_description=data.failure_description,
        root_cause=data.root_cause,
        inspection_notes=data.inspection_notes,
    )
    if not rma:
        raise HTTPException(status_code=404, detail="RMA not found")
    return rma.to_dict()


@router.post("/rmas/{rma_id}/disposition", tags=["RMAs"])
async def disposition_rma(rma_id: str, data: RMADisposition):
    """Set disposition for RMA."""
    service = get_warranty_service()
    rma = service.disposition_rma(
        rma_id=rma_id,
        disposition=data.disposition,
        disposition_by=data.disposition_by,
        notes=data.notes,
        replacement_serial=data.replacement_serial,
        refund_amount=data.refund_amount,
        credit_amount=data.credit_amount,
    )
    if not rma:
        raise HTTPException(status_code=404, detail="RMA not found")
    return rma.to_dict()


@router.post("/rmas/{rma_id}/repair-complete", tags=["RMAs"])
async def complete_repair(rma_id: str, data: RMARepairComplete):
    """Mark repair as complete."""
    service = get_warranty_service()
    rma = service.complete_repair(
        rma_id=rma_id,
        labor_cost=data.labor_cost,
        parts_cost=data.parts_cost,
    )
    if not rma:
        raise HTTPException(status_code=404, detail="RMA not found")
    return rma.to_dict()


@router.post("/rmas/{rma_id}/ship-back", tags=["RMAs"])
async def ship_rma_back(rma_id: str, data: RMAShipBack):
    """Ship item back to customer."""
    service = get_warranty_service()
    rma = service.ship_rma_back(
        rma_id=rma_id,
        carrier=data.carrier,
        tracking_number=data.tracking_number,
        shipping_cost=data.shipping_cost,
    )
    if not rma:
        raise HTTPException(status_code=404, detail="RMA not found")
    return rma.to_dict()


@router.post("/rmas/{rma_id}/complete", tags=["RMAs"])
async def complete_rma(rma_id: str):
    """Mark RMA as complete."""
    service = get_warranty_service()
    rma = service.complete_rma(rma_id)
    if not rma:
        raise HTTPException(status_code=404, detail="RMA not found")
    return rma.to_dict()


@router.post("/rmas/{rma_id}/link-ncr", tags=["RMAs"])
async def link_rma_to_ncr(rma_id: str, ncr_id: str = Query(...)):
    """Link RMA to NCR in quality module."""
    service = get_warranty_service()
    rma = service.link_ncr(rma_id, ncr_id)
    if not rma:
        raise HTTPException(status_code=404, detail="RMA not found")
    return {"status": "linked", "rma_id": rma_id, "ncr_id": ncr_id}


# =============================================================================
# Warranty Policies
# =============================================================================

@router.post("/policies", tags=["Policies"])
async def create_policy(data: PolicyCreate):
    """Create a warranty policy template."""
    service = get_warranty_service()
    policy = service.create_policy(
        policy_code=data.policy_code,
        name=data.name,
        duration_months=data.duration_months,
        warranty_type=data.warranty_type,
        coverage_description=data.coverage_description,
        exclusions=data.exclusions,
        part_id=data.part_id,
        part_category=data.part_category,
        transferable=data.transferable,
    )
    return policy.to_dict()


@router.get("/policies", tags=["Policies"])
async def list_policies(active_only: bool = True):
    """List warranty policies."""
    service = get_warranty_service()
    policies = service.list_policies(active_only=active_only)
    return [p.to_dict() for p in policies]


@router.get("/policies/{policy_id}", tags=["Policies"])
async def get_policy(policy_id: str):
    """Get policy by ID."""
    service = get_warranty_service()
    policy = service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy.to_dict()


@router.get("/policies/for-part/{part_id}", tags=["Policies"])
async def get_policy_for_part(part_id: str):
    """Get applicable warranty policy for a part."""
    service = get_warranty_service()
    policy = service.get_policy_for_part(part_id)
    if not policy:
        raise HTTPException(status_code=404, detail="No policy found for this part")
    return policy.to_dict()


# =============================================================================
# Metrics and Reporting
# =============================================================================

@router.get("/metrics", tags=["Reporting"])
async def get_warranty_metrics():
    """Get aggregated warranty metrics."""
    service = get_warranty_service()
    metrics = service.get_metrics()
    return metrics.to_dict()


@router.get("/failure-analysis", tags=["Reporting"])
async def get_failure_analysis(
    part_number: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """Get failure analysis data."""
    service = get_warranty_service()
    return service.get_failure_analysis(
        part_number=part_number,
        date_from=date_from,
        date_to=date_to,
    )
