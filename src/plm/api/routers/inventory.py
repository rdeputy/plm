"""
Inventory API Router

Inventory transactions, stock levels, and location management.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from plm.api.deps import get_db_session
from plm.inventory import (
    InventoryRepository,
    InventoryService,
    InventoryError,
    InsufficientStockError,
    TransactionType,
)

router = APIRouter()


# ----- Pydantic Schemas -----


class LocationCreate(BaseModel):
    """Schema for creating a location."""

    name: str
    location_type: str  # warehouse, jobsite, trailer, consignment
    address: Optional[str] = None
    project_id: Optional[str] = None
    vendor_id: Optional[str] = None


class LocationResponse(BaseModel):
    """Schema for location response."""

    id: str
    name: str
    location_type: str
    address: Optional[str]
    is_active: bool
    project_id: Optional[str]
    vendor_id: Optional[str]


class TransactionCreate(BaseModel):
    """Schema for creating a transaction."""

    part_id: str
    part_number: str
    location_id: str
    quantity: float
    unit_of_measure: str = "EA"
    unit_cost: Optional[float] = None
    po_id: Optional[str] = None
    project_id: Optional[str] = None
    work_order_id: Optional[str] = None
    lot_number: Optional[str] = None
    serial_number: Optional[str] = None
    notes: Optional[str] = None


class TransferCreate(BaseModel):
    """Schema for transfer between locations."""

    part_id: str
    part_number: str
    from_location_id: str
    to_location_id: str
    quantity: float
    notes: Optional[str] = None


class AdjustmentCreate(BaseModel):
    """Schema for inventory adjustment."""

    part_id: str
    part_number: str
    location_id: str
    new_quantity: float
    notes: Optional[str] = None


class ReorderPointUpdate(BaseModel):
    """Schema for setting reorder point."""

    reorder_point: float
    reorder_qty: Optional[float] = None


class InventoryItemResponse(BaseModel):
    """Schema for inventory item response."""

    id: str
    part_id: str
    part_number: str
    location_id: str
    on_hand: float
    allocated: float
    on_order: float
    available: float
    unit_cost: float
    total_value: float
    reorder_point: Optional[float]
    reorder_qty: Optional[float]
    needs_reorder: bool


class TransactionResponse(BaseModel):
    """Schema for transaction response."""

    id: str
    transaction_type: str
    part_id: str
    part_number: str
    quantity: float
    location_id: str
    from_location_id: Optional[str]
    to_location_id: Optional[str]
    unit_cost: float
    total_cost: float
    transaction_date: datetime
    created_by: str
    notes: Optional[str]


class ReorderSuggestionResponse(BaseModel):
    """Schema for reorder suggestion."""

    part_id: str
    part_number: str
    location_id: str
    current_available: float
    reorder_point: float
    suggested_qty: float
    priority: str


# ----- Endpoints -----


@router.get("/locations", response_model=list[LocationResponse])
async def list_locations(
    location_type: Optional[str] = Query(None),
    is_active: bool = Query(True),
    db: Session = Depends(get_db_session),
):
    """List inventory locations."""
    repo = InventoryRepository(db)
    service = InventoryService(repo)
    locations = service.list_locations(location_type=location_type, is_active=is_active)
    return [
        LocationResponse(
            id=loc.id,
            name=loc.name,
            location_type=loc.location_type,
            address=loc.address,
            is_active=loc.is_active,
            project_id=loc.project_id,
            vendor_id=loc.vendor_id,
        )
        for loc in locations
    ]


@router.post("/locations", response_model=LocationResponse, status_code=201)
async def create_location(
    location: LocationCreate,
    db: Session = Depends(get_db_session),
):
    """Create a new inventory location."""
    from plm.inventory import InventoryLocation
    from uuid import uuid4

    repo = InventoryRepository(db)
    service = InventoryService(repo)

    loc = InventoryLocation(
        id=str(uuid4()),
        name=location.name,
        location_type=location.location_type,
        address=location.address,
        project_id=location.project_id,
        vendor_id=location.vendor_id,
    )
    loc = service.create_location(loc)
    db.commit()

    return LocationResponse(
        id=loc.id,
        name=loc.name,
        location_type=loc.location_type,
        address=loc.address,
        is_active=loc.is_active,
        project_id=loc.project_id,
        vendor_id=loc.vendor_id,
    )


@router.get("/items", response_model=list[InventoryItemResponse])
async def list_inventory_items(
    location_id: Optional[str] = Query(None),
    part_id: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """List inventory items."""
    repo = InventoryRepository(db)

    if location_id:
        items = repo.list_items_by_location(location_id)
    elif part_id:
        items = repo.list_items_by_part(part_id)
    else:
        # Get all items by iterating locations
        locations = repo.list_locations()
        items = []
        for loc in locations:
            items.extend(repo.list_items_by_location(loc.id))

    return [_item_to_response(item) for item in items]


@router.get("/items/{part_id}/{location_id}", response_model=InventoryItemResponse)
async def get_inventory_item(
    part_id: str,
    location_id: str,
    db: Session = Depends(get_db_session),
):
    """Get inventory item for a part at a location."""
    repo = InventoryRepository(db)
    item = repo.get_item_by_part_location(part_id, location_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return _item_to_response(item)


@router.post("/receive", response_model=TransactionResponse, status_code=201)
async def receive_inventory(
    txn: TransactionCreate,
    created_by: str = Query("system"),
    db: Session = Depends(get_db_session),
):
    """Receive inventory (e.g., from a PO)."""
    repo = InventoryRepository(db)
    service = InventoryService(repo)

    try:
        result = service.receive(
            part_id=txn.part_id,
            part_number=txn.part_number,
            location_id=txn.location_id,
            quantity=Decimal(str(txn.quantity)),
            unit_cost=Decimal(str(txn.unit_cost or 0)),
            unit_of_measure=txn.unit_of_measure,
            po_id=txn.po_id,
            lot_number=txn.lot_number,
            serial_number=txn.serial_number,
            created_by=created_by,
            notes=txn.notes,
        )
        db.commit()
        return _txn_to_response(result)
    except InventoryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/issue", response_model=TransactionResponse, status_code=201)
async def issue_inventory(
    txn: TransactionCreate,
    created_by: str = Query("system"),
    allow_negative: bool = Query(False),
    db: Session = Depends(get_db_session),
):
    """Issue inventory (e.g., to a project)."""
    repo = InventoryRepository(db)
    service = InventoryService(repo)

    try:
        result = service.issue(
            part_id=txn.part_id,
            part_number=txn.part_number,
            location_id=txn.location_id,
            quantity=Decimal(str(txn.quantity)),
            unit_of_measure=txn.unit_of_measure,
            project_id=txn.project_id,
            work_order_id=txn.work_order_id,
            created_by=created_by,
            notes=txn.notes,
            allow_negative=allow_negative,
        )
        db.commit()
        return _txn_to_response(result)
    except InsufficientStockError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock: {e.available} available, {e.requested} requested",
        )
    except InventoryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfer", status_code=201)
async def transfer_inventory(
    transfer: TransferCreate,
    created_by: str = Query("system"),
    db: Session = Depends(get_db_session),
):
    """Transfer inventory between locations."""
    repo = InventoryRepository(db)
    service = InventoryService(repo)

    try:
        from_txn, to_txn = service.transfer(
            part_id=transfer.part_id,
            part_number=transfer.part_number,
            from_location_id=transfer.from_location_id,
            to_location_id=transfer.to_location_id,
            quantity=Decimal(str(transfer.quantity)),
            created_by=created_by,
            notes=transfer.notes,
        )
        db.commit()
        return {
            "from_transaction": _txn_to_response(from_txn),
            "to_transaction": _txn_to_response(to_txn),
        }
    except InsufficientStockError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock: {e.available} available, {e.requested} requested",
        )
    except InventoryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/adjust", response_model=TransactionResponse, status_code=201)
async def adjust_inventory(
    adjustment: AdjustmentCreate,
    created_by: str = Query("system"),
    db: Session = Depends(get_db_session),
):
    """Adjust inventory (count adjustment)."""
    repo = InventoryRepository(db)
    service = InventoryService(repo)

    try:
        result = service.adjust(
            part_id=adjustment.part_id,
            part_number=adjustment.part_number,
            location_id=adjustment.location_id,
            new_quantity=Decimal(str(adjustment.new_quantity)),
            created_by=created_by,
            notes=adjustment.notes,
        )
        db.commit()
        return _txn_to_response(result)
    except InventoryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/items/{part_id}/{location_id}/reorder-point")
async def set_reorder_point(
    part_id: str,
    location_id: str,
    update: ReorderPointUpdate,
    db: Session = Depends(get_db_session),
):
    """Set reorder point for an inventory item."""
    repo = InventoryRepository(db)
    service = InventoryService(repo)

    try:
        item = service.set_reorder_point(
            part_id=part_id,
            location_id=location_id,
            reorder_point=Decimal(str(update.reorder_point)),
            reorder_qty=Decimal(str(update.reorder_qty)) if update.reorder_qty else None,
        )
        db.commit()
        return _item_to_response(item)
    except InventoryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reorder-suggestions", response_model=list[ReorderSuggestionResponse])
async def get_reorder_suggestions(
    db: Session = Depends(get_db_session),
):
    """Get list of items that need reordering."""
    repo = InventoryRepository(db)
    service = InventoryService(repo)

    suggestions = service.get_reorder_suggestions()
    return [
        ReorderSuggestionResponse(
            part_id=s.part_id,
            part_number=s.part_number,
            location_id=s.location_id,
            current_available=float(s.current_available),
            reorder_point=float(s.reorder_point),
            suggested_qty=float(s.suggested_qty),
            priority=s.priority,
        )
        for s in suggestions
    ]


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    part_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db_session),
):
    """List inventory transactions."""
    repo = InventoryRepository(db)
    service = InventoryService(repo)

    txn_type = TransactionType(transaction_type) if transaction_type else None

    transactions = service.get_transaction_history(
        part_id=part_id,
        location_id=location_id,
        transaction_type=txn_type,
        limit=limit,
    )
    return [_txn_to_response(txn) for txn in transactions]


def _item_to_response(item) -> InventoryItemResponse:
    """Convert inventory item to response."""
    return InventoryItemResponse(
        id=item.id,
        part_id=item.part_id,
        part_number=item.part_number,
        location_id=item.location_id,
        on_hand=float(item.on_hand),
        allocated=float(item.allocated),
        on_order=float(item.on_order),
        available=float(item.available),
        unit_cost=float(item.unit_cost),
        total_value=float(item.total_value),
        reorder_point=float(item.reorder_point) if item.reorder_point else None,
        reorder_qty=float(item.reorder_qty) if item.reorder_qty else None,
        needs_reorder=item.needs_reorder(),
    )


def _txn_to_response(txn) -> TransactionResponse:
    """Convert transaction to response."""
    return TransactionResponse(
        id=txn.id,
        transaction_type=txn.transaction_type.value,
        part_id=txn.part_id,
        part_number=txn.part_number,
        quantity=float(txn.quantity),
        location_id=txn.location_id,
        from_location_id=txn.from_location_id,
        to_location_id=txn.to_location_id,
        unit_cost=float(txn.unit_cost),
        total_cost=float(txn.total_cost),
        transaction_date=txn.transaction_date,
        created_by=txn.created_by,
        notes=txn.notes,
    )
