"""Procurement module."""
from .models import (
    Vendor,
    VendorContact,
    PurchaseOrder,
    POItem,
    POStatus,
    PriceAgreement,
    Receipt,
    ReceiptItem,
)

# Defer imports that depend on db.models to avoid circular imports


def __getattr__(name: str):
    """Lazy import for classes that depend on db.models."""
    if name == "ProcurementRepository":
        from .repository import ProcurementRepository

        return ProcurementRepository
    if name == "ProcurementService":
        from .service import ProcurementService

        return ProcurementService
    if name == "ProcurementError":
        from .service import ProcurementError

        return ProcurementError
    if name == "VendorNotFoundError":
        from .service import VendorNotFoundError

        return VendorNotFoundError
    if name == "PONotFoundError":
        from .service import PONotFoundError

        return PONotFoundError
    if name == "InvalidPOStateError":
        from .service import InvalidPOStateError

        return InvalidPOStateError
    if name == "ReceiptError":
        from .service import ReceiptError

        return ReceiptError
    if name == "VendorPerformance":
        from .service import VendorPerformance

        return VendorPerformance
    if name == "POSummary":
        from .service import POSummary

        return POSummary
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Models
    "Vendor",
    "VendorContact",
    "PurchaseOrder",
    "POItem",
    "POStatus",
    "PriceAgreement",
    "Receipt",
    "ReceiptItem",
    # Repository
    "ProcurementRepository",
    # Service
    "ProcurementService",
    "ProcurementError",
    "VendorNotFoundError",
    "PONotFoundError",
    "InvalidPOStateError",
    "ReceiptError",
    "VendorPerformance",
    "POSummary",
]
