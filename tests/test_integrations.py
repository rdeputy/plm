"""
Tests for Integrations Module

Tests MRP integration models and service.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from plm.integrations.models import (
    ItemMasterSync,
    BOMSync,
    BOMLineSync,
    ECONotification,
    ECOLineSync,
    CostUpdate,
    InventoryStatus,
    SyncLogEntry,
    MRPIntegrationConfig,
    SyncStatus,
    SyncDirection,
    ChangeAction,
)


class TestItemMasterSync:
    """Tests for ItemMasterSync model."""

    def test_create_item_master_sync(self):
        """Test creating an item master sync record."""
        item = ItemMasterSync(
            item_id="item-001",
            item_number="PART-12345",
            revision="A",
            description="Widget Assembly",
            item_type="manufactured",
            uom="EA",
            lead_time_days=14,
            standard_cost=Decimal("125.50"),
            make_buy="make",
        )
        assert item.item_number == "PART-12345"
        assert item.item_type == "manufactured"
        assert item.standard_cost == Decimal("125.50")

    def test_item_master_sync_to_dict(self):
        """Test converting item sync to dictionary."""
        item = ItemMasterSync(
            item_id="item-001",
            item_number="PART-12345",
            revision="B",
            description="Updated Widget",
            standard_cost=Decimal("130.00"),
            eco_number="ECO-2024-001",
        )
        data = item.to_dict()
        assert data["itemNumber"] == "PART-12345"
        assert data["revision"] == "B"
        assert data["standardCost"] == 130.00
        assert data["ecoNumber"] == "ECO-2024-001"


class TestBOMSync:
    """Tests for BOMSync model."""

    def test_create_bom_sync(self):
        """Test creating a BOM sync record."""
        lines = [
            BOMLineSync(
                line_id="line-001",
                line_number=1,
                component_item_id="comp-001",
                component_item_number="COMP-001",
                component_revision="A",
                quantity=Decimal("2"),
            ),
            BOMLineSync(
                line_id="line-002",
                line_number=2,
                component_item_id="comp-002",
                component_item_number="COMP-002",
                component_revision="A",
                quantity=Decimal("4"),
            ),
        ]
        bom = BOMSync(
            bom_id="bom-001",
            bom_number="BOM-12345",
            revision="A",
            parent_item_id="item-001",
            parent_item_number="ASSY-001",
            parent_revision="A",
            lines=lines,
            bom_type="manufacturing",
        )
        assert bom.bom_number == "BOM-12345"
        assert len(bom.lines) == 2

    def test_bom_sync_to_dict(self):
        """Test converting BOM sync to dictionary."""
        bom = BOMSync(
            bom_id="bom-001",
            bom_number="BOM-12345",
            revision="A",
            parent_item_id="item-001",
            parent_item_number="ASSY-001",
            parent_revision="A",
            bom_type="engineering",
            eco_number="ECO-001",
        )
        data = bom.to_dict()
        assert data["bomNumber"] == "BOM-12345"
        assert data["parentItemNumber"] == "ASSY-001"
        assert data["bomType"] == "engineering"
        assert data["ecoNumber"] == "ECO-001"


class TestBOMLineSync:
    """Tests for BOMLineSync model."""

    def test_create_bom_line_sync(self):
        """Test creating a BOM line sync record."""
        line = BOMLineSync(
            line_id="line-001",
            line_number=1,
            component_item_id="comp-001",
            component_item_number="COMP-12345",
            component_revision="A",
            quantity=Decimal("5"),
            uom="EA",
            find_number="10",
            is_phantom=False,
            scrap_percent=Decimal("2.5"),
        )
        assert line.component_item_number == "COMP-12345"
        assert line.quantity == Decimal("5")
        assert line.scrap_percent == Decimal("2.5")

    def test_bom_line_sync_to_dict(self):
        """Test converting BOM line to dictionary."""
        line = BOMLineSync(
            line_id="line-001",
            line_number=10,
            component_item_id="comp-001",
            component_item_number="COMP-12345",
            component_revision="B",
            quantity=Decimal("3"),
            is_phantom=True,
        )
        data = line.to_dict()
        assert data["componentItemNumber"] == "COMP-12345"
        assert data["quantity"] == 3.0
        assert data["isPhantom"] is True


class TestECONotification:
    """Tests for ECONotification model."""

    def test_create_eco_notification(self):
        """Test creating an ECO notification."""
        lines = [
            ECOLineSync(
                line_id="eco-line-001",
                line_number=1,
                change_action=ChangeAction.REVISE,
                item_id="item-001",
                item_number="PART-12345",
                old_revision="A",
                new_revision="B",
            )
        ]
        eco = ECONotification(
            eco_id="eco-001",
            eco_number="ECO-2024-001",
            title="Widget Redesign",
            change_type="design",
            priority="high",
            reason="Cost reduction",
            effectivity_type="immediate",
            line_items=lines,
            affected_items=["item-001"],
        )
        assert eco.eco_number == "ECO-2024-001"
        assert len(eco.line_items) == 1

    def test_eco_notification_to_dict(self):
        """Test converting ECO notification to dictionary."""
        eco = ECONotification(
            eco_id="eco-001",
            eco_number="ECO-2024-001",
            title="Widget Update",
            change_type="engineering",
            priority="medium",
            reason="Performance improvement",
            effectivity_type="date",
            old_inventory_disposition="use_as_is",
        )
        data = eco.to_dict()
        assert data["ecoNumber"] == "ECO-2024-001"
        assert data["changeType"] == "engineering"
        assert data["oldInventoryDisposition"] == "use_as_is"

    def test_change_action_enums(self):
        """Test change action enums."""
        assert ChangeAction.ADD.value == "add"
        assert ChangeAction.REVISE.value == "revise"
        assert ChangeAction.DELETE.value == "delete"
        assert ChangeAction.REPLACE.value == "replace"


class TestCostUpdate:
    """Tests for CostUpdate model."""

    def test_create_cost_update(self):
        """Test creating a cost update."""
        cost = CostUpdate(
            item_id="item-001",
            item_number="PART-12345",
            standard_cost=Decimal("100.00"),
            actual_cost=Decimal("95.50"),
            material_cost=Decimal("60.00"),
            labor_cost=Decimal("25.00"),
            overhead_cost=Decimal("10.50"),
        )
        assert cost.standard_cost == Decimal("100.00")
        assert cost.actual_cost == Decimal("95.50")

    def test_cost_update_to_dict(self):
        """Test converting cost update to dictionary."""
        cost = CostUpdate(
            item_id="item-001",
            item_number="PART-12345",
            standard_cost=Decimal("100.00"),
            material_cost=Decimal("60.00"),
            labor_cost=Decimal("25.00"),
            overhead_cost=Decimal("15.00"),
            currency="USD",
        )
        data = cost.to_dict()
        assert data["itemNumber"] == "PART-12345"
        assert data["standardCost"] == 100.00
        assert data["materialCost"] == 60.00
        assert data["currency"] == "USD"


class TestInventoryStatus:
    """Tests for InventoryStatus model."""

    def test_create_inventory_status(self):
        """Test creating an inventory status."""
        inventory = InventoryStatus(
            item_id="item-001",
            item_number="PART-12345",
            on_hand=Decimal("500"),
            allocated=Decimal("100"),
            available=Decimal("400"),
            on_order=Decimal("200"),
        )
        assert inventory.on_hand == Decimal("500")
        assert inventory.available == Decimal("400")

    def test_inventory_status_to_dict(self):
        """Test converting inventory status to dictionary."""
        inventory = InventoryStatus(
            item_id="item-001",
            item_number="PART-12345",
            on_hand=Decimal("500"),
            allocated=Decimal("100"),
            available=Decimal("400"),
            on_order=Decimal("200"),
        )
        data = inventory.to_dict()
        assert data["itemNumber"] == "PART-12345"
        assert data["onHand"] == 500.0
        assert data["available"] == 400.0


class TestSyncLogEntry:
    """Tests for SyncLogEntry model."""

    def test_create_sync_log_entry(self):
        """Test creating a sync log entry."""
        entry = SyncLogEntry(
            id="log-001",
            timestamp=datetime.now(),
            direction=SyncDirection.PLM_TO_MRP,
            entity_type="item",
            entity_id="item-001",
            entity_number="PART-12345",
            status=SyncStatus.COMPLETED,
            action="sync",
            message="Item synced successfully",
            duration_ms=150,
        )
        assert entry.status == SyncStatus.COMPLETED
        assert entry.direction == SyncDirection.PLM_TO_MRP

    def test_sync_log_entry_to_dict(self):
        """Test converting sync log entry to dictionary."""
        entry = SyncLogEntry(
            id="log-001",
            timestamp=datetime.now(),
            direction=SyncDirection.MRP_TO_PLM,
            entity_type="cost",
            entity_id="item-001",
            entity_number="PART-12345",
            status=SyncStatus.COMPLETED,
            action="receive",
            duration_ms=50,
        )
        data = entry.to_dict()
        assert data["direction"] == "mrp_to_plm"
        assert data["entityType"] == "cost"
        assert data["status"] == "completed"

    def test_sync_status_enums(self):
        """Test sync status enums."""
        assert SyncStatus.PENDING.value == "pending"
        assert SyncStatus.IN_PROGRESS.value == "in_progress"
        assert SyncStatus.COMPLETED.value == "completed"
        assert SyncStatus.FAILED.value == "failed"
        assert SyncStatus.SKIPPED.value == "skipped"

    def test_sync_direction_enums(self):
        """Test sync direction enums."""
        assert SyncDirection.PLM_TO_MRP.value == "plm_to_mrp"
        assert SyncDirection.MRP_TO_PLM.value == "mrp_to_plm"
        assert SyncDirection.BIDIRECTIONAL.value == "bidirectional"


class TestMRPIntegrationConfig:
    """Tests for MRPIntegrationConfig model."""

    def test_create_config(self):
        """Test creating integration config."""
        config = MRPIntegrationConfig(
            mrp_base_url="http://mrp.example.com",
            api_key="secret-key",
            timeout_seconds=60,
            auto_sync_items=True,
            auto_sync_boms=True,
        )
        assert config.mrp_base_url == "http://mrp.example.com"
        assert config.timeout_seconds == 60

    def test_config_defaults(self):
        """Test config default values."""
        config = MRPIntegrationConfig()
        assert config.mrp_base_url == "http://localhost:3000"
        assert config.timeout_seconds == 30
        assert config.auto_sync_items is True
        assert config.max_retries == 3

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = MRPIntegrationConfig(
            mrp_base_url="http://mrp.example.com",
            auto_sync_items=True,
            auto_sync_boms=False,
            webhook_enabled=True,
        )
        data = config.to_dict()
        assert data["mrpBaseUrl"] == "http://mrp.example.com"
        assert data["autoSyncItems"] is True
        assert data["autoSyncBoms"] is False
        assert data["webhookEnabled"] is True
