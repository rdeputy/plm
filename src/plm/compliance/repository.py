"""
Compliance Repository

Database operations for regulations, declarations, and certificates.
"""

from typing import Optional
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from plm.db.repository import BaseRepository
from plm.db.models import (
    RegulationModel,
    SubstanceDeclarationModel,
    ComplianceDeclarationModel,
    ComplianceCertificateModel,
    ConflictMineralDeclarationModel,
)


class RegulationRepository(BaseRepository[RegulationModel]):
    """Repository for regulations."""

    def __init__(self, session: Session):
        super().__init__(session, RegulationModel)

    def find_by_code(self, code: str) -> Optional[RegulationModel]:
        """Find regulation by code."""
        return self.get_by(regulation_code=code)

    def list_active(self, regulation_type: Optional[str] = None) -> list[RegulationModel]:
        """List active regulations."""
        return self.list(is_active=True, regulation_type=regulation_type)


class SubstanceDeclarationRepository(BaseRepository[SubstanceDeclarationModel]):
    """Repository for substance declarations."""

    def __init__(self, session: Session):
        super().__init__(session, SubstanceDeclarationModel)

    def list_for_part(self, part_id: str) -> list[SubstanceDeclarationModel]:
        """List substances for a part."""
        return self.list(part_id=part_id)

    def list_above_threshold(self, part_id: str) -> list[SubstanceDeclarationModel]:
        """List substances above threshold for a part."""
        return self.list(part_id=part_id, above_threshold=True)


class ComplianceDeclarationRepository(BaseRepository[ComplianceDeclarationModel]):
    """Repository for compliance declarations."""

    def __init__(self, session: Session):
        super().__init__(session, ComplianceDeclarationModel)

    def list_for_part(self, part_id: str) -> list[ComplianceDeclarationModel]:
        """List compliance declarations for a part."""
        return self.list(part_id=part_id)

    def get_for_regulation(
        self,
        part_id: str,
        regulation_id: str,
    ) -> Optional[ComplianceDeclarationModel]:
        """Get declaration for a specific part and regulation."""
        return self.get_by(part_id=part_id, regulation_id=regulation_id)

    def list_non_compliant(self) -> list[ComplianceDeclarationModel]:
        """List all non-compliant declarations."""
        return self.list(status="non_compliant")

    def list_expiring_soon(self, days: int = 30) -> list[ComplianceDeclarationModel]:
        """List declarations expiring within specified days."""
        stmt = select(self.model_class).filter(
            ComplianceDeclarationModel.expires.isnot(None),
            ComplianceDeclarationModel.expires <= date.today().replace(
                day=date.today().day + days
            ),
        )
        return list(self.session.execute(stmt).scalars().all())


class ComplianceCertificateRepository(BaseRepository[ComplianceCertificateModel]):
    """Repository for compliance certificates."""

    def __init__(self, session: Session):
        super().__init__(session, ComplianceCertificateModel)

    def find_by_number(self, cert_number: str) -> Optional[ComplianceCertificateModel]:
        """Find certificate by number."""
        return self.get_by(certificate_number=cert_number)

    def list_active(self) -> list[ComplianceCertificateModel]:
        """List active certificates."""
        return self.list(status="active")

    def list_expiring_soon(self, days: int = 30) -> list[ComplianceCertificateModel]:
        """List certificates expiring soon."""
        from datetime import timedelta

        cutoff = date.today() + timedelta(days=days)
        stmt = select(self.model_class).filter(
            ComplianceCertificateModel.status == "active",
            ComplianceCertificateModel.expiry_date.isnot(None),
            ComplianceCertificateModel.expiry_date <= cutoff,
        )
        return list(self.session.execute(stmt).scalars().all())


class ConflictMineralRepository(BaseRepository[ConflictMineralDeclarationModel]):
    """Repository for conflict mineral declarations."""

    def __init__(self, session: Session):
        super().__init__(session, ConflictMineralDeclarationModel)

    def get_for_part(self, part_id: str) -> Optional[ConflictMineralDeclarationModel]:
        """Get 3TG declaration for a part."""
        return self.get_by(part_id=part_id)

    def list_containing_3tg(self) -> list[ConflictMineralDeclarationModel]:
        """List parts containing 3TG minerals."""
        from sqlalchemy import or_

        stmt = select(self.model_class).filter(
            or_(
                ConflictMineralDeclarationModel.contains_tin == True,
                ConflictMineralDeclarationModel.contains_tantalum == True,
                ConflictMineralDeclarationModel.contains_tungsten == True,
                ConflictMineralDeclarationModel.contains_gold == True,
            )
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_not_conflict_free(self) -> list[ConflictMineralDeclarationModel]:
        """List parts not declared conflict-free."""
        stmt = select(self.model_class).filter(
            ConflictMineralDeclarationModel.conflict_free == False
        )
        return list(self.session.execute(stmt).scalars().all())
