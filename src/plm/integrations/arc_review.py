"""
ARC-Review Integration

Integration with the Architectural Review Committee (ARC) system.
Handles:
- Submitting design changes for ARC approval
- Checking compliance status
- Tracking ARC decisions and conditions
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import httpx


class SubmissionStatus(str, Enum):
    """Status of an ARC submission."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    CONDITIONALLY_APPROVED = "conditionally_approved"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"


class ChangeCategory(str, Enum):
    """Categories of changes that require ARC review."""

    EXTERIOR = "exterior"  # Exterior modifications
    STRUCTURAL = "structural"  # Structural changes
    LANDSCAPE = "landscape"  # Landscaping changes
    COLOR = "color"  # Paint/color changes
    FENCE = "fence"  # Fence/wall changes
    ADDITION = "addition"  # Room additions
    SOLAR = "solar"  # Solar panel installation
    ROOF = "roof"  # Roofing changes
    WINDOW = "window"  # Window replacements
    OTHER = "other"


@dataclass
class ARCCondition:
    """A condition attached to an ARC approval."""

    id: str
    description: str
    due_date: Optional[datetime] = None
    satisfied: bool = False
    satisfied_at: Optional[datetime] = None
    evidence_url: Optional[str] = None


@dataclass
class ARCSubmission:
    """An ARC submission for design changes."""

    id: str
    submission_number: str
    project_id: str
    project_address: str

    # Submission details
    title: str
    description: str
    category: ChangeCategory
    estimated_cost: float = 0
    contractor: Optional[str] = None

    # Status
    status: SubmissionStatus = SubmissionStatus.DRAFT
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewer: Optional[str] = None

    # Decision
    decision_notes: Optional[str] = None
    conditions: list[ARCCondition] = field(default_factory=list)
    approval_expires: Optional[datetime] = None

    # Related PLM entities
    eco_id: Optional[str] = None
    part_ids: list[str] = field(default_factory=list)

    # Documents
    documents: list[dict] = field(default_factory=list)  # [{name, url, type}]


class ARCClient:
    """
    Client for communicating with the ARC-Review system.

    Used by PLM to:
    - Submit changes for ARC review
    - Check submission status
    - Update conditions status
    - Get compliance requirements
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def create_submission(
        self,
        project_id: str,
        project_address: str,
        title: str,
        description: str,
        category: ChangeCategory,
        estimated_cost: float = 0,
        contractor: Optional[str] = None,
        documents: Optional[list[dict]] = None,
        eco_id: Optional[str] = None,
        part_ids: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Create a new ARC submission.

        Returns submission info including ID and submission number.
        """
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/submissions",
                headers=self.headers,
                json={
                    "project_id": project_id,
                    "project_address": project_address,
                    "title": title,
                    "description": description,
                    "category": category.value,
                    "estimated_cost": estimated_cost,
                    "contractor": contractor,
                    "documents": documents or [],
                    "eco_id": eco_id,
                    "part_ids": part_ids or [],
                },
            )
            response.raise_for_status()
            return response.json()

    def submit_for_review(self, submission_id: str) -> dict[str, Any]:
        """Submit a draft submission for ARC review."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/submissions/{submission_id}/submit",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    def get_submission(self, submission_id: str) -> dict[str, Any]:
        """Get submission details."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/api/submissions/{submission_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    def get_submission_status(self, submission_id: str) -> dict[str, Any]:
        """Get current status of a submission."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/api/submissions/{submission_id}/status",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    def list_submissions(
        self,
        project_id: Optional[str] = None,
        status: Optional[SubmissionStatus] = None,
        eco_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List submissions with optional filters."""
        params = {}
        if project_id:
            params["project_id"] = project_id
        if status:
            params["status"] = status.value
        if eco_id:
            params["eco_id"] = eco_id

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/api/submissions",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def add_document(
        self,
        submission_id: str,
        name: str,
        url: str,
        document_type: str = "drawing",
    ) -> dict[str, Any]:
        """Add a document to a submission."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/submissions/{submission_id}/documents",
                headers=self.headers,
                json={
                    "name": name,
                    "url": url,
                    "type": document_type,
                },
            )
            response.raise_for_status()
            return response.json()

    def withdraw_submission(
        self, submission_id: str, reason: str
    ) -> dict[str, Any]:
        """Withdraw a submission."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/submissions/{submission_id}/withdraw",
                headers=self.headers,
                json={"reason": reason},
            )
            response.raise_for_status()
            return response.json()

    def satisfy_condition(
        self,
        submission_id: str,
        condition_id: str,
        evidence_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """Mark a condition as satisfied."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/submissions/{submission_id}/conditions/{condition_id}/satisfy",
                headers=self.headers,
                json={
                    "evidence_url": evidence_url,
                    "notes": notes,
                },
            )
            response.raise_for_status()
            return response.json()

    def get_requirements(
        self, category: ChangeCategory, project_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get ARC requirements for a category of change.

        Returns required documents, review timeline, and guidelines.
        """
        params = {"category": category.value}
        if project_id:
            params["project_id"] = project_id

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/api/requirements",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def check_compliance(
        self,
        project_id: str,
        proposed_changes: list[dict],
    ) -> dict[str, Any]:
        """
        Pre-check if proposed changes comply with ARC guidelines.

        Returns compliance status and any potential issues.
        """
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/compliance/check",
                headers=self.headers,
                json={
                    "project_id": project_id,
                    "proposed_changes": proposed_changes,
                },
            )
            response.raise_for_status()
            return response.json()


