"""
Compliance API Router

Regulatory compliance management (RoHS, REACH, conflict minerals).
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from plm.api.deps import get_db_session
from plm.db.models import (
    RegulationModel,
    SubstanceDeclarationModel,
    ComplianceDeclarationModel,
    ComplianceCertificateModel,
    ConflictMineralDeclarationModel,
)

router = APIRouter()


# ----- Pydantic Schemas -----


class RegulationCreate(BaseModel):
    regulation_code: str
    name: str
    regulation_type: str
    authority: Optional[str] = None
    description: Optional[str] = None


class RegulationResponse(BaseModel):
    id: str
    regulation_code: str
    name: str
    regulation_type: str
    authority: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class SubstanceDeclarationCreate(BaseModel):
    part_id: str
    part_number: str
    substance_name: str
    cas_number: Optional[str] = None
    category: str = "other"
    concentration_ppm: Optional[float] = None
    above_threshold: bool = False


class SubstanceDeclarationResponse(BaseModel):
    id: str
    part_id: str
    part_number: str
    substance_name: str
    cas_number: Optional[str]
    category: str
    concentration_ppm: Optional[float]
    above_threshold: bool

    class Config:
        from_attributes = True


class ComplianceDeclarationCreate(BaseModel):
    part_id: str
    part_number: str
    regulation_id: str
    regulation_code: str
    status: str = "unknown"
    exemption_code: Optional[str] = None


class ComplianceDeclarationUpdate(BaseModel):
    status: Optional[str] = None
    exemption_code: Optional[str] = None
    notes: Optional[str] = None
    verified_by: Optional[str] = None


class ComplianceDeclarationResponse(BaseModel):
    id: str
    part_id: str
    part_number: str
    regulation_id: str
    regulation_code: str
    status: str
    exemption_code: Optional[str]

    class Config:
        from_attributes = True


class CertificateCreate(BaseModel):
    certificate_number: str
    regulation_id: str
    regulation_code: str
    issued_by: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None


class CertificateResponse(BaseModel):
    id: str
    certificate_number: str
    regulation_id: str
    regulation_code: str
    status: str
    issued_by: Optional[str]
    issue_date: Optional[str]
    expiry_date: Optional[str]

    class Config:
        from_attributes = True


class ConflictMineralCreate(BaseModel):
    part_id: str
    part_number: str
    contains_tin: bool = False
    contains_tantalum: bool = False
    contains_tungsten: bool = False
    contains_gold: bool = False
    conflict_free: Optional[bool] = None


class ConflictMineralResponse(BaseModel):
    id: str
    part_id: str
    part_number: str
    contains_tin: bool
    contains_tantalum: bool
    contains_tungsten: bool
    contains_gold: bool
    conflict_free: Optional[bool]

    class Config:
        from_attributes = True


# ----- Regulation Endpoints -----


@router.get("/regulations", response_model=list[RegulationResponse])
async def list_regulations(
    regulation_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db_session),
):
    """List regulations."""
    query = db.query(RegulationModel)

    if regulation_type:
        query = query.filter(RegulationModel.regulation_type == regulation_type)
    if is_active is not None:
        query = query.filter(RegulationModel.is_active == is_active)

    return query.limit(limit).all()


@router.post("/regulations", response_model=RegulationResponse, status_code=201)
async def create_regulation(
    reg: RegulationCreate,
    db: Session = Depends(get_db_session),
):
    """Create a regulation."""
    existing = db.query(RegulationModel).filter(
        RegulationModel.regulation_code == reg.regulation_code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Regulation code already exists")

    model = RegulationModel(
        id=str(uuid4()),
        regulation_code=reg.regulation_code,
        name=reg.name,
        regulation_type=reg.regulation_type,
        authority=reg.authority,
        description=reg.description,
        is_active=True,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/regulations/{reg_id}", response_model=RegulationResponse)
async def get_regulation(reg_id: str, db: Session = Depends(get_db_session)):
    """Get a regulation by ID."""
    reg = db.query(RegulationModel).filter(RegulationModel.id == reg_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Regulation not found")
    return reg


# ----- Substance Declaration Endpoints -----


@router.get("/parts/{part_id}/substances", response_model=list[SubstanceDeclarationResponse])
async def list_part_substances(part_id: str, db: Session = Depends(get_db_session)):
    """List substance declarations for a part."""
    return db.query(SubstanceDeclarationModel).filter(
        SubstanceDeclarationModel.part_id == part_id
    ).all()


@router.post("/parts/{part_id}/substances", response_model=SubstanceDeclarationResponse, status_code=201)
async def create_substance_declaration(
    part_id: str,
    decl: SubstanceDeclarationCreate,
    db: Session = Depends(get_db_session),
):
    """Create a substance declaration for a part."""
    model = SubstanceDeclarationModel(
        id=str(uuid4()),
        part_id=part_id,
        part_number=decl.part_number,
        substance_name=decl.substance_name,
        cas_number=decl.cas_number,
        category=decl.category,
        concentration_ppm=Decimal(str(decl.concentration_ppm)) if decl.concentration_ppm else None,
        above_threshold=decl.above_threshold,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


# ----- Compliance Declaration Endpoints -----


@router.get("/parts/{part_id}/compliance", response_model=list[ComplianceDeclarationResponse])
async def list_part_compliance(part_id: str, db: Session = Depends(get_db_session)):
    """List compliance declarations for a part."""
    return db.query(ComplianceDeclarationModel).filter(
        ComplianceDeclarationModel.part_id == part_id
    ).all()


@router.post("/parts/{part_id}/compliance", response_model=ComplianceDeclarationResponse, status_code=201)
async def create_compliance_declaration(
    part_id: str,
    decl: ComplianceDeclarationCreate,
    db: Session = Depends(get_db_session),
):
    """Create a compliance declaration for a part."""
    model = ComplianceDeclarationModel(
        id=str(uuid4()),
        part_id=part_id,
        part_number=decl.part_number,
        regulation_id=decl.regulation_id,
        regulation_code=decl.regulation_code,
        status=decl.status,
        exemption_code=decl.exemption_code,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.patch("/parts/{part_id}/compliance/{decl_id}", response_model=ComplianceDeclarationResponse)
async def update_compliance_declaration(
    part_id: str,
    decl_id: str,
    updates: ComplianceDeclarationUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a compliance declaration."""
    decl = db.query(ComplianceDeclarationModel).filter(
        ComplianceDeclarationModel.id == decl_id,
        ComplianceDeclarationModel.part_id == part_id,
    ).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Declaration not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(decl, field, value)

    if updates.verified_by:
        decl.verified_date = date.today()

    db.commit()
    db.refresh(decl)
    return decl


