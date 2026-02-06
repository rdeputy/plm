"""
Service Bulletins Repository

Database operations for service bulletins, compliance, maintenance, and units.
"""

from typing import Optional
from datetime import date

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from plm.db.repository import BaseRepository
from plm.db.models import (
    ServiceBulletinModel,
    BulletinComplianceModel,
    MaintenanceScheduleModel,
    UnitConfigurationModel,
)


class ServiceBulletinRepository(BaseRepository[ServiceBulletinModel]):
    """Repository for service bulletins."""

    def __init__(self, session: Session):
        super().__init__(session, ServiceBulletinModel)

    def find_by_number(self, bulletin_number: str) -> Optional[ServiceBulletinModel]:
        """Find bulletin by number."""
        return self.get_by(bulletin_number=bulletin_number)

    def list_by_status(self, status: str) -> list[ServiceBulletinModel]:
        """List bulletins by status."""
        return self.list(status=status, order_by="bulletin_number")

    def list_by_type(self, bulletin_type: str) -> list[ServiceBulletinModel]:
        """List bulletins by type."""
        return self.list(bulletin_type=bulletin_type, order_by="bulletin_number")

    def list_safety_related(self) -> list[ServiceBulletinModel]:
        """List safety-related bulletins."""
        return self.list(safety_issue=True, order_by="bulletin_number")

    def list_expiring_soon(self, days: int = 30) -> list[ServiceBulletinModel]:
        """List bulletins with compliance deadline approaching."""
        from datetime import timedelta

        cutoff = date.today() + timedelta(days=days)
        stmt = select(self.model_class).filter(
            ServiceBulletinModel.compliance_deadline.isnot(None),
            ServiceBulletinModel.compliance_deadline <= cutoff,
        ).order_by(ServiceBulletinModel.compliance_deadline)
        return list(self.session.execute(stmt).scalars().all())

    def search_bulletins(
        self,
        search: str,
        status: Optional[str] = None,
        bulletin_type: Optional[str] = None,
    ) -> list[ServiceBulletinModel]:
        """Search bulletins."""
        return self.search(
            search,
            ["bulletin_number", "title", "summary"],
            status=status,
            bulletin_type=bulletin_type,
        )


class BulletinComplianceRepository(BaseRepository[BulletinComplianceModel]):
    """Repository for bulletin compliance records."""

    def __init__(self, session: Session):
        super().__init__(session, BulletinComplianceModel)

    def list_for_bulletin(self, bulletin_id: str) -> list[BulletinComplianceModel]:
        """List compliance records for a bulletin."""
        return self.list(bulletin_id=bulletin_id)

    def list_for_serial(self, serial_number: str) -> list[BulletinComplianceModel]:
        """List compliance records for a serial number."""
        return self.list(serial_number=serial_number)

    def get_for_bulletin_and_serial(
        self,
        bulletin_id: str,
        serial_number: str,
    ) -> Optional[BulletinComplianceModel]:
        """Get compliance record for bulletin and serial."""
        return self.get_by(bulletin_id=bulletin_id, serial_number=serial_number)

    def list_pending(self) -> list[BulletinComplianceModel]:
        """List pending compliance records."""
        return self.list(status="pending")

    def list_overdue(self) -> list[BulletinComplianceModel]:
        """List overdue compliance records."""
        stmt = select(self.model_class).join(
            ServiceBulletinModel,
            BulletinComplianceModel.bulletin_id == ServiceBulletinModel.id,
        ).filter(
            BulletinComplianceModel.status == "pending",
            ServiceBulletinModel.compliance_deadline.isnot(None),
            ServiceBulletinModel.compliance_deadline < date.today(),
        )
        return list(self.session.execute(stmt).scalars().all())

    def record_completion(
        self,
        compliance_id: str,
        completed_by: str,
        work_order_number: Optional[str] = None,
        labor_hours: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Optional[BulletinComplianceModel]:
        """Record bulletin compliance completion."""
        return self.update(
            compliance_id,
            status="complied",
            completed_date=date.today(),
            completed_by=completed_by,
            work_order_number=work_order_number,
            labor_hours=labor_hours,
            notes=notes,
        )


class MaintenanceScheduleRepository(BaseRepository[MaintenanceScheduleModel]):
    """Repository for maintenance schedules."""

    def __init__(self, session: Session):
        super().__init__(session, MaintenanceScheduleModel)

    def find_by_code(self, schedule_code: str) -> Optional[MaintenanceScheduleModel]:
        """Find schedule by code."""
        return self.get_by(schedule_code=schedule_code)

    def list_for_part(self, part_id: str) -> list[MaintenanceScheduleModel]:
        """List schedules for a part."""
        return self.list(part_id=part_id, is_active=True)

    def list_by_system(self, system: str) -> list[MaintenanceScheduleModel]:
        """List schedules by system."""
        return self.list(system=system, is_active=True)

    def list_by_interval_type(self, interval_type: str) -> list[MaintenanceScheduleModel]:
        """List schedules by interval type."""
        return self.list(interval_type=interval_type, is_active=True)

    def search_schedules(
        self,
        search: str,
        system: Optional[str] = None,
    ) -> list[MaintenanceScheduleModel]:
        """Search maintenance schedules."""
        return self.search(
            search,
            ["schedule_code", "component", "task_description"],
            system=system,
            is_active=True,
        )


class UnitConfigurationRepository(BaseRepository[UnitConfigurationModel]):
    """Repository for unit configurations (serialized products)."""

    def __init__(self, session: Session):
        super().__init__(session, UnitConfigurationModel)

    def find_by_serial(self, serial_number: str) -> Optional[UnitConfigurationModel]:
        """Find unit by serial number."""
        return self.get_by(serial_number=serial_number)

    def list_for_part(self, part_id: str) -> list[UnitConfigurationModel]:
        """List units for a part."""
        return self.list(part_id=part_id, order_by="serial_number")

    def list_for_owner(self, owner_id: str) -> list[UnitConfigurationModel]:
        """List units for an owner."""
        return self.list(owner_id=owner_id, order_by="serial_number")

    def list_maintenance_due(self, days: int = 30) -> list[UnitConfigurationModel]:
        """List units with maintenance due soon."""
        from datetime import timedelta

        cutoff = date.today() + timedelta(days=days)
        stmt = select(self.model_class).filter(
            UnitConfigurationModel.next_maintenance_due.isnot(None),
            UnitConfigurationModel.next_maintenance_due <= cutoff,
        ).order_by(UnitConfigurationModel.next_maintenance_due)
        return list(self.session.execute(stmt).scalars().all())

    def update_hours(
        self,
        unit_id: str,
        hours: float,
        cycles: Optional[int] = None,
    ) -> Optional[UnitConfigurationModel]:
        """Update unit flight hours and cycles."""
        from datetime import datetime

        data = {"total_hours": hours, "last_updated": datetime.now()}
        if cycles is not None:
            data["total_cycles"] = cycles
        return self.update(unit_id, **data)

    def search_units(
        self,
        search: str,
        part_id: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> list[UnitConfigurationModel]:
        """Search units."""
        return self.search(
            search,
            ["serial_number", "part_number", "owner_name", "location"],
            part_id=part_id,
            owner_id=owner_id,
        )
