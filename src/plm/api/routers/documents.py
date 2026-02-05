"""
Document Management API Router

CRUD operations, check-in/check-out, versioning, and document links.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from plm.api.deps import get_db_session
from plm.db.models import (
    DocumentModel,
    DocumentVersionModel,
    DocumentLinkModel,
    PartModel,
    BOMModel,
    ChangeOrderModel,
)
from plm.documents.models import (
    DocumentType,
    DocumentStatus,
    CheckoutStatus,
    increment_document_revision,
)

router = APIRouter()


# ----- Pydantic Schemas -----


class DocumentCreate(BaseModel):
    """Schema for creating a document."""

    document_number: str
    title: str
    description: str = ""
    document_type: str = "other"
    category: Optional[str] = None
    discipline: Optional[str] = None
    project_id: Optional[str] = None
    tags: list[str] = []
    attributes: dict = {}


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    title: Optional[str] = None
    description: Optional[str] = None
    document_type: Optional[str] = None
    category: Optional[str] = None
    discipline: Optional[str] = None
    project_id: Optional[str] = None
    tags: Optional[list[str]] = None
    attributes: Optional[dict] = None


class DocumentLinkCreate(BaseModel):
    """Schema for linking a document."""

    part_id: Optional[str] = None
    bom_id: Optional[str] = None
    eco_id: Optional[str] = None
    project_id: Optional[str] = None
    link_type: str = "reference"
    description: Optional[str] = None


class CheckoutRequest(BaseModel):
    """Schema for checkout request."""

    user_id: str
    notes: Optional[str] = None


class CheckinRequest(BaseModel):
    """Schema for checkin request."""

    user_id: str
    change_summary: Optional[str] = None
    file_hash: Optional[str] = None
    file_size: Optional[int] = None


class DocumentVersionResponse(BaseModel):
    """Schema for version response."""

    id: str
    document_id: str
    version_number: int
    revision: str
    storage_path: str
    file_hash: str
    file_size: int
    change_summary: Optional[str]
    change_order_id: Optional[str]
    created_by: Optional[str]
    created_at: datetime


class DocumentLinkResponse(BaseModel):
    """Schema for link response."""

    id: str
    document_id: str
    part_id: Optional[str]
    bom_id: Optional[str]
    eco_id: Optional[str]
    project_id: Optional[str]
    link_type: str
    description: Optional[str]
    created_by: Optional[str]
    created_at: datetime


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: str
    document_number: str
    revision: str
    full_document_number: str
    title: str
    description: Optional[str]
    document_type: str
    status: str
    storage_path: Optional[str]
    file_name: Optional[str]
    file_size: Optional[int]
    file_hash: Optional[str]
    mime_type: Optional[str]
    category: Optional[str]
    discipline: Optional[str]
    project_id: Optional[str]
    checkout_status: str
    checked_out_by: Optional[str]
    checked_out_at: Optional[datetime]
    checkout_notes: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    released_by: Optional[str]
    released_at: Optional[datetime]
    superseded_by: Optional[str]
    tags: list[str]
    attributes: dict
    versions: list[DocumentVersionResponse]
    links: list[DocumentLinkResponse]


# ----- CRUD Endpoints -----


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    status: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    checkout_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search title/description"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
):
    """List documents with optional filters."""
    query = db.query(DocumentModel)

    if status:
        query = query.filter(DocumentModel.status == status)
    if document_type:
        query = query.filter(DocumentModel.document_type == document_type)
    if category:
        query = query.filter(DocumentModel.category == category)
    if project_id:
        query = query.filter(DocumentModel.project_id == project_id)
    if checkout_status:
        query = query.filter(DocumentModel.checkout_status == checkout_status)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (DocumentModel.title.ilike(search_pattern))
            | (DocumentModel.description.ilike(search_pattern))
            | (DocumentModel.document_number.ilike(search_pattern))
        )

    docs = query.order_by(DocumentModel.created_at.desc()).offset(offset).limit(limit).all()
    return [_doc_to_response(d) for d in docs]


@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(
    doc: DocumentCreate,
    created_by: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Create a new document."""
    from uuid import uuid4

    model = DocumentModel(
        id=str(uuid4()),
        document_number=doc.document_number,
        revision="A",
        title=doc.title,
        description=doc.description,
        document_type=doc.document_type,
        status=DocumentStatus.DRAFT.value,
        category=doc.category,
        discipline=doc.discipline,
        project_id=doc.project_id,
        tags=doc.tags,
        attributes=doc.attributes,
        created_by=created_by,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    return _doc_to_response(model)


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    db: Session = Depends(get_db_session),
):
    """Get a document by ID."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_to_response(doc)


@router.patch("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: str,
    updates: DocumentUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a document (only in draft status or when checked out)."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status not in [DocumentStatus.DRAFT.value, DocumentStatus.PENDING_REVIEW.value]:
        if doc.checkout_status != CheckoutStatus.CHECKED_OUT.value:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot modify document in status {doc.status} unless checked out",
            )

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(doc, field, value)

    db.commit()
    db.refresh(doc)

    return _doc_to_response(doc)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    db: Session = Depends(get_db_session),
):
    """Delete a document (only if draft and no versions)."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status != DocumentStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Can only delete draft documents")

    if doc.versions and len(doc.versions) > 0:
        raise HTTPException(status_code=400, detail="Cannot delete document with versions")

    db.delete(doc)
    db.commit()


