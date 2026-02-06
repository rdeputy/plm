"""
Requirements Repository

Database operations for requirements, links, and verifications.
"""

from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

from plm.db.repository import BaseRepository
from plm.db.models import (
    RequirementModel,
    RequirementLinkModel,
    VerificationRecordModel,
)


class RequirementRepository(BaseRepository[RequirementModel]):
    """Repository for requirements."""

    def __init__(self, session: Session):
        super().__init__(session, RequirementModel)

    def find_by_number(self, requirement_number: str) -> Optional[RequirementModel]:
        """Find requirement by number."""
        return self.get_by(requirement_number=requirement_number)

    def list_by_project(
        self,
        project_id: str,
        status: Optional[str] = None,
        requirement_type: Optional[str] = None,
    ) -> list[RequirementModel]:
        """List requirements for a project."""
        return self.list(
            project_id=project_id,
            status=status,
            requirement_type=requirement_type,
            order_by="requirement_number",
        )

    def list_children(self, parent_id: str) -> list[RequirementModel]:
        """List child requirements."""
        return self.list(parent_id=parent_id, order_by="requirement_number")


class RequirementLinkRepository(BaseRepository[RequirementLinkModel]):
    """Repository for requirement links."""

    def __init__(self, session: Session):
        super().__init__(session, RequirementLinkModel)

    def list_by_requirement(self, requirement_id: str) -> list[RequirementLinkModel]:
        """List links for a requirement."""
        return self.list(requirement_id=requirement_id)

    def list_by_target(
        self,
        target_id: str,
        link_type: Optional[str] = None,
    ) -> list[RequirementLinkModel]:
        """List links to a target."""
        return self.list(target_id=target_id, link_type=link_type)


class VerificationRepository(BaseRepository[VerificationRecordModel]):
    """Repository for verification records."""

    def __init__(self, session: Session):
        super().__init__(session, VerificationRecordModel)

    def list_by_requirement(
        self,
        requirement_id: str,
        status: Optional[str] = None,
    ) -> list[VerificationRecordModel]:
        """List verifications for a requirement."""
        return self.list(requirement_id=requirement_id, status=status)

    def record_result(
        self,
        verification_id: str,
        passed: bool,
        result_summary: str,
        verified_by: str,
    ) -> Optional[VerificationRecordModel]:
        """Record verification result."""
        return self.update(
            verification_id,
            status="passed" if passed else "failed",
            pass_fail=passed,
            result_summary=result_summary,
            verified_by=verified_by,
            verified_date=datetime.now(),
        )
