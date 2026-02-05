"""
Requirements Service

Business logic for requirements management and traceability.
"""

import uuid
from datetime import datetime
from typing import Optional

from .models import (
    Requirement,
    RequirementLink,
    VerificationRecord,
    TraceabilityMatrix,
    RequirementType,
    RequirementStatus,
    RequirementPriority,
    VerificationMethod,
    VerificationStatus,
)


class RequirementsService:
    """
    Manages requirements, traceability, and verification.
    """

    def __init__(self):
        # In-memory storage (replace with database)
        self._requirements: dict[str, Requirement] = {}
        self._links: dict[str, RequirementLink] = {}
        self._verifications: dict[str, VerificationRecord] = {}

        # Counters
        self._req_counter = 0
        self._ver_counter = 0

    # =========================================================================
    # Requirements CRUD
    # =========================================================================

    def create_requirement(
        self,
        title: str,
        description: str,
        requirement_type: RequirementType,
        priority: RequirementPriority = RequirementPriority.MUST_HAVE,
        source: str = "",
        source_document: Optional[str] = None,
        verification_method: VerificationMethod = VerificationMethod.TEST,
        acceptance_criteria: str = "",
        rationale: str = "",
        parent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Requirement:
        """Create a new requirement."""
        self._req_counter += 1
        req_id = str(uuid.uuid4())

        # Generate requirement number based on type
        type_prefix = requirement_type.value[:3].upper()
        req_number = f"{type_prefix}-{self._req_counter:04d}"

        req = Requirement(
            id=req_id,
            requirement_number=req_number,
            requirement_type=requirement_type,
            priority=priority,
            title=title,
            description=description,
            rationale=rationale,
            acceptance_criteria=acceptance_criteria,
            source=source,
            source_document=source_document,
            verification_method=verification_method,
            parent_id=parent_id,
            project_id=project_id,
            created_by=created_by,
        )

        self._requirements[req_id] = req
        return req

    def get_requirement(self, requirement_id: str) -> Optional[Requirement]:
        """Get requirement by ID."""
        return self._requirements.get(requirement_id)

    def list_requirements(
        self,
        requirement_type: Optional[RequirementType] = None,
        status: Optional[RequirementStatus] = None,
        priority: Optional[RequirementPriority] = None,
        project_id: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> list[Requirement]:
        """List requirements with optional filters."""
        results = list(self._requirements.values())

        if requirement_type:
            results = [r for r in results if r.requirement_type == requirement_type]

        if status:
            results = [r for r in results if r.status == status]

        if priority:
            results = [r for r in results if r.priority == priority]

        if project_id:
            results = [r for r in results if r.project_id == project_id]

        if parent_id:
            results = [r for r in results if r.parent_id == parent_id]

        return sorted(results, key=lambda r: r.requirement_number)

    def update_requirement(
        self,
        requirement_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[RequirementPriority] = None,
        acceptance_criteria: Optional[str] = None,
        verification_method: Optional[VerificationMethod] = None,
    ) -> Optional[Requirement]:
        """Update requirement fields."""
        req = self._requirements.get(requirement_id)
        if not req:
            return None

        if title is not None:
            req.title = title
        if description is not None:
            req.description = description
        if priority is not None:
            req.priority = priority
        if acceptance_criteria is not None:
            req.acceptance_criteria = acceptance_criteria
        if verification_method is not None:
            req.verification_method = verification_method

        return req

    def approve_requirement(
        self,
        requirement_id: str,
        approved_by: str,
    ) -> Optional[Requirement]:
        """Approve a requirement."""
        req = self._requirements.get(requirement_id)
        if not req:
            return None

        req.status = RequirementStatus.APPROVED
        req.approved_by = approved_by
        req.approved_date = datetime.now()

        return req

    def change_status(
        self,
        requirement_id: str,
        status: RequirementStatus,
    ) -> Optional[Requirement]:
        """Change requirement status."""
        req = self._requirements.get(requirement_id)
        if not req:
            return None

        req.status = status
        return req

    # =========================================================================
    # Requirement Links (Traceability)
    # =========================================================================

    def link_requirement(
        self,
        requirement_id: str,
        link_type: str,
        target_id: str,
        target_number: Optional[str] = None,
        target_revision: Optional[str] = None,
        relationship: str = "implements",
        coverage: str = "full",
        coverage_notes: str = "",
        created_by: Optional[str] = None,
    ) -> Optional[RequirementLink]:
        """Link a requirement to an implementing item."""
        req = self._requirements.get(requirement_id)
        if not req:
            return None

        link_id = str(uuid.uuid4())

        link = RequirementLink(
            id=link_id,
            requirement_id=requirement_id,
            link_type=link_type,
            target_id=target_id,
            target_number=target_number,
            target_revision=target_revision,
            relationship=relationship,
            coverage=coverage,
            coverage_notes=coverage_notes,
            created_by=created_by,
        )

        self._links[link_id] = link

        # Update requirement status
        if req.status == RequirementStatus.APPROVED:
            req.status = RequirementStatus.IMPLEMENTED

        return link

    def get_links_for_requirement(self, requirement_id: str) -> list[RequirementLink]:
        """Get all links for a requirement."""
        return [
            link for link in self._links.values()
            if link.requirement_id == requirement_id
        ]

    def get_requirements_for_target(
        self,
        target_id: str,
        link_type: Optional[str] = None,
    ) -> list[Requirement]:
        """Get requirements linked to a target (part, document, etc.)."""
        links = [
            link for link in self._links.values()
            if link.target_id == target_id and
            (link_type is None or link.link_type == link_type)
        ]

        req_ids = {link.requirement_id for link in links}
        return [
            self._requirements[req_id]
            for req_id in req_ids
            if req_id in self._requirements
        ]

    def remove_link(self, link_id: str) -> bool:
        """Remove a requirement link."""
        if link_id in self._links:
            del self._links[link_id]
            return True
        return False

    # =========================================================================
    # Verification Records
    # =========================================================================

    def create_verification(
        self,
        requirement_id: str,
        method: VerificationMethod,
        procedure_id: Optional[str] = None,
        procedure_number: Optional[str] = None,
    ) -> Optional[VerificationRecord]:
        """Create a verification record for a requirement."""
        req = self._requirements.get(requirement_id)
        if not req:
            return None

        self._ver_counter += 1
        ver_id = str(uuid.uuid4())
        ver_number = f"VER-{self._ver_counter:04d}"

        verification = VerificationRecord(
            id=ver_id,
            verification_number=ver_number,
            requirement_id=requirement_id,
            requirement_number=req.requirement_number,
            method=method,
            procedure_id=procedure_id,
            procedure_number=procedure_number,
        )

        self._verifications[ver_id] = verification
        return verification

    def get_verification(self, verification_id: str) -> Optional[VerificationRecord]:
        """Get verification record by ID."""
        return self._verifications.get(verification_id)

    def get_verifications_for_requirement(
        self,
        requirement_id: str,
    ) -> list[VerificationRecord]:
        """Get all verifications for a requirement."""
        return [
            v for v in self._verifications.values()
            if v.requirement_id == requirement_id
        ]

    def record_verification_result(
        self,
        verification_id: str,
        passed: bool,
        result_summary: str,
        verified_by: str,
        actual_value: Optional[str] = None,
        expected_value: Optional[str] = None,
        deviation: Optional[str] = None,
        evidence_documents: Optional[list[str]] = None,
    ) -> Optional[VerificationRecord]:
        """Record the result of a verification."""
        ver = self._verifications.get(verification_id)
        if not ver:
            return None

        ver.status = VerificationStatus.PASSED if passed else VerificationStatus.FAILED
        ver.pass_fail = passed
        ver.result_summary = result_summary
        ver.verified_by = verified_by
        ver.verified_date = datetime.now()

        if actual_value:
            ver.actual_value = actual_value
        if expected_value:
            ver.expected_value = expected_value
        if deviation:
            ver.deviation = deviation
        if evidence_documents:
            ver.evidence_documents = evidence_documents

        # Update requirement status
        req = self._requirements.get(ver.requirement_id)
        if req and passed:
            req.status = RequirementStatus.VERIFIED

        return ver

    def approve_verification(
        self,
        verification_id: str,
        approved_by: str,
    ) -> Optional[VerificationRecord]:
        """Approve a verification record."""
        ver = self._verifications.get(verification_id)
        if not ver:
            return None

        ver.approved_by = approved_by
        ver.approved_date = datetime.now()

        return ver

    # =========================================================================
    # Traceability Matrix
    # =========================================================================

    def generate_traceability_matrix(
        self,
        project_id: str,
    ) -> TraceabilityMatrix:
        """Generate a traceability matrix for a project."""
        # Get all requirements for project
        requirements = self.list_requirements(project_id=project_id)

        rows = []
        implemented_count = 0
        verified_count = 0
        failed_count = 0
        not_started_count = 0

        for req in requirements:
            # Get links
            links = self.get_links_for_requirement(req.id)
            link_info = [
                {
                    "type": link.link_type,
                    "target": link.target_number or link.target_id,
                    "coverage": link.coverage,
                }
                for link in links
            ]

            # Get verifications
            verifications = self.get_verifications_for_requirement(req.id)
            ver_info = [
                {
                    "number": v.verification_number,
                    "method": v.method.value,
                    "status": v.status.value,
                    "passed": v.pass_fail,
                }
                for v in verifications
            ]

            # Determine overall verification status
            if verifications:
                if any(v.status == VerificationStatus.FAILED for v in verifications):
                    ver_status = "failed"
                    failed_count += 1
                elif all(v.status == VerificationStatus.PASSED for v in verifications):
                    ver_status = "passed"
                    verified_count += 1
                else:
                    ver_status = "in_progress"
            else:
                ver_status = "not_started"
                not_started_count += 1

            if links:
                implemented_count += 1

            rows.append({
                "requirement_id": req.id,
                "requirement_number": req.requirement_number,
                "title": req.title,
                "type": req.requirement_type.value,
                "priority": req.priority.value,
                "status": req.status.value,
                "links": link_info,
                "verifications": ver_info,
                "verification_status": ver_status,
            })

        total = len(requirements)
        impl_coverage = (implemented_count / total * 100) if total > 0 else 0
        ver_coverage = (verified_count / total * 100) if total > 0 else 0

        return TraceabilityMatrix(
            project_id=project_id,
            total_requirements=total,
            implemented_count=implemented_count,
            verified_count=verified_count,
            failed_count=failed_count,
            not_started_count=not_started_count,
            implementation_coverage=impl_coverage,
            verification_coverage=ver_coverage,
            rows=rows,
        )

    def get_orphan_requirements(self, project_id: str) -> list[Requirement]:
        """Get requirements with no implementations."""
        requirements = self.list_requirements(project_id=project_id)
        orphans = []

        for req in requirements:
            links = self.get_links_for_requirement(req.id)
            if not links:
                orphans.append(req)

        return orphans

    def get_unverified_requirements(self, project_id: str) -> list[Requirement]:
        """Get requirements with no passing verification."""
        requirements = self.list_requirements(project_id=project_id)
        unverified = []

        for req in requirements:
            verifications = self.get_verifications_for_requirement(req.id)
            if not any(v.pass_fail for v in verifications):
                unverified.append(req)

        return unverified


# Singleton instance
_requirements_service: Optional[RequirementsService] = None


def get_requirements_service() -> RequirementsService:
    """Get the requirements service singleton."""
    global _requirements_service
    if _requirements_service is None:
        _requirements_service = RequirementsService()
    return _requirements_service
