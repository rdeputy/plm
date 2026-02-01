"""
Procurement API Router

Vendors, purchase orders, and receiving.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from plm.api.deps import get_db_session
from plm.procurement import (
    ProcurementRepository,
    ProcurementService,
    ProcurementError,
    VendorNotFoundError,
    PONotFoundError,
    InvalidPOStateError,
    POStatus,
)

router = APIRouter()


# ----- Pydantic Schemas -----


class VendorCreate(BaseModel):
    """Schema for creating a vendor."""

    name: str
    vendor_code: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "USA"
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    payment_terms: str = "Net 30"
    freight_terms: str = "FOB Origin"
    categories: list[str] = []


class VendorResponse(BaseModel):
    """Schema for vendor response."""

    id: str
    name: str
    vendor_code: str
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    country: str
    phone: Optional[str]
    email: Optional[str]
    payment_terms: str
    freight_terms: str
    categories: list[str]
    on_time_rate: float
    quality_rate: float
    is_approved: bool
    is_active: bool


class POItemCreate(BaseModel):
    """Schema for PO line item."""

    part_id: str
    part_number: str
    description: str
    quantity: float
    unit_of_measure: str = "EA"
    unit_price: Optional[float] = None
    required_date: Optional[date] = None
    project_id: Optional[str] = None


class POCreate(BaseModel):
    """Schema for creating a purchase order."""

    vendor_id: str
    items: list[POItemCreate]
    ship_to_location_id: Optional[str] = None
    ship_to_address: Optional[str] = None
    required_date: Optional[date] = None
    project_id: Optional[str] = None
    notes: Optional[str] = None


class POItemResponse(BaseModel):
    """Schema for PO item response."""

    id: str
    line_number: int
    part_id: str
    part_number: str
    description: str
    quantity: float
    received_quantity: float
    open_quantity: float
    unit_price: float
    extended_price: float
    required_date: Optional[date]
    promised_date: Optional[date]
    is_closed: bool


class POResponse(BaseModel):
    """Schema for purchase order response."""

    id: str
    po_number: str
    vendor_id: str
    vendor_name: str
    status: str
    items: list[POItemResponse]
    subtotal: float
    tax: float
    shipping: float
    total: float
    order_date: Optional[date]
    required_date: Optional[date]
    promised_date: Optional[date]
    ship_to_address: Optional[str]
    freight_terms: str
    payment_terms: str
    project_id: Optional[str]
    notes: Optional[str]
    created_by: str
    approved_by: Optional[str]


class ReceiveItemCreate(BaseModel):
    """Schema for receiving a PO item."""

    po_item_id: str
    quantity_received: float
    quantity_accepted: Optional[float] = None
    quantity_rejected: float = 0
    lot_number: Optional[str] = None
    serial_numbers: list[str] = []
    location_id: Optional[str] = None
    inspection_required: bool = False


class ReceiveCreate(BaseModel):
    """Schema for receiving goods."""

    items: list[ReceiveItemCreate]
    location_id: Optional[str] = None
    packing_slip: Optional[str] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None


class ReceiptResponse(BaseModel):
    """Schema for receipt response."""

    id: str
    receipt_number: str
    po_id: str
    po_number: str
    vendor_id: str
    receipt_date: date
    packing_slip: Optional[str]
    carrier: Optional[str]
    tracking_number: Optional[str]
    received_by: str
    is_complete: bool


# ----- Vendor Endpoints -----


@router.get("/vendors", response_model=list[VendorResponse])
async def list_vendors(
    is_active: bool = Query(True),
    is_approved: Optional[bool] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """List vendors."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)
    vendors = service.list_vendors(
        is_active=is_active, is_approved=is_approved, category=category
    )
    return [_vendor_to_response(v) for v in vendors]


@router.post("/vendors", response_model=VendorResponse, status_code=201)
async def create_vendor(
    vendor: VendorCreate,
    db: Session = Depends(get_db_session),
):
    """Create a new vendor."""
    from plm.procurement import Vendor
    from uuid import uuid4

    repo = ProcurementRepository(db)
    service = ProcurementService(repo)

    v = Vendor(
        id=str(uuid4()),
        name=vendor.name,
        vendor_code=vendor.vendor_code,
        address=vendor.address,
        city=vendor.city,
        state=vendor.state,
        postal_code=vendor.postal_code,
        country=vendor.country,
        phone=vendor.phone,
        email=vendor.email,
        website=vendor.website,
        payment_terms=vendor.payment_terms,
        freight_terms=vendor.freight_terms,
        categories=vendor.categories,
    )
    v = service.create_vendor(v)
    db.commit()

    return _vendor_to_response(v)


