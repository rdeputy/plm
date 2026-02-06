"""
Compliance Service

Business logic for regulatory compliance management.
"""

from typing import Optional
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from plm.compliance.repository import (
    RegulationRepository,
    SubstanceDeclarationRepository,
    ComplianceDeclarationRepository,
    ComplianceCertificateRepository,
    ConflictMineralRepository,
)
from plm.db.models import (
    RegulationModel,
    SubstanceDeclarationModel,
    ComplianceDeclarationModel,
    ComplianceCertificateModel,
    ConflictMineralDeclarationModel,
)


@dataclass
class ComplianceStatus:
    """Compliance status for a part."""

    part_id: str
    is_compliant: bool
    regulations_checked: int
    compliant_count: int
    non_compliant_count: int
    pending_count: int
    expiring_soon: list[str]
    issues: list[str]


@dataclass
class ComplianceStats:
    """Overall compliance statistics."""

    total_parts_checked: int
    fully_compliant: int
    non_compliant: int
    pending_review: int
    certificates_expiring_soon: int


class ComplianceService:
    """Service for compliance management."""

    def __init__(self, session: Session):
        self.session = session
        self.regulations = RegulationRepository(session)
        self.substances = SubstanceDeclarationRepository(session)
        self.declarations = ComplianceDeclarationRepository(session)
        self.certificates = ComplianceCertificateRepository(session)
        self.conflict_minerals = ConflictMineralRepository(session)

    def get_regulation(self, regulation_id: str) -> Optional[RegulationModel]:
        """Get regulation by ID."""
        return self.regulations.get(regulation_id)

    def get_regulation_by_code(self, code: str) -> Optional[RegulationModel]:
        """Get regulation by code."""
        return self.regulations.find_by_code(code)

    def list_active_regulations(
        self,
        regulation_type: Optional[str] = None,
    ) -> list[RegulationModel]:
        """List active regulations."""
        return self.regulations.list_active(regulation_type)

    def declare_substance(
        self,
        part_id: str,
        substance_name: str,
        part_number: str = "",
        cas_number: Optional[str] = None,
        concentration_ppm: Optional[float] = None,
        threshold_ppm: Optional[float] = None,
        location_in_part: str = "",
    ) -> SubstanceDeclarationModel:
        """Declare a substance in a part."""
        above_threshold = False
        if concentration_ppm is not None and threshold_ppm is not None:
            above_threshold = concentration_ppm > threshold_ppm

        return self.substances.create(
            part_id=part_id,
            part_number=part_number,
            substance_name=substance_name,
            cas_number=cas_number,
            concentration_ppm=concentration_ppm,
            threshold_ppm=threshold_ppm,
            above_threshold=above_threshold,
            component=location_in_part,
        )

    def get_part_substances(self, part_id: str) -> list[SubstanceDeclarationModel]:
        """Get all substances for a part."""
        return self.substances.list_for_part(part_id)

    def get_substances_above_threshold(
        self,
        part_id: str,
    ) -> list[SubstanceDeclarationModel]:
        """Get substances above threshold for a part."""
        return self.substances.list_above_threshold(part_id)

    def declare_compliance(
        self,
        part_id: str,
        regulation_id: str,
        status: str = "pending",
        declaration_date: Optional[date] = None,
        expires: Optional[date] = None,
        declared_by: Optional[str] = None,
        notes: str = "",
    ) -> ComplianceDeclarationModel:
        """Declare compliance status for a part and regulation."""
        return self.declarations.create(
            part_id=part_id,
            regulation_id=regulation_id,
            status=status,
            declaration_date=declaration_date or date.today(),
            expires=expires,
            declared_by=declared_by,
            notes=notes,
        )

    def get_part_compliance(
        self,
        part_id: str,
    ) -> list[ComplianceDeclarationModel]:
        """Get all compliance declarations for a part."""
        return self.declarations.list_for_part(part_id)

    def check_part_compliance_status(self, part_id: str) -> ComplianceStatus:
        """Check overall compliance status for a part."""
        declarations = self.declarations.list_for_part(part_id)

        compliant_count = 0
        non_compliant_count = 0
        pending_count = 0
        expiring_soon: list[str] = []
        issues: list[str] = []

        cutoff = date.today() + timedelta(days=30)

        for decl in declarations:
            status_str = str(decl.status.value) if hasattr(decl.status, "value") else str(decl.status)
            if status_str == "compliant":
                compliant_count += 1
                if decl.expires and decl.expires <= cutoff:
                    expiring_soon.append(str(decl.regulation_id))
            elif status_str == "non_compliant":
                non_compliant_count += 1
                issues.append(f"Non-compliant with regulation {decl.regulation_id}")
            else:
                pending_count += 1

        is_compliant = non_compliant_count == 0 and pending_count == 0

        return ComplianceStatus(
            part_id=part_id,
            is_compliant=is_compliant,
            regulations_checked=len(declarations),
            compliant_count=compliant_count,
            non_compliant_count=non_compliant_count,
            pending_count=pending_count,
            expiring_soon=expiring_soon,
            issues=issues,
        )

    def create_certificate(
        self,
        certificate_number: str,
        regulation_id: str,
        issuing_authority: str,
        issue_date: date,
        expiry_date: Optional[date] = None,
        scope: str = "",
    ) -> ComplianceCertificateModel:
        """Create a compliance certificate."""
        return self.certificates.create(
            certificate_number=certificate_number,
            regulation_id=regulation_id,
            issuing_authority=issuing_authority,
            issue_date=issue_date,
            expiry_date=expiry_date,
            scope=scope,
            status="active",
        )

    def get_certificate(
        self,
        certificate_number: str,
    ) -> Optional[ComplianceCertificateModel]:
        """Get certificate by number."""
        return self.certificates.find_by_number(certificate_number)

    def get_expiring_certificates(
        self,
        days: int = 30,
    ) -> list[ComplianceCertificateModel]:
        """Get certificates expiring soon."""
        return self.certificates.list_expiring_soon(days)

    def declare_conflict_minerals(
        self,
        part_id: str,
        contains_tin: bool = False,
        contains_tantalum: bool = False,
        contains_tungsten: bool = False,
        contains_gold: bool = False,
        conflict_free: Optional[bool] = None,
        smelter_list: Optional[list] = None,
        due_diligence_date: Optional[date] = None,
    ) -> ConflictMineralDeclarationModel:
        """Declare conflict mineral (3TG) status for a part."""
        return self.conflict_minerals.create(
            part_id=part_id,
            contains_tin=contains_tin,
            contains_tantalum=contains_tantalum,
            contains_tungsten=contains_tungsten,
            contains_gold=contains_gold,
            conflict_free=conflict_free,
            smelter_list=smelter_list or [],
            due_diligence_date=due_diligence_date,
        )

    def get_conflict_mineral_status(
        self,
        part_id: str,
    ) -> Optional[ConflictMineralDeclarationModel]:
        """Get 3TG declaration for a part."""
        return self.conflict_minerals.get_for_part(part_id)

    def list_non_conflict_free_parts(self) -> list[ConflictMineralDeclarationModel]:
        """List parts not declared conflict-free."""
        return self.conflict_minerals.list_not_conflict_free()

    def get_stats(self) -> ComplianceStats:
        """Get overall compliance statistics."""
        non_compliant = self.declarations.list_non_compliant()
        expiring_certs = self.certificates.list_expiring_soon(30)

        all_declarations = self.declarations.list(limit=10000)
        part_ids = set(d.part_id for d in all_declarations)

        fully_compliant = 0
        non_compliant_count = 0
        pending_count = 0

        for part_id in part_ids:
            status = self.check_part_compliance_status(part_id)
            if status.is_compliant:
                fully_compliant += 1
            elif status.non_compliant_count > 0:
                non_compliant_count += 1
            else:
                pending_count += 1

        return ComplianceStats(
            total_parts_checked=len(part_ids),
            fully_compliant=fully_compliant,
            non_compliant=non_compliant_count,
            pending_review=pending_count,
            certificates_expiring_soon=len(expiring_certs),
        )

    def commit(self):
        """Commit transaction."""
        self.session.commit()
