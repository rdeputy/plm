"""
PLM Database Layer

SQLAlchemy ORM models and database configuration.
"""

from .base import (
    Base,
    SessionLocal,
    engine,
    get_db,
    get_session,
    init_db,
    drop_db,
)
from .models import (
    # Parts
    PartModel,
    PartRevisionModel,
    # BOMs
    BOMModel,
    BOMItemModel,
    # Changes
    ChangeOrderModel,
    ChangeModel,
    ApprovalModel,
    ImpactAnalysisModel,
    # Inventory
    InventoryLocationModel,
    InventoryItemModel,
    InventoryTransactionModel,
    # Procurement
    VendorModel,
    PriceAgreementModel,
    PurchaseOrderModel,
    POItemModel,
    ReceiptModel,
    ReceiptItemModel,
)

__all__ = [
    # Base
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "get_session",
    "init_db",
    "drop_db",
    # Parts
    "PartModel",
    "PartRevisionModel",
    # BOMs
    "BOMModel",
    "BOMItemModel",
    # Changes
    "ChangeOrderModel",
    "ChangeModel",
    "ApprovalModel",
    "ImpactAnalysisModel",
    # Inventory
    "InventoryLocationModel",
    "InventoryItemModel",
    "InventoryTransactionModel",
    # Procurement
    "VendorModel",
    "PriceAgreementModel",
    "PurchaseOrderModel",
    "POItemModel",
    "ReceiptModel",
    "ReceiptItemModel",
]