@router.get("/vendors/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: str,
    db: Session = Depends(get_db_session),
):
    """Get a vendor by ID."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)
    vendor = service.get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return _vendor_to_response(vendor)


@router.get("/vendors/{vendor_id}/performance")
async def get_vendor_performance(
    vendor_id: str,
    db: Session = Depends(get_db_session),
):
    """Get vendor performance metrics."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)

    try:
        perf = service.get_vendor_performance(vendor_id)
        return {
            "vendor_id": perf.vendor_id,
            "vendor_name": perf.vendor_name,
            "total_orders": perf.total_orders,
            "total_value": float(perf.total_value),
            "on_time_deliveries": perf.on_time_deliveries,
            "late_deliveries": perf.late_deliveries,
            "on_time_rate": perf.on_time_rate,
            "quality_accepts": float(perf.quality_accepts),
            "quality_rejects": float(perf.quality_rejects),
            "quality_rate": perf.quality_rate,
            "avg_lead_time_days": perf.avg_lead_time_days,
        }
    except VendorNotFoundError:
        raise HTTPException(status_code=404, detail="Vendor not found")


# ----- Purchase Order Endpoints -----


@router.get("/orders", response_model=list[POResponse])
async def list_purchase_orders(
    vendor_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """List purchase orders."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)

    po_status = POStatus(status) if status else None
    pos = service.list_purchase_orders(
        vendor_id=vendor_id, status=po_status, project_id=project_id
    )
    return [_po_to_response(po) for po in pos]


@router.post("/orders", response_model=POResponse, status_code=201)
async def create_purchase_order(
    po: POCreate,
    created_by: str = Query("system"),
    db: Session = Depends(get_db_session),
):
    """Create a new purchase order."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)

    try:
        items = [item.model_dump() for item in po.items]
        result = service.create_purchase_order(
            vendor_id=po.vendor_id,
            items=items,
            ship_to_location_id=po.ship_to_location_id,
            ship_to_address=po.ship_to_address,
            required_date=po.required_date,
            project_id=po.project_id,
            created_by=created_by,
            notes=po.notes,
        )
        db.commit()
        return _po_to_response(result)
    except VendorNotFoundError:
        raise HTTPException(status_code=404, detail="Vendor not found")
    except ProcurementError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders/{po_id}", response_model=POResponse)
async def get_purchase_order(
    po_id: str,
    db: Session = Depends(get_db_session),
):
    """Get a purchase order by ID."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)
    po = service.get_purchase_order(po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return _po_to_response(po)


@router.post("/orders/{po_id}/submit", response_model=POResponse)
async def submit_purchase_order(
    po_id: str,
    db: Session = Depends(get_db_session),
):
    """Submit a PO for approval."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)

    try:
        result = service.submit_for_approval(po_id)
        db.commit()
        return _po_to_response(result)
    except PONotFoundError:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    except InvalidPOStateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{po_id}/approve", response_model=POResponse)
async def approve_purchase_order(
    po_id: str,
    approved_by: str = Query(...),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """Approve a purchase order."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)

    try:
        result = service.approve_purchase_order(po_id, approved_by, notes)
        db.commit()
        return _po_to_response(result)
    except PONotFoundError:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    except InvalidPOStateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{po_id}/send", response_model=POResponse)
async def send_purchase_order(
    po_id: str,
    db: Session = Depends(get_db_session),
):
    """Mark PO as sent to vendor."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)

    try:
        result = service.send_purchase_order(po_id)
        db.commit()
        return _po_to_response(result)
    except PONotFoundError:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    except InvalidPOStateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{po_id}/acknowledge", response_model=POResponse)
async def acknowledge_purchase_order(
    po_id: str,
    promised_date: Optional[date] = Query(None),
    db: Session = Depends(get_db_session),
):
    """Vendor acknowledges PO."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)

    try:
        result = service.acknowledge_purchase_order(po_id, promised_date)
        db.commit()
        return _po_to_response(result)
    except PONotFoundError:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    except InvalidPOStateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{po_id}/cancel", response_model=POResponse)
async def cancel_purchase_order(
    po_id: str,
    reason: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Cancel a purchase order."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)

    try:
        result = service.cancel_purchase_order(po_id, reason)
        db.commit()
        return _po_to_response(result)
    except PONotFoundError:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    except InvalidPOStateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{po_id}/close", response_model=POResponse)
async def close_purchase_order(
    po_id: str,
    db: Session = Depends(get_db_session),
):
    """Close a fully received PO."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)

    try:
        result = service.close_purchase_order(po_id)
        db.commit()
        return _po_to_response(result)
    except PONotFoundError:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    except InvalidPOStateError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----- Receiving Endpoints -----


@router.post("/orders/{po_id}/receive", response_model=ReceiptResponse, status_code=201)
async def receive_goods(
    po_id: str,
    receipt: ReceiveCreate,
    received_by: str = Query("system"),
    db: Session = Depends(get_db_session),
):
    """Receive goods against a PO."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)

    try:
        items = [item.model_dump() for item in receipt.items]
        result = service.receive_goods(
            po_id=po_id,
            items=items,
            received_by=received_by,
            location_id=receipt.location_id,
            packing_slip=receipt.packing_slip,
            carrier=receipt.carrier,
            tracking_number=receipt.tracking_number,
            notes=receipt.notes,
        )
        db.commit()
        return ReceiptResponse(
            id=result.id,
            receipt_number=result.receipt_number,
            po_id=result.po_id,
            po_number=result.po_number,
            vendor_id=result.vendor_id,
            receipt_date=result.receipt_date,
            packing_slip=result.packing_slip,
            carrier=result.carrier,
            tracking_number=result.tracking_number,
            received_by=result.received_by,
            is_complete=result.is_complete,
        )
    except PONotFoundError:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    except (InvalidPOStateError, ProcurementError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/receipts", response_model=list[ReceiptResponse])
async def list_receipts(
    po_id: Optional[str] = Query(None),
    vendor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """List receipts."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)
    receipts = service.list_receipts(po_id=po_id, vendor_id=vendor_id)
    return [
        ReceiptResponse(
            id=r.id,
            receipt_number=r.receipt_number,
            po_id=r.po_id,
            po_number=r.po_number,
            vendor_id=r.vendor_id,
            receipt_date=r.receipt_date,
            packing_slip=r.packing_slip,
            carrier=r.carrier,
            tracking_number=r.tracking_number,
            received_by=r.received_by,
            is_complete=r.is_complete,
        )
        for r in receipts
    ]


# ----- Summary Endpoint -----


@router.get("/summary")
async def get_procurement_summary(
    vendor_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """Get procurement summary."""
    repo = ProcurementRepository(db)
    service = ProcurementService(repo)

    summary = service.get_po_summary(vendor_id=vendor_id, project_id=project_id)
    return {
        "total_orders": summary.total_orders,
        "total_value": float(summary.total_value),
        "by_status": summary.by_status,
        "open_value": float(summary.open_value),
        "received_value": float(summary.received_value),
    }


def _vendor_to_response(vendor) -> VendorResponse:
    """Convert vendor to response."""
    return VendorResponse(
        id=vendor.id,
        name=vendor.name,
        vendor_code=vendor.vendor_code,
        address=vendor.address,
        city=vendor.city,
        state=vendor.state,
        postal_code=vendor.postal_code,
        country=vendor.country,
        phone=vendor.phone,
        email=vendor.email,
        payment_terms=vendor.payment_terms,
        freight_terms=vendor.freight_terms,
        categories=vendor.categories,
        on_time_rate=vendor.on_time_rate,
        quality_rate=vendor.quality_rate,
        is_approved=vendor.is_approved,
        is_active=vendor.is_active,
    )


def _po_to_response(po) -> POResponse:
    """Convert PO to response."""
    return POResponse(
        id=po.id,
        po_number=po.po_number,
        vendor_id=po.vendor_id,
        vendor_name=po.vendor_name,
        status=po.status.value,
        items=[
            POItemResponse(
                id=item.id,
                line_number=item.line_number,
                part_id=item.part_id,
                part_number=item.part_number,
                description=item.description,
                quantity=float(item.quantity),
                received_quantity=float(item.received_quantity),
                open_quantity=float(item.open_quantity),
                unit_price=float(item.unit_price),
                extended_price=float(item.extended_price),
                required_date=item.required_date,
                promised_date=item.promised_date,
                is_closed=item.is_closed,
            )
            for item in po.items
        ],
        subtotal=float(po.subtotal),
        tax=float(po.tax),
        shipping=float(po.shipping),
        total=float(po.total),
        order_date=po.order_date,
        required_date=po.required_date,
        promised_date=po.promised_date,
        ship_to_address=po.ship_to_address,
        freight_terms=po.freight_terms,
        payment_terms=po.payment_terms,
        project_id=po.project_id,
        notes=po.notes,
        created_by=po.created_by,
        approved_by=po.approved_by,
    )
