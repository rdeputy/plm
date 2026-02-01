"""Inventory Management module."""
from .models import (
    InventoryLocation,
    InventoryItem,
    InventoryTransaction,
    TransactionType,
    StockLevel,
)

# Defer imports that depend on db.models to avoid circular imports
# Import these at runtime using: from plm.inventory import InventoryRepository


def __getattr__(name: str):
    """Lazy import for classes that depend on db.models."""
    if name == "InventoryRepository":
        from .repository import InventoryRepository

        return InventoryRepository
    if name == "InventoryService":
        from .service import InventoryService

        return InventoryService
    if name == "InventoryError":
        from .service import InventoryError

        return InventoryError
    if name == "InsufficientStockError":
        from .service import InsufficientStockError

        return InsufficientStockError
    if name == "LocationNotFoundError":
        from .service import LocationNotFoundError

        return LocationNotFoundError
    if name == "InvalidTransactionError":
        from .service import InvalidTransactionError

        return InvalidTransactionError
    if name == "ReorderSuggestion":
        from .service import ReorderSuggestion

        return ReorderSuggestion
    if name == "TransferRequest":
        from .service import TransferRequest

        return TransferRequest
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Models
    "InventoryLocation",
    "InventoryItem",
    "InventoryTransaction",
    "TransactionType",
    "StockLevel",
    # Repository
    "InventoryRepository",
    # Service
    "InventoryService",
    "InventoryError",
    "InsufficientStockError",
    "LocationNotFoundError",
    "InvalidTransactionError",
    "ReorderSuggestion",
    "TransferRequest",
]