# ----- Check-in/Check-out Endpoints -----


@router.post("/{doc_id}/checkout", response_model=DocumentResponse)
async def checkout_document(
    doc_id: str,
    request: CheckoutRequest,
    db: Session = Depends(get_db_session),
):
    """Check out a document for editing."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.checkout_status != CheckoutStatus.AVAILABLE.value:
        raise HTTPException(
            status_code=400,
            detail=f"Document is {doc.checkout_status}, cannot check out",
        )

    if doc.status in [DocumentStatus.OBSOLETE.value, DocumentStatus.VOID.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot check out document in status {doc.status}",
        )

    doc.checkout_status = CheckoutStatus.CHECKED_OUT.value
    doc.checked_out_by = request.user_id
    doc.checked_out_at = datetime.now()
    doc.checkout_notes = request.notes

    db.commit()
    db.refresh(doc)

    return _doc_to_response(doc)


@router.post("/{doc_id}/checkin", response_model=DocumentResponse)
async def checkin_document(
    doc_id: str,
    request: CheckinRequest,
    db: Session = Depends(get_db_session),
):
    """Check in a document after editing."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.checkout_status != CheckoutStatus.CHECKED_OUT.value:
        raise HTTPException(status_code=400, detail="Document is not checked out")

    if doc.checked_out_by != request.user_id:
        raise HTTPException(
            status_code=403,
            detail=f"Document is checked out by {doc.checked_out_by}",
        )

    # Create a new version if file changed
    if request.file_hash and request.file_hash != doc.file_hash:
        from uuid import uuid4

        version_count = len(doc.versions) + 1
        version = DocumentVersionModel(
            id=str(uuid4()),
            document_id=doc_id,
            version_number=version_count,
            revision=doc.revision,
            storage_path=doc.storage_path or "",
            file_hash=request.file_hash,
            file_size=request.file_size or doc.file_size or 0,
            change_summary=request.change_summary,
            created_by=request.user_id,
            created_at=datetime.now(),
        )
        db.add(version)

        # Update document with new hash
        doc.file_hash = request.file_hash
        if request.file_size:
            doc.file_size = request.file_size

    # Clear checkout
    doc.checkout_status = CheckoutStatus.AVAILABLE.value
    doc.checked_out_by = None
    doc.checked_out_at = None
    doc.checkout_notes = None

    db.commit()
    db.refresh(doc)

    return _doc_to_response(doc)


@router.post("/{doc_id}/cancel-checkout", response_model=DocumentResponse)
async def cancel_checkout(
    doc_id: str,
    user_id: str = Query(...),
    force: bool = Query(False, description="Force cancel (admin only)"),
    db: Session = Depends(get_db_session),
):
    """Cancel checkout without saving changes."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.checkout_status != CheckoutStatus.CHECKED_OUT.value:
        raise HTTPException(status_code=400, detail="Document is not checked out")

    if doc.checked_out_by != user_id and not force:
        raise HTTPException(
            status_code=403,
            detail=f"Document is checked out by {doc.checked_out_by}",
        )

    doc.checkout_status = CheckoutStatus.AVAILABLE.value
    doc.checked_out_by = None
    doc.checked_out_at = None
    doc.checkout_notes = None

    db.commit()
    db.refresh(doc)

    return _doc_to_response(doc)


# ----- Workflow Endpoints -----


@router.post("/{doc_id}/submit-for-review", response_model=DocumentResponse)
async def submit_for_review(
    doc_id: str,
    submitted_by: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Submit document for review."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status != DocumentStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail=f"Can only submit draft documents, current status: {doc.status}",
        )

    if doc.checkout_status == CheckoutStatus.CHECKED_OUT.value:
        raise HTTPException(status_code=400, detail="Cannot submit document that is checked out")

    doc.status = DocumentStatus.PENDING_REVIEW.value
    db.commit()
    db.refresh(doc)

    return _doc_to_response(doc)


@router.post("/{doc_id}/start-review", response_model=DocumentResponse)
async def start_review(
    doc_id: str,
    db: Session = Depends(get_db_session),
):
    """Move document from pending to in-review."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status != DocumentStatus.PENDING_REVIEW.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start review for document in status {doc.status}",
        )

    doc.status = DocumentStatus.IN_REVIEW.value
    db.commit()
    db.refresh(doc)

    return _doc_to_response(doc)