# ----- Certificate Endpoints -----


@router.get("/certificates", response_model=list[CertificateResponse])
async def list_certificates(
    regulation_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db_session),
):
    """List compliance certificates."""
    query = db.query(ComplianceCertificateModel)

    if regulation_id:
        query = query.filter(ComplianceCertificateModel.regulation_id == regulation_id)
    if status:
        query = query.filter(ComplianceCertificateModel.status == status)

    return query.limit(limit).all()


@router.post("/certificates", response_model=CertificateResponse, status_code=201)
async def create_certificate(
    cert: CertificateCreate,
    db: Session = Depends(get_db_session),
):
    """Create a compliance certificate."""
    model = ComplianceCertificateModel(
        id=str(uuid4()),
        certificate_number=cert.certificate_number,
        regulation_id=cert.regulation_id,
        regulation_code=cert.regulation_code,
        status="draft",
        issued_by=cert.issued_by,
        issue_date=date.fromisoformat(cert.issue_date) if cert.issue_date else None,
        expiry_date=date.fromisoformat(cert.expiry_date) if cert.expiry_date else None,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


# ----- Conflict Mineral Endpoints -----


@router.get("/parts/{part_id}/conflict-minerals", response_model=ConflictMineralResponse)
async def get_conflict_mineral_declaration(part_id: str, db: Session = Depends(get_db_session)):
    """Get conflict mineral declaration for a part."""
    decl = db.query(ConflictMineralDeclarationModel).filter(
        ConflictMineralDeclarationModel.part_id == part_id
    ).first()
    if not decl:
        raise HTTPException(status_code=404, detail="No conflict mineral declaration found")
    return decl


@router.post("/parts/{part_id}/conflict-minerals", response_model=ConflictMineralResponse, status_code=201)
async def create_conflict_mineral_declaration(
    part_id: str,
    decl: ConflictMineralCreate,
    db: Session = Depends(get_db_session),
):
    """Create a conflict mineral declaration for a part."""
    existing = db.query(ConflictMineralDeclarationModel).filter(
        ConflictMineralDeclarationModel.part_id == part_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Declaration already exists for this part")

    model = ConflictMineralDeclarationModel(
        id=str(uuid4()),
        part_id=part_id,
        part_number=decl.part_number,
        contains_tin=decl.contains_tin,
        contains_tantalum=decl.contains_tantalum,
        contains_tungsten=decl.contains_tungsten,
        contains_gold=decl.contains_gold,
        conflict_free=decl.conflict_free,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.put("/parts/{part_id}/conflict-minerals", response_model=ConflictMineralResponse)
async def update_conflict_mineral_declaration(
    part_id: str,
    decl: ConflictMineralCreate,
    db: Session = Depends(get_db_session),
):
    """Update a conflict mineral declaration."""
    existing = db.query(ConflictMineralDeclarationModel).filter(
        ConflictMineralDeclarationModel.part_id == part_id
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Declaration not found")

    existing.contains_tin = decl.contains_tin
    existing.contains_tantalum = decl.contains_tantalum
    existing.contains_tungsten = decl.contains_tungsten
    existing.contains_gold = decl.contains_gold
    existing.conflict_free = decl.conflict_free

    db.commit()
    db.refresh(existing)
    return existing
