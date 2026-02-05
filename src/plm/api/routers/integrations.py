"""
PLM Integrations API Router

Endpoints for MRP and other system integrations.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from plm.integrations import (
    get_mrp_integration_service,
    SyncStatus,
)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ItemSyncRequest(BaseModel):
    """Request to sync item to MRP."""
    item_id: str
    item_number: str
    revision: str
    description: str
    item_type: str = "purchased"
    uom: str = "EA"
    lead_time_days: int = 0
    standard_cost: Decimal = Decimal("0")
    make_buy: str = "buy"
    eco_number: Optional[str] = None


class BOMLineRequest(BaseModel):
    """BOM line for sync."""
    component_item_id: str
    component_item_number: str
    component_revision: str = "A"
    quantity: Decimal = Decimal("1")
    uom: str = "EA"
    find_number: Optional[str] = None
    is_phantom: bool = False
    scrap_percent: Decimal = Decimal("0")


class BOMSyncRequest(BaseModel):
    """Request to sync BOM to MRP."""
    bom_id: str
    bom_number: str
    revision: str
    parent_item_id: str
    parent_item_number: str
    parent_revision: str
    lines: list[BOMLineRequest]
    bom_type: str = "manufacturing"
    eco_number: Optional[str] = None


class ECOLineRequest(BaseModel):
    """ECO line for notification."""
    item_id: str
    item_number: str
    change_action: str = "revise"
    old_revision: Optional[str] = None
    new_revision: Optional[str] = None
    bom_id: Optional[str] = None
    old_quantity: Optional[Decimal] = None
    new_quantity: Optional[Decimal] = None
    replacement_item_id: Optional[str] = None
    change_description: str = ""


class ECONotifyRequest(BaseModel):
    """Request to notify MRP of ECO."""
    eco_id: str
    eco_number: str
    title: str
    change_type: str
    priority: str
    reason: str
    effectivity_type: str
    line_items: list[ECOLineRequest]
    affected_items: list[str] = []
    affected_boms: list[str] = []
    effective_date: Optional[date] = None
    old_inventory_disposition: str = "use_as_is"


class CostUpdateRequest(BaseModel):
    """Cost update from MRP."""
    item_id: str
    item_number: str
    standard_cost: Decimal
    actual_cost: Optional[Decimal] = None
    material_cost: Decimal = Decimal("0")
    labor_cost: Decimal = Decimal("0")
    overhead_cost: Decimal = Decimal("0")
    currency: str = "USD"


class InventoryUpdateRequest(BaseModel):
    """Inventory update from MRP."""
    item_id: str
    item_number: str
    on_hand: Decimal
    allocated: Decimal = Decimal("0")
    available: Decimal = Decimal("0")
    on_order: Decimal = Decimal("0")


# =============================================================================
# PLM → MRP Endpoints (Push)
# =============================================================================

@router.post("/mrp/items/sync", tags=["MRP Integration"])
async def sync_item_to_mrp(data: ItemSyncRequest, background_tasks: BackgroundTasks):
    """
    Sync a released item to MRP.

    Called when:
    - Part is released in PLM
    - Part revision is released
    - ECO affecting part is implemented
    """
    service = get_mrp_integration_service()

    # Run sync in background
    async def do_sync():
        await service.sync_item_to_mrp(
            item_id=data.item_id,
            item_number=data.item_number,
            revision=data.revision,
            description=data.description,
            item_type=data.item_type,
            uom=data.uom,
            lead_time_days=data.lead_time_days,
            standard_cost=data.standard_cost,
            make_buy=data.make_buy,
            eco_number=data.eco_number,
        )

    background_tasks.add_task(do_sync)

    return {
        "status": "queued",
        "message": f"Item {data.item_number} queued for MRP sync",
    }


@router.post("/mrp/boms/sync", tags=["MRP Integration"])
async def sync_bom_to_mrp(data: BOMSyncRequest, background_tasks: BackgroundTasks):
    """
    Sync a released BOM to MRP.

    Called when:
    - BOM is released in PLM
    - ECO affecting BOM is implemented
    """
    service = get_mrp_integration_service()

    # Convert Pydantic models to dicts
    lines = [
        {
            "component_item_id": line.component_item_id,
            "component_item_number": line.component_item_number,
            "component_revision": line.component_revision,
            "quantity": line.quantity,
            "uom": line.uom,
            "find_number": line.find_number,
            "is_phantom": line.is_phantom,
            "scrap_percent": line.scrap_percent,
        }
        for line in data.lines
    ]

    async def do_sync():
        await service.sync_bom_to_mrp(
            bom_id=data.bom_id,
            bom_number=data.bom_number,
            revision=data.revision,
            parent_item_id=data.parent_item_id,
            parent_item_number=data.parent_item_number,
            parent_revision=data.parent_revision,
            lines=lines,
            bom_type=data.bom_type,
            eco_number=data.eco_number,
        )

    background_tasks.add_task(do_sync)

    return {
        "status": "queued",
        "message": f"BOM {data.bom_number} with {len(data.lines)} lines queued for MRP sync",
    }


@router.post("/mrp/ecos/notify", tags=["MRP Integration"])
async def notify_eco_to_mrp(data: ECONotifyRequest, background_tasks: BackgroundTasks):
    """
    Notify MRP of an approved/implemented ECO.

    Allows MRP to:
    - Update affected BOMs
    - Handle inventory disposition
    - Adjust planning for new revisions
    """
    service = get_mrp_integration_service()

    # Convert Pydantic models to dicts
    line_items = [
        {
            "item_id": line.item_id,
            "item_number": line.item_number,
            "change_action": line.change_action,
            "old_revision": line.old_revision,
            "new_revision": line.new_revision,
            "bom_id": line.bom_id,
            "old_quantity": line.old_quantity,
            "new_quantity": line.new_quantity,
            "replacement_item_id": line.replacement_item_id,
            "change_description": line.change_description,
        }
        for line in data.line_items
    ]

    async def do_notify():
        await service.notify_eco_to_mrp(
            eco_id=data.eco_id,
            eco_number=data.eco_number,
            title=data.title,
            change_type=data.change_type,
            priority=data.priority,
            reason=data.reason,
            effectivity_type=data.effectivity_type,
            line_items=line_items,
            affected_items=data.affected_items,
            affected_boms=data.affected_boms,
            effective_date=data.effective_date.isoformat() if data.effective_date else None,
            old_inventory_disposition=data.old_inventory_disposition,
        )

    background_tasks.add_task(do_notify)

    return {
        "status": "queued",
        "message": f"ECO {data.eco_number} notification queued for MRP",
    }


# =============================================================================
# MRP → PLM Endpoints (Receive)
# =============================================================================

@router.post("/mrp/costs/update", tags=["MRP Integration"])
async def receive_cost_update(data: CostUpdateRequest):
    """
    Receive cost update from MRP.

    Allows PLM to track actual vs standard costs.
    """
    service = get_mrp_integration_service()

    cost = service.receive_cost_update(
        item_id=data.item_id,
        item_number=data.item_number,
        standard_cost=data.standard_cost,
        actual_cost=data.actual_cost,
        material_cost=data.material_cost,
        labor_cost=data.labor_cost,
        overhead_cost=data.overhead_cost,
        currency=data.currency,
    )

    return {
        "status": "received",
        "item_number": data.item_number,
        "cost": cost.to_dict(),
    }


@router.post("/mrp/inventory/update", tags=["MRP Integration"])
async def receive_inventory_update(data: InventoryUpdateRequest):
    """
    Receive inventory status from MRP.

    Allows PLM users to see stock levels.
    """
    service = get_mrp_integration_service()

    inventory = service.receive_inventory_status(
        item_id=data.item_id,
        item_number=data.item_number,
        on_hand=data.on_hand,
        allocated=data.allocated,
        available=data.available,
        on_order=data.on_order,
    )

    return {
        "status": "received",
        "item_number": data.item_number,
        "inventory": inventory.to_dict(),
    }


# =============================================================================
# Sync Status and Monitoring
# =============================================================================

@router.get("/mrp/sync/log", tags=["MRP Integration"])
async def get_sync_log(
    entity_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
):
    """Get sync log entries."""
    service = get_mrp_integration_service()

    status_enum = SyncStatus(status) if status else None
    entries = service.get_sync_log(
        entity_type=entity_type,
        status=status_enum,
        limit=limit,
    )

    return [e.to_dict() for e in entries]


@router.get("/mrp/sync/stats", tags=["MRP Integration"])
async def get_sync_stats():
    """Get sync statistics."""
    service = get_mrp_integration_service()
    return service.get_sync_stats()


@router.get("/mrp/sync/pending", tags=["MRP Integration"])
async def get_pending_syncs():
    """Get items pending sync."""
    service = get_mrp_integration_service()
    return service.get_pending_syncs()


# =============================================================================
# Webhooks (for real-time notifications)
# =============================================================================

@router.post("/mrp/webhook/item-released", tags=["MRP Webhooks"])
async def webhook_item_released(
    item_id: str,
    item_number: str,
    revision: str,
    background_tasks: BackgroundTasks,
):
    """
    Webhook triggered when an item is released in PLM.

    Automatically syncs the item to MRP.
    """
    service = get_mrp_integration_service()
    service.queue_for_sync("item", item_id, item_number, "sync")

    return {"status": "queued", "item_number": item_number}


@router.post("/mrp/webhook/bom-released", tags=["MRP Webhooks"])
async def webhook_bom_released(
    bom_id: str,
    bom_number: str,
    revision: str,
    background_tasks: BackgroundTasks,
):
    """
    Webhook triggered when a BOM is released in PLM.

    Automatically syncs the BOM to MRP.
    """
    service = get_mrp_integration_service()
    service.queue_for_sync("bom", bom_id, bom_number, "sync")

    return {"status": "queued", "bom_number": bom_number}


@router.post("/mrp/webhook/eco-approved", tags=["MRP Webhooks"])
async def webhook_eco_approved(
    eco_id: str,
    eco_number: str,
    background_tasks: BackgroundTasks,
):
    """
    Webhook triggered when an ECO is approved in PLM.

    Notifies MRP of the pending change.
    """
    service = get_mrp_integration_service()
    service.queue_for_sync("eco", eco_id, eco_number, "notify")

    return {"status": "queued", "eco_number": eco_number}