@router.post("/{doc_id}/approve", response_model=DocumentResponse)
async def approve_document(
    doc_id: str,
    approved_by: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Approve/release a document."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status not in [
        DocumentStatus.PENDING_REVIEW.value,
        DocumentStatus.IN_REVIEW.value,
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve document in status {doc.status}",
        )

    doc.status = DocumentStatus.APPROVED.value
    doc.released_by = approved_by
    doc.released_at = datetime.now()

    db.commit()
    db.refresh(doc)

    return _doc_to_response(doc)


@router.post("/{doc_id}/revise", response_model=DocumentResponse)
async def revise_document(
    doc_id: str,
    revised_by: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Create a new revision of an approved document."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status != DocumentStatus.APPROVED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Can only revise approved documents, current status: {doc.status}",
        )

    from uuid import uuid4

    # Mark current as superseded
    doc.status = DocumentStatus.SUPERSEDED.value

    # Create new revision
    new_revision = increment_document_revision(doc.revision)
    new_doc = DocumentModel(
        id=str(uuid4()),
        document_number=doc.document_number,
        revision=new_revision,
        title=doc.title,
        description=doc.description,
        document_type=doc.document_type,
        status=DocumentStatus.DRAFT.value,
        storage_path=doc.storage_path,
        file_name=doc.file_name,
        file_size=doc.file_size,
        file_hash=doc.file_hash,
        mime_type=doc.mime_type,
        category=doc.category,
        discipline=doc.discipline,
        project_id=doc.project_id,
        created_by=revised_by,
        created_at=datetime.now(),
        tags=doc.tags or [],
        attributes=doc.attributes or {},
    )
    doc.superseded_by = new_doc.id

    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    return _doc_to_response(new_doc)


@router.post("/{doc_id}/obsolete", response_model=DocumentResponse)
async def obsolete_document(
    doc_id: str,
    reason: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Mark document as obsolete."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status in [DocumentStatus.OBSOLETE.value, DocumentStatus.VOID.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Document is already {doc.status}",
        )

    doc.status = DocumentStatus.OBSOLETE.value
    db.commit()
    db.refresh(doc)

    return _doc_to_response(doc)


# ----- Link Endpoints -----


