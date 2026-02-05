"""
Quality Service

Centralized service for quality management operations.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from .models import (
    CAPA,
    CAPAStatus,
    CAPAType,
    DispositionType,
    InspectionRecord,
    NCRSeverity,
    NCRSource,
    NCRStatus,
    NonConformanceReport,
    QualityHold,
)

logger = logging.getLogger(__name__)


class QualityService:
    """
    Service for managing quality records.
    """

    def __init__(self):
        # In-memory storage (replace with DB)
        self._ncrs: dict[str, NonConformanceReport] = {}
        self._capas: dict[str, CAPA] = {}
        self._inspections: dict[str, InspectionRecord] = {}
        self._holds: dict[str, QualityHold] = {}

        # Counters for generating numbers
        self._ncr_counter = 0
        self._capa_counter = 0
        self._inspection_counter = 0
        self._hold_counter = 0

    # =========================================================================
    # NCR Management
    # =========================================================================

    def create_ncr(
        self,
        title: str,
        description: str,
        severity: NCRSeverity,
        source: NCRSource,
        created_by: str,
        part_id: Optional[str] = None,
        part_number: Optional[str] = None,
        lot_number: Optional[str] = None,
        quantity_affected: Decimal = Decimal("1"),
        project_id: Optional[str] = None,
        supplier_id: Optional[str] = None,
        po_id: Optional[str] = None,
    ) -> NonConformanceReport:
        """Create a new NCR."""
        self._ncr_counter += 1
        ncr_number = f"NCR-{datetime.now().year}-{self._ncr_counter:04d}"

        ncr = NonConformanceReport(
            id=str(uuid4()),
            ncr_number=ncr_number,
            title=title,
            description=description,
            severity=severity,
            source=source,
            status=NCRStatus.OPEN,
            part_id=part_id,
            part_number=part_number,
            lot_number=lot_number,
            quantity_affected=quantity_affected,
            project_id=project_id,
            supplier_id=supplier_id,
            po_id=po_id,
            created_by=created_by,
            detected_by=created_by,
        )

        self._ncrs[ncr.id] = ncr
        logger.info(f"Created NCR {ncr_number}")

        # Auto-create hold for critical/major NCRs
        if severity in [NCRSeverity.CRITICAL, NCRSeverity.MAJOR]:
            self.create_hold(
                reason=f"NCR: {title}",
                hold_type="ncr",
                part_number=part_number,
                lot_number=lot_number,
                quantity=quantity_affected,
                ncr_id=ncr.id,
                placed_by=created_by,
            )

        return ncr

    def get_ncr(self, ncr_id: str) -> Optional[NonConformanceReport]:
        """Get an NCR by ID."""
        return self._ncrs.get(ncr_id)

    def list_ncrs(
        self,
        status: Optional[NCRStatus] = None,
        severity: Optional[NCRSeverity] = None,
        part_number: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[NonConformanceReport]:
        """List NCRs with filters."""
        ncrs = list(self._ncrs.values())

        if status:
            ncrs = [n for n in ncrs if n.status == status]
        if severity:
            ncrs = [n for n in ncrs if n.severity == severity]
        if part_number:
            ncrs = [n for n in ncrs if n.part_number == part_number]
        if project_id:
            ncrs = [n for n in ncrs if n.project_id == project_id]

        ncrs.sort(key=lambda n: n.created_at or datetime.min, reverse=True)
        return ncrs[:limit]

    def update_ncr_status(
        self,
        ncr_id: str,
        status: NCRStatus,
        user_id: str,
        notes: Optional[str] = None,
    ) -> Optional[NonConformanceReport]:
        """Update NCR status."""
        ncr = self.get_ncr(ncr_id)
        if not ncr:
            return None

        ncr.status = status

        if status == NCRStatus.CLOSED:
            ncr.closed_at = datetime.now()
            ncr.closed_by = user_id
            # Release any holds
            for hold in self._holds.values():
                if hold.ncr_id == ncr_id and hold.is_active:
                    self.release_hold(hold.id, user_id, "NCR closed")

        return ncr

    def set_disposition(
        self,
        ncr_id: str,
        disposition: DispositionType,
        disposition_by: str,
        notes: Optional[str] = None,
    ) -> Optional[NonConformanceReport]:
        """Set NCR disposition."""
        ncr = self.get_ncr(ncr_id)
        if not ncr:
            return None

        ncr.disposition = disposition
        ncr.disposition_by = disposition_by
        ncr.disposition_date = datetime.now()
        ncr.disposition_notes = notes
        ncr.status = NCRStatus.DISPOSITION_APPROVED

        return ncr

    def link_capa(
        self,
        ncr_id: str,
        capa_id: str,
    ) -> Optional[NonConformanceReport]:
        """Link a CAPA to an NCR."""
        ncr = self.get_ncr(ncr_id)
        if not ncr:
            return None

        ncr.capa_id = capa_id
        ncr.capa_required = True

        # Also add NCR to CAPA
        capa = self.get_capa(capa_id)
        if capa and ncr_id not in capa.ncr_ids:
            capa.ncr_ids.append(ncr_id)

        return ncr

    # =========================================================================
    # CAPA Management
    # =========================================================================

    def create_capa(
        self,
        title: str,
        description: str,
        capa_type: CAPAType,
        initiated_by: str,
        owner_id: str,
        problem_statement: str = "",
        ncr_ids: list[str] | None = None,
        priority: str = "medium",
        due_date: Optional[date] = None,
    ) -> CAPA:
        """Create a new CAPA."""
        self._capa_counter += 1
        capa_number = f"CAPA-{datetime.now().year}-{self._capa_counter:04d}"

        capa = CAPA(
            id=str(uuid4()),
            capa_number=capa_number,
            capa_type=capa_type,
            status=CAPAStatus.OPEN,
            title=title,
            description=description,
            problem_statement=problem_statement,
            ncr_ids=ncr_ids or [],
            priority=priority,
            owner_id=owner_id,
            initiated_by=initiated_by,
            due_date=due_date,
        )

        self._capas[capa.id] = capa
        logger.info(f"Created CAPA {capa_number}")

        # Link NCRs to this CAPA
        for ncr_id in capa.ncr_ids:
            ncr = self.get_ncr(ncr_id)
            if ncr:
                ncr.capa_id = capa.id
                ncr.capa_required = True

        return capa

    def get_capa(self, capa_id: str) -> Optional[CAPA]:
        """Get a CAPA by ID."""
        return self._capas.get(capa_id)

    def list_capas(
        self,
        status: Optional[CAPAStatus] = None,
        capa_type: Optional[CAPAType] = None,
        owner_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[CAPA]:
        """List CAPAs with filters."""
        capas = list(self._capas.values())

        if status:
            capas = [c for c in capas if c.status == status]
        if capa_type:
            capas = [c for c in capas if c.capa_type == capa_type]
        if owner_id:
            capas = [c for c in capas if c.owner_id == owner_id]

        capas.sort(key=lambda c: c.created_at or datetime.min, reverse=True)
        return capas[:limit]

    def update_capa_status(
        self,
        capa_id: str,
        status: CAPAStatus,
        user_id: str,
    ) -> Optional[CAPA]:
        """Update CAPA status."""
        capa = self.get_capa(capa_id)
        if not capa:
            return None

        capa.status = status

        if status == CAPAStatus.CLOSED:
            capa.closed_date = datetime.now()
            capa.closed_by = user_id

        return capa

    def add_root_cause(
        self,
        capa_id: str,
        root_cause: str,
        analysis_method: str = "",
    ) -> Optional[CAPA]:
        """Add a root cause to CAPA."""
        capa = self.get_capa(capa_id)
        if not capa:
            return None

        capa.root_causes.append(root_cause)
        if analysis_method:
            capa.root_cause_method = analysis_method

        return capa

    def add_action(
        self,
        capa_id: str,
        action_type: str,  # immediate, corrective, preventive
        description: str,
        responsible: str,
        due_date: Optional[date] = None,
    ) -> Optional[CAPA]:
        """Add an action to CAPA."""
        capa = self.get_capa(capa_id)
        if not capa:
            return None

        action = {
            "id": str(uuid4()),
            "description": description,
            "responsible": responsible,
            "due_date": due_date.isoformat() if due_date else None,
            "status": "open",
            "completed_date": None,
        }

        if action_type == "immediate":
            capa.immediate_actions.append(action)
        elif action_type == "corrective":
            capa.corrective_actions.append(action)
        elif action_type == "preventive":
            capa.preventive_actions.append(action)

        return capa

    def verify_capa(
        self,
        capa_id: str,
        verified_by: str,
        method: str,
        results: str,
    ) -> Optional[CAPA]:
        """Record CAPA verification."""
        capa = self.get_capa(capa_id)
        if not capa:
            return None

        capa.verification_method = method
        capa.verification_results = results
        capa.verified_by = verified_by
        capa.verified_date = datetime.now()
        capa.status = CAPAStatus.EFFECTIVENESS_REVIEW

        return capa

    # =========================================================================
    # Inspection Management
    # =========================================================================

    def create_inspection(
        self,
        inspection_type: str,
        inspector_id: str,
        inspector_name: str,
        part_number: Optional[str] = None,
        lot_number: Optional[str] = None,
        po_id: Optional[str] = None,
        quantity_inspected: Decimal = Decimal("0"),
    ) -> InspectionRecord:
        """Create a new inspection record."""
        self._inspection_counter += 1
        inspection_number = f"INS-{datetime.now().year}-{self._inspection_counter:04d}"

        inspection = InspectionRecord(
            id=str(uuid4()),
            inspection_number=inspection_number,
            inspection_type=inspection_type,
            part_number=part_number,
            lot_number=lot_number,
            po_id=po_id,
            quantity_inspected=quantity_inspected,
            inspector_id=inspector_id,
            inspector_name=inspector_name,
            inspection_date=date.today(),
        )

        self._inspections[inspection.id] = inspection
        return inspection

    def complete_inspection(
        self,
        inspection_id: str,
        result: str,
        quantity_accepted: Decimal,
        quantity_rejected: Decimal,
        defects: list[dict] | None = None,
        measurements: list[dict] | None = None,
        create_ncr_if_failed: bool = True,
        inspector_id: Optional[str] = None,
    ) -> InspectionRecord:
        """Complete an inspection with results."""
        inspection = self._inspections.get(inspection_id)
        if not inspection:
            raise ValueError(f"Inspection not found: {inspection_id}")

        inspection.result = result
        inspection.quantity_accepted = quantity_accepted
        inspection.quantity_rejected = quantity_rejected
        inspection.completed_at = datetime.now()

        if defects:
            inspection.defects_found = defects
        if measurements:
            inspection.measurements = measurements

        # Auto-create NCR for failed inspections
        if result == "fail" and create_ncr_if_failed and inspection.quantity_rejected > 0:
            ncr = self.create_ncr(
                title=f"Inspection failure: {inspection.part_number or 'Unknown'}",
                description=f"Failed {inspection.inspection_type} inspection. {len(inspection.defects_found)} defects found.",
                severity=NCRSeverity.MAJOR,
                source=NCRSource.INCOMING_INSPECTION if inspection.inspection_type == "receiving" else NCRSource.IN_PROCESS,
                created_by=inspector_id or inspection.inspector_id or "system",
                part_number=inspection.part_number,
                lot_number=inspection.lot_number,
                quantity_affected=inspection.quantity_rejected,
                po_id=inspection.po_id,
            )
            inspection.ncr_id = ncr.id

        return inspection

    def get_inspection(self, inspection_id: str) -> Optional[InspectionRecord]:
        """Get an inspection by ID."""
        return self._inspections.get(inspection_id)

    def list_inspections(
        self,
        inspection_type: Optional[str] = None,
        result: Optional[str] = None,
        part_number: Optional[str] = None,
        limit: int = 100,
    ) -> list[InspectionRecord]:
        """List inspections with filters."""
        inspections = list(self._inspections.values())

        if inspection_type:
            inspections = [i for i in inspections if i.inspection_type == inspection_type]
        if result:
            inspections = [i for i in inspections if i.result == result]
        if part_number:
            inspections = [i for i in inspections if i.part_number == part_number]

        inspections.sort(key=lambda i: i.created_at or datetime.min, reverse=True)
        return inspections[:limit]

    # =========================================================================
    # Hold Management
    # =========================================================================

    def create_hold(
        self,
        reason: str,
        hold_type: str,
        placed_by: str,
        part_number: Optional[str] = None,
        lot_number: Optional[str] = None,
        quantity: Decimal = Decimal("0"),
        ncr_id: Optional[str] = None,
        location_id: Optional[str] = None,
    ) -> QualityHold:
        """Create a quality hold."""
        self._hold_counter += 1
        hold_number = f"HOLD-{datetime.now().year}-{self._hold_counter:04d}"

        hold = QualityHold(
            id=str(uuid4()),
            hold_number=hold_number,
            reason=reason,
            hold_type=hold_type,
            part_number=part_number,
            lot_number=lot_number,
            quantity=quantity,
            ncr_id=ncr_id,
            location_id=location_id,
            placed_by=placed_by,
        )

        self._holds[hold.id] = hold
        logger.info(f"Created hold {hold_number}")

        return hold

    def release_hold(
        self,
        hold_id: str,
        released_by: str,
        notes: Optional[str] = None,
    ) -> Optional[QualityHold]:
        """Release a quality hold."""
        hold = self._holds.get(hold_id)
        if not hold:
            return None

        hold.is_active = False
        hold.released_by = released_by
        hold.released_at = datetime.now()
        hold.release_notes = notes

        logger.info(f"Released hold {hold.hold_number}")

        return hold

    def get_hold(self, hold_id: str) -> Optional[QualityHold]:
        """Get a hold by ID."""
        return self._holds.get(hold_id)

    def list_holds(
        self,
        active_only: bool = False,
        part_number: Optional[str] = None,
        limit: int = 100,
    ) -> list[QualityHold]:
        """List quality holds."""
        holds = list(self._holds.values())

        if active_only:
            holds = [h for h in holds if h.is_active]
        if part_number:
            holds = [h for h in holds if h.part_number == part_number]

        holds.sort(key=lambda h: h.placed_at or datetime.min, reverse=True)
        return holds[:limit]

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_quality_metrics(self) -> dict:
        """Get quality metrics summary."""
        open_ncrs = [n for n in self._ncrs.values() if n.status not in [NCRStatus.CLOSED, NCRStatus.VOIDED]]
        open_capas = [c for c in self._capas.values() if c.status != CAPAStatus.CLOSED]
        active_holds = [h for h in self._holds.values() if h.is_active]

        return {
            "ncrs": {
                "total": len(self._ncrs),
                "open": len(open_ncrs),
                "critical": len([n for n in open_ncrs if n.severity == NCRSeverity.CRITICAL]),
                "pending_disposition": len([n for n in open_ncrs if n.status == NCRStatus.PENDING_DISPOSITION]),
            },
            "capas": {
                "total": len(self._capas),
                "open": len(open_capas),
                "overdue": len([c for c in open_capas if c.due_date and c.due_date < date.today()]),
            },
            "inspections": {
                "total": len(self._inspections),
                "failed": len([i for i in self._inspections.values() if i.result == "fail"]),
            },
            "holds": {
                "active": len(active_holds),
            },
        }


# Singleton instance
_service: Optional[QualityService] = None


def get_quality_service() -> QualityService:
    """Get the singleton quality service instance."""
    global _service
    if _service is None:
        _service = QualityService()
    return _service
