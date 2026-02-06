"""
Requirements API Router

CRUD operations for requirements, links, and verification records.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from plm.api.deps import get_db_session
from plm.db.models import RequirementModel, RequirementLinkModel, VerificationRecordModel

router = APIRouter()


# ----- Pydantic Schemas -----


class RequirementCreate(BaseModel):
    requirement_number: str
    requirement_type: str = "functional"
    title: str
    description: Optional[str] = None
    priority: str = "must_have"
    source: Optional[str] = None
    verification_method: str = "test"
    parent_id: Optional[str] = None
    project_id: Optional[str] = None


class RequirementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    rationale: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    verification_method: Optional[str] = None


class RequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    requirement_number: str
    requirement_type: str
    status: str
    priority: str
    title: str
    description: Optional[str]
    source: Optional[str]
    verification_method: str
    parent_id: Optional[str]
    project_id: Optional[str]


class RequirementLinkCreate(BaseModel):
    requirement_id: str
    link_type: str  # part, document, test
    target_id: str
    target_number: Optional[str] = None
    relationship: str = "implements"
    coverage: str = "full"


class RequirementLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    requirement_id: str
    link_type: str
    target_id: str
    target_number: Optional[str]
    relationship: str
    coverage: str


class VerificationCreate(BaseModel):
    verification_number: str
    requirement_id: str
    requirement_number: str
    method: str
    procedure_id: Optional[str] = None


class VerificationUpdate(BaseModel):
    status: Optional[str] = None
    result_summary: Optional[str] = None
    pass_fail: Optional[bool] = None
    verified_by: Optional[str] = None


class VerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    verification_number: str
    requirement_id: str
    requirement_number: str
    method: str
    status: str
    pass_fail: Optional[bool]
    verified_by: Optional[str]


# ----- Requirement Endpoints -----


@router.get("", response_model=list[RequirementResponse])
async def list_requirements(
    requirement_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
):
    """List requirements with optional filters."""
    query = db.query(RequirementModel)

    if requirement_type:
        query = query.filter(RequirementModel.requirement_type == requirement_type)
    if status:
        query = query.filter(RequirementModel.status == status)
    if priority:
        query = query.filter(RequirementModel.priority == priority)
    if project_id:
        query = query.filter(RequirementModel.project_id == project_id)
    if search:
        term = f"%{search}%"
        query = query.filter(
            (RequirementModel.requirement_number.ilike(term))
            | (RequirementModel.title.ilike(term))
        )

    return query.offset(offset).limit(limit).all()


@router.post("", response_model=RequirementResponse, status_code=201)
async def create_requirement(
    req: RequirementCreate,
    db: Session = Depends(get_db_session),
):
    """Create a new requirement."""
    existing = db.query(RequirementModel).filter(
        RequirementModel.requirement_number == req.requirement_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Requirement number already exists")

    model = RequirementModel(
        id=str(uuid4()),
        requirement_number=req.requirement_number,
        requirement_type=req.requirement_type,
        status="draft",
        priority=req.priority,
        title=req.title,
        description=req.description,
        source=req.source,
        verification_method=req.verification_method,
        parent_id=req.parent_id,
        project_id=req.project_id,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/{req_id}", response_model=RequirementResponse)
async def get_requirement(req_id: str, db: Session = Depends(get_db_session)):
    """Get a requirement by ID."""
    req = db.query(RequirementModel).filter(RequirementModel.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return req


@router.patch("/{req_id}", response_model=RequirementResponse)
async def update_requirement(
    req_id: str,
    updates: RequirementUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a requirement."""
    req = db.query(RequirementModel).filter(RequirementModel.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(req, field, value)

    db.commit()
    db.refresh(req)
    return req


@router.delete("/{req_id}", status_code=204)
async def delete_requirement(req_id: str, db: Session = Depends(get_db_session)):
    """Delete a requirement."""
    req = db.query(RequirementModel).filter(RequirementModel.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    db.delete(req)
    db.commit()


# ----- Requirement Link Endpoints -----


@router.get("/{req_id}/links", response_model=list[RequirementLinkResponse])
async def list_requirement_links(req_id: str, db: Session = Depends(get_db_session)):
    """List links for a requirement."""
    return db.query(RequirementLinkModel).filter(
        RequirementLinkModel.requirement_id == req_id
    ).all()


@router.post("/{req_id}/links", response_model=RequirementLinkResponse, status_code=201)
async def create_requirement_link(
    req_id: str,
    link: RequirementLinkCreate,
    db: Session = Depends(get_db_session),
):
    """Create a link from requirement to an artifact."""
    req = db.query(RequirementModel).filter(RequirementModel.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    model = RequirementLinkModel(
        id=str(uuid4()),
        requirement_id=req_id,
        link_type=link.link_type,
        target_id=link.target_id,
        target_number=link.target_number,
        relationship=link.relationship,
        coverage=link.coverage,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.delete("/{req_id}/links/{link_id}", status_code=204)
async def delete_requirement_link(
    req_id: str,
    link_id: str,
    db: Session = Depends(get_db_session),
):
    """Delete a requirement link."""
    link = db.query(RequirementLinkModel).filter(
        RequirementLinkModel.id == link_id,
        RequirementLinkModel.requirement_id == req_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    db.delete(link)
    db.commit()


# ----- Verification Endpoints -----


@router.get("/verifications", response_model=list[VerificationResponse])
async def list_verifications(
    requirement_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db_session),
):
    """List verification records."""
    query = db.query(VerificationRecordModel)

    if requirement_id:
        query = query.filter(VerificationRecordModel.requirement_id == requirement_id)
    if status:
        query = query.filter(VerificationRecordModel.status == status)

    return query.limit(limit).all()


@router.post("/verifications", response_model=VerificationResponse, status_code=201)
async def create_verification(
    ver: VerificationCreate,
    db: Session = Depends(get_db_session),
):
    """Create a verification record."""
    model = VerificationRecordModel(
        id=str(uuid4()),
        verification_number=ver.verification_number,
        requirement_id=ver.requirement_id,
        requirement_number=ver.requirement_number,
        method=ver.method,
        procedure_id=ver.procedure_id,
        status="not_started",
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.patch("/verifications/{ver_id}", response_model=VerificationResponse)
async def update_verification(
    ver_id: str,
    updates: VerificationUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a verification record."""
    ver = db.query(VerificationRecordModel).filter(
        VerificationRecordModel.id == ver_id
    ).first()
    if not ver:
        raise HTTPException(status_code=404, detail="Verification not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(ver, field, value)

    if updates.pass_fail is not None and updates.verified_by:
        ver.verified_date = datetime.now()

    db.commit()
    db.refresh(ver)
    return ver
