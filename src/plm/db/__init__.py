"""
PLM Database Layer

SQLAlchemy ORM models and database configuration.
"""

from .base import (
    Base,
    SessionLocal,
    engine,
    get_db,
    get_session,
    init_db,
    drop_db,
)
from .models import (
    # Parts
    PartModel,
    PartRevisionModel,
    # BOMs
    BOMModel,
    BOMItemModel,
    # Changes
    ChangeOrderModel,
    ChangeModel,
    ApprovalModel,
    ImpactAnalysisModel,
    # Requirements
    RequirementModel,
    RequirementLinkModel,
    VerificationRecordModel,
    # Suppliers
    ManufacturerModel,
    SupplierVendorModel,
    ApprovedManufacturerModel,
    ApprovedVendorModel,
    # Compliance
    RegulationModel,
    SubstanceDeclarationModel,
    ComplianceDeclarationModel,
    ComplianceCertificateModel,
    ConflictMineralDeclarationModel,
    # Costing
    PartCostModel,
    CostElementModel,
    CostVarianceModel,
    ShouldCostAnalysisModel,
    # Service Bulletins
    ServiceBulletinModel,
    BulletinComplianceModel,
    MaintenanceScheduleModel,
    UnitConfigurationModel,
    # Projects
    ProjectModel,
    MilestoneModel,
    DeliverableModel,
    # Integrations
    SyncLogEntryModel,
)

__all__ = [
    # Base
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "get_session",
    "init_db",
    "drop_db",
    # Parts
    "PartModel",
    "PartRevisionModel",
    # BOMs
    "BOMModel",
    "BOMItemModel",
    # Changes
    "ChangeOrderModel",
    "ChangeModel",
    "ApprovalModel",
    "ImpactAnalysisModel",
    # Requirements
    "RequirementModel",
    "RequirementLinkModel",
    "VerificationRecordModel",
    # Suppliers
    "ManufacturerModel",
    "SupplierVendorModel",
    "ApprovedManufacturerModel",
    "ApprovedVendorModel",
    # Compliance
    "RegulationModel",
    "SubstanceDeclarationModel",
    "ComplianceDeclarationModel",
    "ComplianceCertificateModel",
    "ConflictMineralDeclarationModel",
    # Costing
    "PartCostModel",
    "CostElementModel",
    "CostVarianceModel",
    "ShouldCostAnalysisModel",
    # Service Bulletins
    "ServiceBulletinModel",
    "BulletinComplianceModel",
    "MaintenanceScheduleModel",
    "UnitConfigurationModel",
    # Projects
    "ProjectModel",
    "MilestoneModel",
    "DeliverableModel",
    # Integrations
    "SyncLogEntryModel",
]
