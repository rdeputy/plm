"""
MRP Integration Service

Handles synchronization between PLM and MRP systems.
"""

import uuid
import httpx
from datetime import datetime
from decimal import Decimal
from typing import Optional

from .models import (
    ItemMasterSync,
    BOMSync,
    BOMLineSync,
    ECONotification,
    ECOLineSync,
    CostUpdate,
    InventoryStatus,
    SyncLogEntry,
    SyncStatus,
    SyncDirection,
    ChangeAction,
    MRPIntegrationConfig,
)


class MRPIntegrationService:
    """
    Service for PLM-MRP integration.

    Handles:
    - Pushing released items/BOMs/ECOs to MRP
    - Receiving cost and inventory updates from MRP
    - Webhook notifications for real-time sync
    """

    def __init__(self, config: Optional[MRPIntegrationConfig] = None):
        self.config = config or MRPIntegrationConfig()
        self._sync_log: list[SyncLogEntry] = []
        self._pending_syncs: dict[str, dict] = {}

        # HTTP client for MRP API calls
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {}
            if self.config.api_key:
                headers["X-API-Key"] = self.config.api_key
            self._client = httpx.AsyncClient(
                base_url=self.config.mrp_base_url,
                headers=headers,
                timeout=self.config.timeout_seconds,
            )
        return self._client

    def _log_sync(
        self,
        direction: SyncDirection,
        entity_type: str,
        entity_id: str,
        entity_number: str,
        status: SyncStatus,
        action: str = "",
        message: str = "",
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> SyncLogEntry:
        """Log a sync operation."""
        entry = SyncLogEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            direction=direction,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_number=entity_number,
            status=status,
            action=action,
            message=message,
            error=error,
            duration_ms=duration_ms,
        )
        self._sync_log.append(entry)
        return entry

    # =========================================================================
    # PLM → MRP: Push Operations
    # =========================================================================

    async def sync_item_to_mrp(
        self,
        item_id: str,
        item_number: str,
        revision: str,
        description: str,
        item_type: str = "purchased",
        uom: str = "EA",
        lead_time_days: int = 0,
        standard_cost: Decimal = Decimal("0"),
        make_buy: str = "buy",
        eco_number: Optional[str] = None,
        **kwargs
    ) -> SyncLogEntry:
        """
        Sync a released item to MRP.

        Called when:
        - Part is released in PLM
        - Part revision is released
        - ECO affecting part is implemented
        """
        start = datetime.now()

        item_data = ItemMasterSync(
            item_id=item_id,
            item_number=item_number,
            revision=revision,
            description=description,
            item_type=item_type,
            uom=uom,
            lead_time_days=lead_time_days,
            standard_cost=standard_cost,
            make_buy=make_buy,
            eco_number=eco_number,
            plm_released_at=datetime.now(),
            **kwargs
        )

        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/plm/items",
                json=item_data.to_dict(),
            )
            response.raise_for_status()

            duration = int((datetime.now() - start).total_seconds() * 1000)
            return self._log_sync(
                direction=SyncDirection.PLM_TO_MRP,
                entity_type="item",
                entity_id=item_id,
                entity_number=item_number,
                status=SyncStatus.COMPLETED,
                action="sync",
                message=f"Item {item_number} rev {revision} synced to MRP",
                duration_ms=duration,
            )

        except httpx.HTTPError as e:
            duration = int((datetime.now() - start).total_seconds() * 1000)
            return self._log_sync(
                direction=SyncDirection.PLM_TO_MRP,
                entity_type="item",
                entity_id=item_id,
                entity_number=item_number,
                status=SyncStatus.FAILED,
                action="sync",
                error=str(e),
                duration_ms=duration,
            )

    async def sync_bom_to_mrp(
        self,
        bom_id: str,
        bom_number: str,
        revision: str,
        parent_item_id: str,
        parent_item_number: str,
        parent_revision: str,
        lines: list[dict],
        bom_type: str = "manufacturing",
        eco_number: Optional[str] = None,
        **kwargs
    ) -> SyncLogEntry:
        """
        Sync a released BOM to MRP.

        Called when:
        - BOM is released in PLM
        - ECO affecting BOM is implemented
        """
        start = datetime.now()

        # Convert line dicts to BOMLineSync objects
        sync_lines = [
            BOMLineSync(
                line_id=line.get("id", str(uuid.uuid4())),
                line_number=line.get("line_number", i + 1),
                component_item_id=line["component_item_id"],
                component_item_number=line["component_item_number"],
                component_revision=line.get("component_revision", "A"),
                quantity=Decimal(str(line.get("quantity", 1))),
                uom=line.get("uom", "EA"),
                find_number=line.get("find_number"),
                is_phantom=line.get("is_phantom", False),
                scrap_percent=Decimal(str(line.get("scrap_percent", 0))),
            )
            for i, line in enumerate(lines)
        ]

        bom_data = BOMSync(
            bom_id=bom_id,
            bom_number=bom_number,
            revision=revision,
            parent_item_id=parent_item_id,
            parent_item_number=parent_item_number,
            parent_revision=parent_revision,
            bom_type=bom_type,
            lines=sync_lines,
            eco_number=eco_number,
            plm_released_at=datetime.now(),
            **kwargs
        )

        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/plm/boms",
                json=bom_data.to_dict(),
            )
            response.raise_for_status()

            duration = int((datetime.now() - start).total_seconds() * 1000)
            return self._log_sync(
                direction=SyncDirection.PLM_TO_MRP,
                entity_type="bom",
                entity_id=bom_id,
                entity_number=bom_number,
                status=SyncStatus.COMPLETED,
                action="sync",
                message=f"BOM {bom_number} rev {revision} with {len(lines)} lines synced to MRP",
                duration_ms=duration,
            )

        except httpx.HTTPError as e:
            duration = int((datetime.now() - start).total_seconds() * 1000)
            return self._log_sync(
                direction=SyncDirection.PLM_TO_MRP,
                entity_type="bom",
                entity_id=bom_id,
                entity_number=bom_number,
                status=SyncStatus.FAILED,
                action="sync",
                error=str(e),
                duration_ms=duration,
            )

    async def notify_eco_to_mrp(
        self,
        eco_id: str,
        eco_number: str,
        title: str,
        change_type: str,
        priority: str,
        reason: str,
        effectivity_type: str,
        line_items: list[dict],
        affected_items: list[str],
        affected_boms: list[str],
        effective_date: Optional[str] = None,
        old_inventory_disposition: str = "use_as_is",
        **kwargs
    ) -> SyncLogEntry:
        """
        Notify MRP of an approved/implemented ECO.

        Allows MRP to:
        - Update affected BOMs
        - Handle inventory disposition
        - Adjust planning for new revisions
        """
        start = datetime.now()

        # Convert line dicts to ECOLineSync objects
        sync_lines = [
            ECOLineSync(
                line_id=line.get("id", str(uuid.uuid4())),
                line_number=line.get("line_number", i + 1),
                change_action=ChangeAction(line.get("change_action", "revise")),
                item_id=line["item_id"],
                item_number=line["item_number"],
                old_revision=line.get("old_revision"),
                new_revision=line.get("new_revision"),
                bom_id=line.get("bom_id"),
                old_quantity=Decimal(str(line["old_quantity"])) if line.get("old_quantity") else None,
                new_quantity=Decimal(str(line["new_quantity"])) if line.get("new_quantity") else None,
                replacement_item_id=line.get("replacement_item_id"),
                change_description=line.get("change_description", ""),
            )
            for i, line in enumerate(line_items)
        ]

        eco_data = ECONotification(
            eco_id=eco_id,
            eco_number=eco_number,
            title=title,
            change_type=change_type,
            priority=priority,
            reason=reason,
            effectivity_type=effectivity_type,
            line_items=sync_lines,
            affected_items=affected_items,
            affected_boms=affected_boms,
            old_inventory_disposition=old_inventory_disposition,
            approved_at=datetime.now(),
            **kwargs
        )

        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/plm/ecos",
                json=eco_data.to_dict(),
            )
            response.raise_for_status()

            duration = int((datetime.now() - start).total_seconds() * 1000)
            return self._log_sync(
                direction=SyncDirection.PLM_TO_MRP,
                entity_type="eco",
                entity_id=eco_id,
                entity_number=eco_number,
                status=SyncStatus.COMPLETED,
                action="notify",
                message=f"ECO {eco_number} notification sent to MRP",
                duration_ms=duration,
            )

        except httpx.HTTPError as e:
            duration = int((datetime.now() - start).total_seconds() * 1000)
            return self._log_sync(
                direction=SyncDirection.PLM_TO_MRP,
                entity_type="eco",
                entity_id=eco_id,
                entity_number=eco_number,
                status=SyncStatus.FAILED,
                action="notify",
                error=str(e),
                duration_ms=duration,
            )

    # =========================================================================
    # MRP → PLM: Receive Operations
    # =========================================================================

    def receive_cost_update(
        self,
        item_id: str,
        item_number: str,
        standard_cost: Decimal,
        actual_cost: Optional[Decimal] = None,
        material_cost: Decimal = Decimal("0"),
        labor_cost: Decimal = Decimal("0"),
        overhead_cost: Decimal = Decimal("0"),
        currency: str = "USD",
    ) -> CostUpdate:
        """
        Receive cost update from MRP.

        Allows PLM to track actual vs standard costs.
        """
        cost_update = CostUpdate(
            item_id=item_id,
            item_number=item_number,
            standard_cost=standard_cost,
            actual_cost=actual_cost,
            material_cost=material_cost,
            labor_cost=labor_cost,
            overhead_cost=overhead_cost,
            currency=currency,
        )

        self._log_sync(
            direction=SyncDirection.MRP_TO_PLM,
            entity_type="cost",
            entity_id=item_id,
            entity_number=item_number,
            status=SyncStatus.COMPLETED,
            action="receive",
            message=f"Cost update received for {item_number}",
        )

        return cost_update

    def receive_inventory_status(
        self,
        item_id: str,
        item_number: str,
        on_hand: Decimal,
        allocated: Decimal = Decimal("0"),
        available: Decimal = Decimal("0"),
        on_order: Decimal = Decimal("0"),
    ) -> InventoryStatus:
        """
        Receive inventory status from MRP.

        Allows PLM users to see stock levels without
        accessing MRP directly.
        """
        inventory = InventoryStatus(
            item_id=item_id,
            item_number=item_number,
            on_hand=on_hand,
            allocated=allocated,
            available=available,
            on_order=on_order,
        )

        self._log_sync(
            direction=SyncDirection.MRP_TO_PLM,
            entity_type="inventory",
            entity_id=item_id,
            entity_number=item_number,
            status=SyncStatus.COMPLETED,
            action="receive",
            message=f"Inventory status received for {item_number}",
        )

        return inventory

    # =========================================================================
    # Sync Log and Status
    # =========================================================================

    def get_sync_log(
        self,
        entity_type: Optional[str] = None,
        status: Optional[SyncStatus] = None,
        limit: int = 100,
    ) -> list[SyncLogEntry]:
        """Get sync log entries."""
        results = self._sync_log

        if entity_type:
            results = [e for e in results if e.entity_type == entity_type]

        if status:
            results = [e for e in results if e.status == status]

        return sorted(results, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_sync_stats(self) -> dict:
        """Get sync statistics."""
        total = len(self._sync_log)
        completed = len([e for e in self._sync_log if e.status == SyncStatus.COMPLETED])
        failed = len([e for e in self._sync_log if e.status == SyncStatus.FAILED])

        by_type = {}
        for entry in self._sync_log:
            by_type[entry.entity_type] = by_type.get(entry.entity_type, 0) + 1

        return {
            "total_syncs": total,
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "by_entity_type": by_type,
        }

    def get_pending_syncs(self) -> list[dict]:
        """Get items pending sync."""
        return list(self._pending_syncs.values())

    def queue_for_sync(
        self,
        entity_type: str,
        entity_id: str,
        entity_number: str,
        action: str = "sync",
    ) -> None:
        """Queue an entity for sync (for batch processing)."""
        key = f"{entity_type}:{entity_id}"
        self._pending_syncs[key] = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "entity_number": entity_number,
            "action": action,
            "queued_at": datetime.now().isoformat(),
        }

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_mrp_service: Optional[MRPIntegrationService] = None


def get_mrp_integration_service() -> MRPIntegrationService:
    """Get the MRP integration service singleton."""
    global _mrp_service
    if _mrp_service is None:
        _mrp_service = MRPIntegrationService()
    return _mrp_service
