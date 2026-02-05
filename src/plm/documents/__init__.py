"""Document Management for PLM."""
from .models import (
    DocumentType,
    DocumentStatus,
    CheckoutStatus,
    Document,
    DocumentVersion,
    DocumentLink,
)
from .dms_integration import (
    PLMDocumentService,
    get_document_service,
    UploadResult,
    SearchHit,
)

__all__ = [
    # Domain models
    "DocumentType",
    "DocumentStatus",
    "CheckoutStatus",
    "Document",
    "DocumentVersion",
    "DocumentLink",
    # DMS integration
    "PLMDocumentService",
    "get_document_service",
    "UploadResult",
    "SearchHit",
]