class ARCComplianceChecker:
    """
    Local compliance checker for PLM changes.

    Evaluates if changes require ARC submission and
    pre-checks against common guidelines.
    """

    # Categories that typically require ARC review
    EXTERIOR_CATEGORIES = {
        "07 - Thermal and Moisture Protection",  # Roofing, siding
        "08 - Openings",  # Windows, doors
        "32 - Exterior Improvements",  # Landscaping
    }

    # CSI codes that typically need ARC review
    ARC_SENSITIVE_CSI_CODES = {
        "07 31 00",  # Shingles and Shakes
        "07 41 00",  # Roof Panels
        "07 46 00",  # Siding
        "08 51 00",  # Metal Windows
        "08 52 00",  # Wood Windows
        "08 54 00",  # Composite Windows
        "32 31 00",  # Fences and Gates
        "32 93 00",  # Plants
    }

    def check_requires_arc_review(
        self,
        part_ids: list[str],
        part_data: dict[str, dict],
    ) -> dict[str, Any]:
        """
        Check if changes to parts require ARC review.

        Args:
            part_ids: List of part IDs being changed
            part_data: Dict of part_id -> part info (category, csi_code, etc.)

        Returns:
            {
                "requires_review": bool,
                "reasons": list[str],
                "recommended_category": ChangeCategory,
                "affected_parts": list[str]
            }
        """
        requires_review = False
        reasons = []
        affected_parts = []
        categories = set()

        for part_id in part_ids:
            part = part_data.get(part_id, {})
            category = part.get("category", "")
            csi_code = part.get("csi_code", "")

            # Check category
            if category in self.EXTERIOR_CATEGORIES:
                requires_review = True
                reasons.append(f"Part {part_id} is in category '{category}'")
                affected_parts.append(part_id)
                categories.add(category)

            # Check CSI code
            if csi_code and any(
                csi_code.startswith(code) for code in self.ARC_SENSITIVE_CSI_CODES
            ):
                requires_review = True
                reasons.append(f"Part {part_id} has CSI code {csi_code}")
                if part_id not in affected_parts:
                    affected_parts.append(part_id)

        # Determine recommended category
        if "32 - Exterior Improvements" in categories:
            recommended = ChangeCategory.LANDSCAPE
        elif "07 - Thermal and Moisture Protection" in categories:
            recommended = ChangeCategory.ROOF
        elif "08 - Openings" in categories:
            recommended = ChangeCategory.WINDOW
        else:
            recommended = ChangeCategory.EXTERIOR

        return {
            "requires_review": requires_review,
            "reasons": reasons,
            "recommended_category": recommended,
            "affected_parts": affected_parts,
        }

    def validate_submission_completeness(
        self,
        submission_data: dict,
        requirements: dict,
    ) -> dict[str, Any]:
        """
        Validate that a submission has all required elements.

        Args:
            submission_data: The submission being prepared
            requirements: Requirements from ARC for this category

        Returns:
            {
                "is_complete": bool,
                "missing": list[str],
                "warnings": list[str]
            }
        """
        missing = []
        warnings = []

        # Check required documents
        required_docs = set(requirements.get("required_documents", []))
        provided_docs = {d.get("type") for d in submission_data.get("documents", [])}
        missing_docs = required_docs - provided_docs
        if missing_docs:
            missing.extend([f"Missing document: {doc}" for doc in missing_docs])

        # Check required fields
        if not submission_data.get("description"):
            missing.append("Description is required")
        if not submission_data.get("title"):
            missing.append("Title is required")
        if not submission_data.get("project_address"):
            missing.append("Project address is required")

        # Cost threshold warnings
        cost = submission_data.get("estimated_cost", 0)
        if cost > 10000 and not submission_data.get("contractor"):
            warnings.append("Consider providing contractor info for projects > $10,000")

        return {
            "is_complete": len(missing) == 0,
            "missing": missing,
            "warnings": warnings,
        }