@router.post("/{doc_id}/links", response_model=DocumentLinkResponse, status_code=201)
async def link_document(
    doc_id: str,
    link: DocumentLinkCreate,
    created_by: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Link a document to a part, BOM, or ECO."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Validate link target exists
    if link.part_id:
        part = db.query(PartModel).filter(PartModel.id == link.part_id).first()
        if not part:
            raise HTTPException(status_code=404, detail="Part not found")
    if link.bom_id:
        bom = db.query(BOMModel).filter(BOMModel.id == link.bom_id).first()
        if not bom:
            raise HTTPException(status_code=404, detail="BOM not found")
    if link.eco_id:
        eco = db.query(ChangeOrderModel).filter(ChangeOrderModel.id == link.eco_id).first()
        if not eco:
            raise HTTPException(status_code=404, detail="ECO not found")

    from uuid import uuid4

    model = DocumentLinkModel(
        id=str(uuid4()),
        document_id=doc_id,
        part_id=link.part_id,
        bom_id=link.bom_id,
        eco_id=link.eco_id,
        project_id=link.project_id,
        link_type=link.link_type,
        description=link.description,
        created_by=created_by,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    return _link_to_response(model)


@router.get("/{doc_id}/links", response_model=list[DocumentLinkResponse])
async def list_document_links(
    doc_id: str,
    db: Session = Depends(get_db_session),
):
    """List all links for a document."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return [_link_to_response(link) for link in doc.links]


@router.delete("/{doc_id}/links/{link_id}", status_code=204)
async def unlink_document(
    doc_id: str,
    link_id: str,
    db: Session = Depends(get_db_session),
):
    """Remove a document link."""
    link = (
        db.query(DocumentLinkModel)
        .filter(DocumentLinkModel.id == link_id, DocumentLinkModel.document_id == doc_id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    db.delete(link)
    db.commit()


# ----- Version Endpoints -----


@router.get("/{doc_id}/versions", response_model=list[DocumentVersionResponse])
async def list_document_versions(
    doc_id: str,
    db: Session = Depends(get_db_session),
):
    """List all versions of a document."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return [_version_to_response(v) for v in sorted(doc.versions, key=lambda x: x.version_number, reverse=True)]


@router.get("/{doc_id}/versions/{version_id}", response_model=DocumentVersionResponse)
async def get_document_version(
    doc_id: str,
    version_id: str,
    db: Session = Depends(get_db_session),
):
    """Get a specific version of a document."""
    version = (
        db.query(DocumentVersionModel)
        .filter(DocumentVersionModel.id == version_id, DocumentVersionModel.document_id == doc_id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return _version_to_response(version)


# ----- Cross-reference Endpoints -----


@router.get("/by-part/{part_id}", response_model=list[DocumentResponse])
async def get_documents_for_part(
    part_id: str,
    db: Session = Depends(get_db_session),
):
    """Get all documents linked to a part."""
    links = db.query(DocumentLinkModel).filter(DocumentLinkModel.part_id == part_id).all()
    doc_ids = [link.document_id for link in links]

    if not doc_ids:
        return []

    docs = db.query(DocumentModel).filter(DocumentModel.id.in_(doc_ids)).all()
    return [_doc_to_response(d) for d in docs]


@router.get("/by-bom/{bom_id}", response_model=list[DocumentResponse])
async def get_documents_for_bom(
    bom_id: str,
    db: Session = Depends(get_db_session),
):
    """Get all documents linked to a BOM."""
    links = db.query(DocumentLinkModel).filter(DocumentLinkModel.bom_id == bom_id).all()
    doc_ids = [link.document_id for link in links]

    if not doc_ids:
        return []

    docs = db.query(DocumentModel).filter(DocumentModel.id.in_(doc_ids)).all()
    return [_doc_to_response(d) for d in docs]


@router.get("/by-eco/{eco_id}", response_model=list[DocumentResponse])
async def get_documents_for_eco(
    eco_id: str,
    db: Session = Depends(get_db_session),
):
    """Get all documents linked to an ECO."""
    links = db.query(DocumentLinkModel).filter(DocumentLinkModel.eco_id == eco_id).all()
    doc_ids = [link.document_id for link in links]

    if not doc_ids:
        return []

    docs = db.query(DocumentModel).filter(DocumentModel.id.in_(doc_ids)).all()
    return [_doc_to_response(d) for d in docs]


# ----- Helpers -----


def _doc_to_response(model: DocumentModel) -> DocumentResponse:
    """Convert DB model to response."""
    return DocumentResponse(
        id=model.id,
        document_number=model.document_number,
        revision=model.revision,
        full_document_number=f"{model.document_number}-{model.revision}",
        title=model.title,
        description=model.description,
        document_type=model.document_type.value if hasattr(model.document_type, 'value') else model.document_type,
        status=model.status.value if hasattr(model.status, 'value') else model.status,
        storage_path=model.storage_path,
        file_name=model.file_name,
        file_size=model.file_size,
        file_hash=model.file_hash,
        mime_type=model.mime_type,
        category=model.category,
        discipline=model.discipline,
        project_id=model.project_id,
        checkout_status=model.checkout_status.value if hasattr(model.checkout_status, 'value') else model.checkout_status,
        checked_out_by=model.checked_out_by,
        checked_out_at=model.checked_out_at,
        checkout_notes=model.checkout_notes,
        created_by=model.created_by,
        created_at=model.created_at,
        released_by=model.released_by,
        released_at=model.released_at,
        superseded_by=model.superseded_by,
        tags=model.tags or [],
        attributes=model.attributes or {},
        versions=[_version_to_response(v) for v in (model.versions or [])],
        links=[_link_to_response(lnk) for lnk in (model.links or [])],
    )


def _version_to_response(model: DocumentVersionModel) -> DocumentVersionResponse:
    """Convert version model to response."""
    return DocumentVersionResponse(
        id=model.id,
        document_id=model.document_id,
        version_number=model.version_number,
        revision=model.revision,
        storage_path=model.storage_path,
        file_hash=model.file_hash,
        file_size=model.file_size,
        change_summary=model.change_summary,
        change_order_id=model.change_order_id,
        created_by=model.created_by,
        created_at=model.created_at,
    )


def _link_to_response(model: DocumentLinkModel) -> DocumentLinkResponse:
    """Convert link model to response."""
    return DocumentLinkResponse(
        id=model.id,
        document_id=model.document_id,
        part_id=model.part_id,
        bom_id=model.bom_id,
        eco_id=model.eco_id,
        project_id=model.project_id,
        link_type=model.link_type,
        description=model.description,
        created_by=model.created_by,
        created_at=model.created_at,
    )
