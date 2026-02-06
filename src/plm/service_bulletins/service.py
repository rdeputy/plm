"""
Service Bulletins Service

Business logic for aviation service bulletins and maintenance.
"""

from typing import Optional
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from plm.service_bulletins.repository import (
    ServiceBulletinRepository,
    BulletinComplianceRepository,
    MaintenanceScheduleRepository,
    UnitConfigurationRepository,
)
from plm.db.models import (
    ServiceBulletinModel,
    BulletinComplianceModel,
    MaintenanceScheduleModel,
    UnitConfigurationModel,
)


@dataclass
class BulletinStats:
    """Statistics for service bulletins."""

    total: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    safety_related: int
    pending_compliance: int
    overdue: int


@dataclass
class UnitStatus:
    """Status summary for a unit."""

    serial_number: str
    part_number: str
    total_hours: float
    total_cycles: int
    pending_bulletins: int
    overdue_bulletins: int
    maintenance_due: bool
    days_to_maintenance: Optional[int]


class ServiceBulletinService:
    """Service for service bulletin management."""

    def __init__(self, session: Session):
        self.session = session
        self.bulletins = ServiceBulletinRepository(session)
        self.compliance = BulletinComplianceRepository(session)

    def create_bulletin(
        self,
        bulletin_number: str,
        bulletin_type: str,
        title: str,
        summary: str = "",
        description: str = "",
        reason: str = "",
        safety_issue: bool = False,
        action_required: str = "",
        compliance_deadline: Optional[date] = None,
        created_by: Optional[str] = None,
    ) -> ServiceBulletinModel:
        """Create a new service bulletin."""
        return self.bulletins.create(
            bulletin_number=bulletin_number,
            bulletin_type=bulletin_type,
            title=title,
            summary=summary,
            description=description,
            reason=reason,
            safety_issue=safety_issue,
            action_required=action_required,
            compliance_deadline=compliance_deadline,
            status="draft",
            created_by=created_by,
        )

    def get_bulletin(self, bulletin_id: str) -> Optional[ServiceBulletinModel]:
        """Get bulletin by ID."""
        return self.bulletins.get(bulletin_id)

    def get_bulletin_by_number(
        self,
        bulletin_number: str,
    ) -> Optional[ServiceBulletinModel]:
        """Get bulletin by number."""
        return self.bulletins.find_by_number(bulletin_number)

    def approve_bulletin(
        self,
        bulletin_id: str,
        approved_by: str,
        effective_date: Optional[date] = None,
    ) -> Optional[ServiceBulletinModel]:
        """Approve and activate a bulletin."""
        from datetime import datetime

        return self.bulletins.update(
            bulletin_id,
            status="active",
            approved_by=approved_by,
            approved_date=datetime.now(),
            effective_date=effective_date or date.today(),
        )

    def list_active_bulletins(self) -> list[ServiceBulletinModel]:
        """List active bulletins."""
        return self.bulletins.list_by_status("active")

    def list_safety_bulletins(self) -> list[ServiceBulletinModel]:
        """List safety-related bulletins."""
        return self.bulletins.list_safety_related()

    def list_expiring_bulletins(self, days: int = 30) -> list[ServiceBulletinModel]:
        """List bulletins with approaching compliance deadline."""
        return self.bulletins.list_expiring_soon(days)

    def create_compliance_record(
        self,
        bulletin_id: str,
        serial_number: str,
        part_id: Optional[str] = None,
        part_number: Optional[str] = None,
    ) -> BulletinComplianceModel:
        """Create compliance tracking record for a unit."""
        bulletin = self.bulletins.get(bulletin_id)
        if not bulletin:
            raise ValueError(f"Bulletin {bulletin_id} not found")

        return self.compliance.create(
            bulletin_id=bulletin_id,
            bulletin_number=bulletin.bulletin_number,
            serial_number=serial_number,
            part_id=part_id,
            part_number=part_number,
            status="pending",
        )

    def record_compliance(
        self,
        compliance_id: str,
        completed_by: str,
        work_order_number: Optional[str] = None,
        labor_hours: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Optional[BulletinComplianceModel]:
        """Record bulletin compliance completion."""
        return self.compliance.record_completion(
            compliance_id=compliance_id,
            completed_by=completed_by,
            work_order_number=work_order_number,
            labor_hours=labor_hours,
            notes=notes,
        )

    def waive_compliance(
        self,
        compliance_id: str,
        waiver_reason: str,
        waiver_approved_by: str,
        waiver_expiry: Optional[date] = None,
    ) -> Optional[BulletinComplianceModel]:
        """Waive bulletin compliance requirement."""
        return self.compliance.update(
            compliance_id,
            waived=True,
            waiver_reason=waiver_reason,
            waiver_approved_by=waiver_approved_by,
            waiver_expiry=waiver_expiry,
            status="waived",
        )

    def get_unit_compliance(
        self,
        serial_number: str,
    ) -> list[BulletinComplianceModel]:
        """Get compliance records for a unit."""
        return self.compliance.list_for_serial(serial_number)

    def get_overdue_compliance(self) -> list[BulletinComplianceModel]:
        """Get overdue compliance records."""
        return self.compliance.list_overdue()

    def get_stats(self) -> BulletinStats:
        """Get bulletin statistics."""
        all_bulletins = self.bulletins.list(limit=10000)
        pending = self.compliance.list_pending()
        overdue = self.compliance.list_overdue()

        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        safety_count = 0

        for b in all_bulletins:
            status = str(b.status.value) if hasattr(b.status, "value") else str(b.status)
            btype = str(b.bulletin_type.value) if hasattr(b.bulletin_type, "value") else str(b.bulletin_type)

            by_status[status] = by_status.get(status, 0) + 1
            by_type[btype] = by_type.get(btype, 0) + 1

            if b.safety_issue:
                safety_count += 1

        return BulletinStats(
            total=len(all_bulletins),
            by_status=by_status,
            by_type=by_type,
            safety_related=safety_count,
            pending_compliance=len(pending),
            overdue=len(overdue),
        )

    def commit(self):
        """Commit transaction."""
        self.session.commit()


class MaintenanceService:
    """Service for maintenance schedule management."""

    def __init__(self, session: Session):
        self.session = session
        self.schedules = MaintenanceScheduleRepository(session)

    def create_schedule(
        self,
        schedule_code: str,
        system: str,
        component: str,
        interval_type: str,
        interval_value: int,
        interval_unit: str,
        task_description: str,
        part_id: Optional[str] = None,
        part_number: Optional[str] = None,
        procedure_reference: Optional[str] = None,
        estimated_time: Optional[str] = None,
    ) -> MaintenanceScheduleModel:
        """Create a maintenance schedule."""
        return self.schedules.create(
            schedule_code=schedule_code,
            system=system,
            component=component,
            interval_type=interval_type,
            interval_value=interval_value,
            interval_unit=interval_unit,
            task_description=task_description,
            part_id=part_id,
            part_number=part_number,
            procedure_reference=procedure_reference,
            estimated_time=estimated_time,
            is_active=True,
        )

    def get_schedule(self, schedule_id: str) -> Optional[MaintenanceScheduleModel]:
        """Get schedule by ID."""
        return self.schedules.get(schedule_id)

    def get_schedule_by_code(self, code: str) -> Optional[MaintenanceScheduleModel]:
        """Get schedule by code."""
        return self.schedules.find_by_code(code)

    def list_by_system(self, system: str) -> list[MaintenanceScheduleModel]:
        """List schedules by system."""
        return self.schedules.list_by_system(system)

    def list_for_part(self, part_id: str) -> list[MaintenanceScheduleModel]:
        """List schedules for a part."""
        return self.schedules.list_for_part(part_id)

    def deactivate_schedule(
        self,
        schedule_id: str,
    ) -> Optional[MaintenanceScheduleModel]:
        """Deactivate a maintenance schedule."""
        return self.schedules.update(schedule_id, is_active=False)

    def commit(self):
        """Commit transaction."""
        self.session.commit()


class UnitConfigurationService:
    """Service for unit configuration management."""

    def __init__(self, session: Session):
        self.session = session
        self.units = UnitConfigurationRepository(session)
        self.compliance = BulletinComplianceRepository(session)

    def create_unit(
        self,
        serial_number: str,
        part_id: str,
        part_number: str,
        current_revision: str = "",
        build_date: Optional[date] = None,
        owner_id: Optional[str] = None,
        owner_name: str = "",
        location: str = "",
    ) -> UnitConfigurationModel:
        """Create a unit configuration record."""
        return self.units.create(
            serial_number=serial_number,
            part_id=part_id,
            part_number=part_number,
            current_revision=current_revision,
            build_date=build_date,
            owner_id=owner_id,
            owner_name=owner_name,
            location=location,
            total_hours=0.0,
            total_cycles=0,
        )

    def get_unit(self, unit_id: str) -> Optional[UnitConfigurationModel]:
        """Get unit by ID."""
        return self.units.get(unit_id)

    def get_unit_by_serial(
        self,
        serial_number: str,
    ) -> Optional[UnitConfigurationModel]:
        """Get unit by serial number."""
        return self.units.find_by_serial(serial_number)

    def update_usage(
        self,
        unit_id: str,
        hours: float,
        cycles: Optional[int] = None,
    ) -> Optional[UnitConfigurationModel]:
        """Update unit flight hours and cycles."""
        return self.units.update_hours(unit_id, hours, cycles)

    def get_unit_status(self, serial_number: str) -> Optional[UnitStatus]:
        """Get comprehensive status for a unit."""
        unit = self.units.find_by_serial(serial_number)
        if not unit:
            return None

        compliance_records = self.compliance.list_for_serial(serial_number)
        pending = [c for c in compliance_records if c.status == "pending"]

        overdue = 0
        for c in pending:
            bulletin = c.bulletin_id
            # Would need to join to check deadline

        days_to_maintenance = None
        if unit.next_maintenance_due:
            delta = unit.next_maintenance_due - date.today()
            days_to_maintenance = delta.days

        return UnitStatus(
            serial_number=serial_number,
            part_number=unit.part_number,
            total_hours=float(unit.total_hours),
            total_cycles=unit.total_cycles,
            pending_bulletins=len(pending),
            overdue_bulletins=overdue,
            maintenance_due=days_to_maintenance is not None and days_to_maintenance <= 0,
            days_to_maintenance=days_to_maintenance,
        )

    def list_units_for_part(self, part_id: str) -> list[UnitConfigurationModel]:
        """List units for a part."""
        return self.units.list_for_part(part_id)

    def list_maintenance_due(self, days: int = 30) -> list[UnitConfigurationModel]:
        """List units with maintenance due soon."""
        return self.units.list_maintenance_due(days)

    def commit(self):
        """Commit transaction."""
        self.session.commit()
