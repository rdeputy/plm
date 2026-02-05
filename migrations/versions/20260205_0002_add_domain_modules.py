"""Add domain module tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-05

Adds tables for:
- Requirements (requirements, requirement_links, verification_records)
- Suppliers/AML/AVL (manufacturers, supplier_vendors, approved_manufacturers, approved_vendors)
- Compliance (regulations, substance_declarations, compliance_declarations, compliance_certificates, conflict_mineral_declarations)
- Costing (part_costs, cost_elements, cost_variances, should_cost_analyses)
- Service Bulletins (service_bulletins, bulletin_compliance, maintenance_schedules, unit_configurations)
- Projects (projects, milestones, deliverables)
- Integrations (sync_log_entries)
- Documents (documents, document_versions, document_links)
- IPC (supersessions, effectivity_ranges, ipc_figures, figure_hotspots)

Removes deprecated tables:
- inventory_locations, inventory_items, inventory_transactions
- vendors, price_agreements, purchase_orders, po_items, receipts, receipt_items
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Drop deprecated tables (inventory, procurement)
    # =========================================================================
    op.drop_table("receipt_items")
    op.drop_table("receipts")
    op.drop_table("po_items")
    op.drop_table("purchase_orders")
    op.drop_table("price_agreements")
    op.drop_table("vendors")
    op.drop_table("inventory_transactions")
    op.drop_table("inventory_items")
    op.drop_table("inventory_locations")

    # =========================================================================
    # Document Tables
    # =========================================================================
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_number", sa.String(100), nullable=False, index=True),
        sa.Column("revision", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("document_type", sa.String(30), default="other"),
        sa.Column("status", sa.String(20), default="draft", index=True),
        sa.Column("storage_path", sa.String(1000)),
        sa.Column("file_name", sa.String(255)),
        sa.Column("file_size", sa.Integer),
        sa.Column("file_hash", sa.String(64)),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("category", sa.String(100)),
        sa.Column("discipline", sa.String(100)),
        sa.Column("project_id", sa.String(36), index=True),
        sa.Column("checkout_status", sa.String(20), default="available"),
        sa.Column("checked_out_by", sa.String(100)),
        sa.Column("checked_out_at", sa.DateTime),
        sa.Column("checkout_notes", sa.Text),
        sa.Column("created_by", sa.String(100)),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("released_by", sa.String(100)),
        sa.Column("released_at", sa.DateTime),
        sa.Column("superseded_by", sa.String(36)),
        sa.Column("attributes", sa.JSON, default={}),
        sa.Column("tags", sa.JSON, default=[]),
    )

    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("revision", sa.String(20), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("change_summary", sa.Text),
        sa.Column("change_order_id", sa.String(36), sa.ForeignKey("change_orders.id")),
        sa.Column("created_by", sa.String(100)),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("attributes", sa.JSON, default={}),
    )

    op.create_table(
        "document_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), index=True),
        sa.Column("bom_id", sa.String(36), sa.ForeignKey("boms.id"), index=True),
        sa.Column("eco_id", sa.String(36), sa.ForeignKey("change_orders.id"), index=True),
        sa.Column("project_id", sa.String(36), index=True),
        sa.Column("link_type", sa.String(50), default="reference"),
        sa.Column("description", sa.Text),
        sa.Column("created_by", sa.String(100)),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    # =========================================================================
    # IPC Tables
    # =========================================================================
    op.create_table(
        "supersessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("superseded_part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("superseded_part_number", sa.String(100), nullable=False),
        sa.Column("superseding_part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("superseding_part_number", sa.String(100), nullable=False),
        sa.Column("supersession_type", sa.String(50), default="replacement"),
        sa.Column("is_interchangeable", sa.Boolean, default=True),
        sa.Column("quantity_ratio", sa.Numeric(8, 4), default=1),
        sa.Column("effective_date", sa.Date),
        sa.Column("effective_serial", sa.String(50)),
        sa.Column("reason", sa.Text, default=""),
        sa.Column("change_order_id", sa.String(36), sa.ForeignKey("change_orders.id")),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("created_by", sa.String(100)),
    )

    op.create_table(
        "effectivity_ranges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("effectivity_type", sa.String(20), nullable=False),
        sa.Column("serial_from", sa.String(50)),
        sa.Column("serial_to", sa.String(50)),
        sa.Column("date_from", sa.Date),
        sa.Column("date_to", sa.Date),
        sa.Column("model_codes", sa.JSON, default=[]),
        sa.Column("config_codes", sa.JSON, default=[]),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), index=True),
        sa.Column("bom_item_id", sa.String(36), sa.ForeignKey("bom_items.id"), index=True),
        sa.Column("display_text", sa.String(255), default="All"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    op.create_table(
        "ipc_figures",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("bom_id", sa.String(36), sa.ForeignKey("boms.id"), nullable=False, index=True),
        sa.Column("figure_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("sheet_number", sa.Integer, default=1),
        sa.Column("total_sheets", sa.Integer, default=1),
        sa.Column("view_type", sa.String(50), default="exploded"),
        sa.Column("scale", sa.String(20)),
        sa.Column("is_current", sa.Boolean, default=True),
        sa.Column("superseded_by", sa.String(36)),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "figure_hotspots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("figure_id", sa.String(36), sa.ForeignKey("ipc_figures.id"), nullable=False, index=True),
        sa.Column("bom_item_id", sa.String(36), sa.ForeignKey("bom_items.id"), nullable=False, index=True),
        sa.Column("index_number", sa.Integer, nullable=False),
        sa.Column("find_number", sa.Integer, nullable=False),
        sa.Column("x", sa.Numeric(6, 4), nullable=False),
        sa.Column("y", sa.Numeric(6, 4), nullable=False),
        sa.Column("target_x", sa.Numeric(6, 4)),
        sa.Column("target_y", sa.Numeric(6, 4)),
        sa.Column("shape", sa.String(20), default="circle"),
        sa.Column("size", sa.Numeric(4, 3), default=0.02),
        sa.Column("part_number", sa.String(100)),
        sa.Column("part_name", sa.String(255)),
        sa.Column("quantity", sa.Numeric(12, 4)),
        sa.Column("page_number", sa.Integer, default=1),
        sa.Column("notes", sa.Text),
    )

    # =========================================================================
    # Requirements Tables
    # =========================================================================
    op.create_table(
        "requirements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("requirement_number", sa.String(50), nullable=False, unique=True),
        sa.Column("requirement_type", sa.String(20), default="functional"),
        sa.Column("status", sa.String(20), default="draft", index=True),
        sa.Column("priority", sa.String(20), default="must_have"),
        sa.Column("title", sa.String(255), default=""),
        sa.Column("description", sa.Text, default=""),
        sa.Column("rationale", sa.Text, default=""),
        sa.Column("acceptance_criteria", sa.Text, default=""),
        sa.Column("source", sa.String(255), default=""),
        sa.Column("source_document", sa.String(255)),
        sa.Column("source_section", sa.String(100)),
        sa.Column("customer_id", sa.String(36)),
        sa.Column("verification_method", sa.String(20), default="test"),
        sa.Column("verification_procedure", sa.String(255)),
        sa.Column("parent_id", sa.String(36), index=True),
        sa.Column("derived_from", sa.JSON, default=[]),
        sa.Column("project_id", sa.String(36), index=True),
        sa.Column("phase", sa.String(50)),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("created_by", sa.String(100)),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_date", sa.DateTime),
        sa.Column("tags", sa.JSON, default=[]),
        sa.Column("attachments", sa.JSON, default=[]),
    )

    op.create_table(
        "requirement_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("requirement_id", sa.String(36), sa.ForeignKey("requirements.id"), nullable=False, index=True),
        sa.Column("link_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False, index=True),
        sa.Column("target_number", sa.String(100)),
        sa.Column("target_revision", sa.String(20)),
        sa.Column("relationship", sa.String(50), default="implements"),
        sa.Column("coverage", sa.String(20), default="full"),
        sa.Column("coverage_notes", sa.Text, default=""),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("created_by", sa.String(100)),
    )

    op.create_table(
        "verification_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("verification_number", sa.String(50), nullable=False, unique=True),
        sa.Column("requirement_id", sa.String(36), sa.ForeignKey("requirements.id"), nullable=False, index=True),
        sa.Column("requirement_number", sa.String(50), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("procedure_id", sa.String(36)),
        sa.Column("procedure_number", sa.String(100)),
        sa.Column("status", sa.String(20), default="not_started", index=True),
        sa.Column("result_summary", sa.Text, default=""),
        sa.Column("pass_fail", sa.Boolean),
        sa.Column("actual_value", sa.String(255)),
        sa.Column("expected_value", sa.String(255)),
        sa.Column("deviation", sa.Text),
        sa.Column("evidence_documents", sa.JSON, default=[]),
        sa.Column("test_report_id", sa.String(36)),
        sa.Column("verified_by", sa.String(100)),
        sa.Column("verified_date", sa.DateTime),
        sa.Column("witness", sa.String(100)),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_date", sa.DateTime),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    # =========================================================================
    # Supplier/AML/AVL Tables
    # =========================================================================
    op.create_table(
        "manufacturers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("manufacturer_code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text, default=""),
        sa.Column("country", sa.String(100), default=""),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("contact_phone", sa.String(50)),
        sa.Column("website", sa.String(500)),
        sa.Column("status", sa.String(20), default="pending", index=True),
        sa.Column("certifications", sa.JSON, default=[]),
        sa.Column("cage_code", sa.String(20)),
        sa.Column("duns_number", sa.String(20)),
        sa.Column("capabilities", sa.JSON, default=[]),
        sa.Column("specialties", sa.JSON, default=[]),
        sa.Column("last_audit_date", sa.Date),
        sa.Column("next_audit_date", sa.Date),
        sa.Column("audit_score", sa.Integer),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("approved_date", sa.Date),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("notes", sa.Text, default=""),
    )

    op.create_table(
        "supplier_vendors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("vendor_code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text, default=""),
        sa.Column("country", sa.String(100), default=""),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("contact_phone", sa.String(50)),
        sa.Column("website", sa.String(500)),
        sa.Column("status", sa.String(20), default="pending", index=True),
        sa.Column("tier", sa.String(20), default="approved"),
        sa.Column("payment_terms", sa.String(50), default=""),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("minimum_order", sa.Numeric(12, 2), default=0),
        sa.Column("on_time_delivery_rate", sa.Numeric(5, 2)),
        sa.Column("quality_rating", sa.Numeric(5, 2)),
        sa.Column("lead_time_days", sa.Integer),
        sa.Column("certifications", sa.JSON, default=[]),
        sa.Column("duns_number", sa.String(20)),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("approved_date", sa.Date),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("notes", sa.Text, default=""),
    )

    op.create_table(
        "approved_manufacturers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("manufacturer_id", sa.String(36), sa.ForeignKey("manufacturers.id"), nullable=False, index=True),
        sa.Column("manufacturer_name", sa.String(255), nullable=False),
        sa.Column("manufacturer_part_number", sa.String(100), default=""),
        sa.Column("status", sa.String(20), default="pending", index=True),
        sa.Column("qualification_status", sa.String(20), default="not_started"),
        sa.Column("preference_rank", sa.Integer, default=1),
        sa.Column("is_primary", sa.Boolean, default=False),
        sa.Column("qualification_date", sa.Date),
        sa.Column("qualification_report", sa.String(255)),
        sa.Column("qualification_expires", sa.Date),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("created_by", sa.String(100)),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_date", sa.Date),
        sa.Column("notes", sa.Text, default=""),
    )

    op.create_table(
        "approved_vendors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("vendor_id", sa.String(36), sa.ForeignKey("supplier_vendors.id"), nullable=False, index=True),
        sa.Column("vendor_name", sa.String(255), nullable=False),
        sa.Column("vendor_part_number", sa.String(100), default=""),
        sa.Column("status", sa.String(20), default="pending", index=True),
        sa.Column("preference_rank", sa.Integer, default=1),
        sa.Column("is_primary", sa.Boolean, default=False),
        sa.Column("unit_price", sa.Numeric(12, 4), default=0),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("minimum_order_qty", sa.Numeric(12, 4), default=1),
        sa.Column("lead_time_days", sa.Integer, default=0),
        sa.Column("price_valid_until", sa.Date),
        sa.Column("on_time_delivery_rate", sa.Numeric(5, 2)),
        sa.Column("quality_reject_rate", sa.Numeric(5, 2)),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("created_by", sa.String(100)),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_date", sa.Date),
        sa.Column("notes", sa.Text, default=""),
    )

    # =========================================================================
    # Compliance Tables
    # =========================================================================
    op.create_table(
        "regulations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("regulation_code", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("regulation_type", sa.String(30), nullable=False, index=True),
        sa.Column("description", sa.Text, default=""),
        sa.Column("authority", sa.String(255), default=""),
        sa.Column("effective_date", sa.Date),
        sa.Column("version", sa.String(50), default=""),
        sa.Column("regions", sa.JSON, default=[]),
        sa.Column("product_categories", sa.JSON, default=[]),
        sa.Column("exemptions", sa.JSON, default=[]),
        sa.Column("reference_url", sa.String(500)),
        sa.Column("reference_document", sa.String(255)),
        sa.Column("is_active", sa.Boolean, default=True, index=True),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    op.create_table(
        "substance_declarations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("substance_name", sa.String(255), nullable=False),
        sa.Column("cas_number", sa.String(50)),
        sa.Column("category", sa.String(20), default="other"),
        sa.Column("concentration_ppm", sa.Numeric(12, 4)),
        sa.Column("concentration_percent", sa.Numeric(8, 4)),
        sa.Column("threshold_ppm", sa.Numeric(12, 4)),
        sa.Column("above_threshold", sa.Boolean, default=False),
        sa.Column("component", sa.String(255), default=""),
        sa.Column("homogeneous_material", sa.String(255), default=""),
        sa.Column("source", sa.String(100), default=""),
        sa.Column("source_document", sa.String(255)),
        sa.Column("declaration_date", sa.Date),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    op.create_table(
        "compliance_declarations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("regulation_id", sa.String(36), sa.ForeignKey("regulations.id"), nullable=False, index=True),
        sa.Column("regulation_code", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), default="unknown", index=True),
        sa.Column("exemption_code", sa.String(50)),
        sa.Column("exemption_expiry", sa.Date),
        sa.Column("notes", sa.Text, default=""),
        sa.Column("certificate_id", sa.String(36)),
        sa.Column("test_report_id", sa.String(36)),
        sa.Column("supplier_declaration", sa.String(255)),
        sa.Column("declared_by", sa.String(100)),
        sa.Column("declared_date", sa.Date),
        sa.Column("verified_by", sa.String(100)),
        sa.Column("verified_date", sa.Date),
        sa.Column("expires", sa.Date),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    op.create_table(
        "compliance_certificates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("certificate_number", sa.String(100), nullable=False, unique=True),
        sa.Column("regulation_id", sa.String(36), sa.ForeignKey("regulations.id"), nullable=False, index=True),
        sa.Column("regulation_code", sa.String(100), nullable=False),
        sa.Column("part_ids", sa.JSON, default=[]),
        sa.Column("product_family", sa.String(255)),
        sa.Column("status", sa.String(20), default="draft", index=True),
        sa.Column("issue_date", sa.Date),
        sa.Column("expiry_date", sa.Date),
        sa.Column("issued_by", sa.String(255), default=""),
        sa.Column("certificate_url", sa.String(500)),
        sa.Column("attachments", sa.JSON, default=[]),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    op.create_table(
        "conflict_mineral_declarations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("contains_tin", sa.Boolean, default=False),
        sa.Column("contains_tantalum", sa.Boolean, default=False),
        sa.Column("contains_tungsten", sa.Boolean, default=False),
        sa.Column("contains_gold", sa.Boolean, default=False),
        sa.Column("conflict_free", sa.Boolean),
        sa.Column("smelter_list", sa.JSON, default=[]),
        sa.Column("countries_of_origin", sa.JSON, default=[]),
        sa.Column("cmrt_version", sa.String(50)),
        sa.Column("cmrt_document", sa.String(255)),
        sa.Column("declaration_date", sa.Date),
        sa.Column("declared_by", sa.String(100)),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    # =========================================================================
    # Costing Tables
    # =========================================================================
    op.create_table(
        "part_costs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("part_revision", sa.String(20), default=""),
        sa.Column("status", sa.String(20), default="draft", index=True),
        sa.Column("material_cost", sa.Numeric(12, 4), default=0),
        sa.Column("labor_cost", sa.Numeric(12, 4), default=0),
        sa.Column("overhead_cost", sa.Numeric(12, 4), default=0),
        sa.Column("total_cost", sa.Numeric(12, 4), default=0),
        sa.Column("target_cost", sa.Numeric(12, 4)),
        sa.Column("should_cost", sa.Numeric(12, 4)),
        sa.Column("selling_price", sa.Numeric(12, 4)),
        sa.Column("margin_percent", sa.Numeric(8, 4)),
        sa.Column("lot_size", sa.Integer, default=1),
        sa.Column("annual_volume", sa.Integer),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("exchange_rate", sa.Numeric(12, 6), default=1),
        sa.Column("effective_date", sa.Date),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("created_by", sa.String(100)),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_date", sa.DateTime),
        sa.Column("notes", sa.Text, default=""),
    )

    op.create_table(
        "cost_elements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_cost_id", sa.String(36), sa.ForeignKey("part_costs.id"), nullable=False, index=True),
        sa.Column("cost_type", sa.String(20), nullable=False),
        sa.Column("description", sa.String(255), default=""),
        sa.Column("unit_cost", sa.Numeric(12, 4), default=0),
        sa.Column("quantity", sa.Numeric(12, 4), default=1),
        sa.Column("extended_cost", sa.Numeric(12, 4), default=0),
        sa.Column("rate", sa.Numeric(12, 4)),
        sa.Column("unit_of_measure", sa.String(10), default="EA"),
        sa.Column("basis", sa.String(255), default=""),
        sa.Column("source", sa.String(100), default=""),
        sa.Column("vendor_id", sa.String(36)),
        sa.Column("quote_number", sa.String(50)),
        sa.Column("quote_date", sa.Date),
        sa.Column("target_cost", sa.Numeric(12, 4)),
        sa.Column("variance", sa.Numeric(12, 4)),
        sa.Column("variance_percent", sa.Numeric(8, 4)),
    )

    op.create_table(
        "cost_variances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("period", sa.String(20), nullable=False, index=True),
        sa.Column("standard_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("actual_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("variance", sa.Numeric(12, 4), default=0),
        sa.Column("variance_percent", sa.Numeric(8, 4), default=0),
        sa.Column("variance_type", sa.String(30), default="material_price"),
        sa.Column("favorable", sa.Boolean, default=True),
        sa.Column("root_cause", sa.Text, default=""),
        sa.Column("corrective_action", sa.Text, default=""),
        sa.Column("quantity", sa.Numeric(12, 4), default=1),
        sa.Column("total_variance", sa.Numeric(12, 4), default=0),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    op.create_table(
        "should_cost_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("analysis_date", sa.Date, default=sa.func.current_date()),
        sa.Column("analyst", sa.String(100), default=""),
        sa.Column("methodology", sa.String(50), default=""),
        sa.Column("should_cost", sa.Numeric(12, 4), default=0),
        sa.Column("raw_material", sa.Numeric(12, 4), default=0),
        sa.Column("material_processing", sa.Numeric(12, 4), default=0),
        sa.Column("conversion_cost", sa.Numeric(12, 4), default=0),
        sa.Column("profit_margin", sa.Numeric(12, 4), default=0),
        sa.Column("logistics", sa.Numeric(12, 4), default=0),
        sa.Column("current_price", sa.Numeric(12, 4)),
        sa.Column("savings_opportunity", sa.Numeric(12, 4)),
        sa.Column("savings_percent", sa.Numeric(8, 4)),
        sa.Column("assumptions", sa.JSON, default=[]),
        sa.Column("data_sources", sa.JSON, default=[]),
        sa.Column("notes", sa.Text, default=""),
    )

    # =========================================================================
    # Service Bulletin Tables
    # =========================================================================
    op.create_table(
        "service_bulletins",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("bulletin_number", sa.String(50), nullable=False, unique=True),
        sa.Column("bulletin_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), default="draft", index=True),
        sa.Column("title", sa.String(255), default=""),
        sa.Column("summary", sa.Text, default=""),
        sa.Column("description", sa.Text, default=""),
        sa.Column("reason", sa.Text, default=""),
        sa.Column("safety_issue", sa.Boolean, default=False),
        sa.Column("action_required", sa.Text, default=""),
        sa.Column("action_procedure", sa.Text, default=""),
        sa.Column("estimated_time", sa.String(50)),
        sa.Column("special_tools", sa.JSON, default=[]),
        sa.Column("required_parts", sa.JSON, default=[]),
        sa.Column("affected_parts", sa.JSON, default=[]),
        sa.Column("affected_part_numbers", sa.JSON, default=[]),
        sa.Column("serial_range_start", sa.String(50)),
        sa.Column("serial_range_end", sa.String(50)),
        sa.Column("effectivity_start", sa.Date),
        sa.Column("effectivity_end", sa.Date),
        sa.Column("affected_configurations", sa.JSON, default=[]),
        sa.Column("compliance_deadline", sa.Date),
        sa.Column("flight_hours_limit", sa.Integer),
        sa.Column("cycles_limit", sa.Integer),
        sa.Column("related_eco_id", sa.String(36)),
        sa.Column("related_ncr_ids", sa.JSON, default=[]),
        sa.Column("supersedes", sa.String(50)),
        sa.Column("superseded_by", sa.String(50)),
        sa.Column("attachments", sa.JSON, default=[]),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("created_by", sa.String(100)),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_date", sa.DateTime),
        sa.Column("effective_date", sa.Date),
        sa.Column("expiry_date", sa.Date),
    )

    op.create_table(
        "bulletin_compliance",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("bulletin_id", sa.String(36), sa.ForeignKey("service_bulletins.id"), nullable=False, index=True),
        sa.Column("bulletin_number", sa.String(50), nullable=False),
        sa.Column("serial_number", sa.String(100), nullable=False, index=True),
        sa.Column("part_id", sa.String(36)),
        sa.Column("part_number", sa.String(100)),
        sa.Column("status", sa.String(20), default="pending", index=True),
        sa.Column("completed_date", sa.Date),
        sa.Column("completed_by", sa.String(100)),
        sa.Column("work_order_number", sa.String(50)),
        sa.Column("labor_hours", sa.Numeric(8, 2)),
        sa.Column("parts_used", sa.JSON, default=[]),
        sa.Column("waived", sa.Boolean, default=False),
        sa.Column("waiver_reason", sa.Text),
        sa.Column("waiver_approved_by", sa.String(100)),
        sa.Column("waiver_expiry", sa.Date),
        sa.Column("notes", sa.Text, default=""),
        sa.Column("attachments", sa.JSON, default=[]),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    op.create_table(
        "maintenance_schedules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("schedule_code", sa.String(50), nullable=False, index=True),
        sa.Column("part_id", sa.String(36)),
        sa.Column("part_number", sa.String(100)),
        sa.Column("system", sa.String(100), default=""),
        sa.Column("component", sa.String(255), default=""),
        sa.Column("interval_type", sa.String(20), default="calendar"),
        sa.Column("interval_value", sa.Integer, default=0),
        sa.Column("interval_unit", sa.String(20), default=""),
        sa.Column("task_description", sa.Text, default=""),
        sa.Column("procedure_reference", sa.String(255)),
        sa.Column("estimated_time", sa.String(50)),
        sa.Column("required_parts", sa.JSON, default=[]),
        sa.Column("consumables", sa.JSON, default=[]),
        sa.Column("is_active", sa.Boolean, default=True, index=True),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    op.create_table(
        "unit_configurations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("serial_number", sa.String(100), nullable=False, unique=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("current_revision", sa.String(20), default=""),
        sa.Column("configuration_id", sa.String(36)),
        sa.Column("build_date", sa.Date),
        sa.Column("delivery_date", sa.Date),
        sa.Column("total_hours", sa.Numeric(12, 2), default=0),
        sa.Column("total_cycles", sa.Integer, default=0),
        sa.Column("last_updated", sa.DateTime),
        sa.Column("owner_id", sa.String(36)),
        sa.Column("owner_name", sa.String(255), default=""),
        sa.Column("location", sa.String(255), default=""),
        sa.Column("applied_bulletins", sa.JSON, default=[]),
        sa.Column("pending_bulletins", sa.JSON, default=[]),
        sa.Column("last_maintenance_date", sa.Date),
        sa.Column("next_maintenance_due", sa.Date),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    # =========================================================================
    # Project Tables
    # =========================================================================
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_number", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), default="proposed", index=True),
        sa.Column("phase", sa.String(20), default="concept"),
        sa.Column("project_type", sa.String(50), default=""),
        sa.Column("description", sa.Text, default=""),
        sa.Column("objectives", sa.Text, default=""),
        sa.Column("scope", sa.Text, default=""),
        sa.Column("program_id", sa.String(36)),
        sa.Column("parent_project_id", sa.String(36)),
        sa.Column("customer_id", sa.String(36)),
        sa.Column("customer_name", sa.String(255), default=""),
        sa.Column("contract_number", sa.String(100)),
        sa.Column("start_date", sa.Date),
        sa.Column("target_end_date", sa.Date),
        sa.Column("actual_end_date", sa.Date),
        sa.Column("budget", sa.Numeric(14, 2), default=0),
        sa.Column("actual_cost", sa.Numeric(14, 2), default=0),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("project_manager_id", sa.String(36)),
        sa.Column("project_manager_name", sa.String(255), default=""),
        sa.Column("team_members", sa.JSON, default=[]),
        sa.Column("part_ids", sa.JSON, default=[]),
        sa.Column("bom_ids", sa.JSON, default=[]),
        sa.Column("document_ids", sa.JSON, default=[]),
        sa.Column("eco_ids", sa.JSON, default=[]),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("created_by", sa.String(100)),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_date", sa.DateTime),
        sa.Column("notes", sa.Text, default=""),
        sa.Column("tags", sa.JSON, default=[]),
    )

    op.create_table(
        "milestones",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("milestone_number", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), default="not_started", index=True),
        sa.Column("phase", sa.String(20)),
        sa.Column("description", sa.Text, default=""),
        sa.Column("success_criteria", sa.Text, default=""),
        sa.Column("planned_date", sa.Date),
        sa.Column("forecast_date", sa.Date),
        sa.Column("actual_date", sa.Date),
        sa.Column("sequence", sa.Integer, default=0),
        sa.Column("predecessor_ids", sa.JSON, default=[]),
        sa.Column("review_required", sa.Boolean, default=False),
        sa.Column("review_type", sa.String(50), default=""),
        sa.Column("reviewers", sa.JSON, default=[]),
        sa.Column("review_notes", sa.Text, default=""),
        sa.Column("deliverable_ids", sa.JSON, default=[]),
        sa.Column("completed_by", sa.String(100)),
        sa.Column("completion_notes", sa.Text, default=""),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    op.create_table(
        "deliverables",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("milestone_id", sa.String(36), sa.ForeignKey("milestones.id"), index=True),
        sa.Column("deliverable_number", sa.String(50), default=""),
        sa.Column("name", sa.String(255), default=""),
        sa.Column("deliverable_type", sa.String(20), default="document"),
        sa.Column("description", sa.Text, default=""),
        sa.Column("acceptance_criteria", sa.Text, default=""),
        sa.Column("status", sa.String(20), default="not_started", index=True),
        sa.Column("percent_complete", sa.Integer, default=0),
        sa.Column("due_date", sa.Date),
        sa.Column("submitted_date", sa.Date),
        sa.Column("accepted_date", sa.Date),
        sa.Column("assigned_to", sa.String(36)),
        sa.Column("assigned_name", sa.String(255), default=""),
        sa.Column("part_id", sa.String(36)),
        sa.Column("document_id", sa.String(36)),
        sa.Column("bom_id", sa.String(36)),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approval_notes", sa.Text, default=""),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )

    # =========================================================================
    # Integration Tables
    # =========================================================================
    op.create_table(
        "sync_log_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("timestamp", sa.DateTime, nullable=False, index=True),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False, index=True),
        sa.Column("entity_number", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("action", sa.String(50), default=""),
        sa.Column("message", sa.Text, default=""),
        sa.Column("error", sa.Text),
        sa.Column("request_payload", sa.JSON),
        sa.Column("response_payload", sa.JSON),
        sa.Column("duration_ms", sa.Integer),
    )


def downgrade() -> None:
    # Drop new tables in reverse order
    op.drop_table("sync_log_entries")
    op.drop_table("deliverables")
    op.drop_table("milestones")
    op.drop_table("projects")
    op.drop_table("unit_configurations")
    op.drop_table("maintenance_schedules")
    op.drop_table("bulletin_compliance")
    op.drop_table("service_bulletins")
    op.drop_table("should_cost_analyses")
    op.drop_table("cost_variances")
    op.drop_table("cost_elements")
    op.drop_table("part_costs")
    op.drop_table("conflict_mineral_declarations")
    op.drop_table("compliance_certificates")
    op.drop_table("compliance_declarations")
    op.drop_table("substance_declarations")
    op.drop_table("regulations")
    op.drop_table("approved_vendors")
    op.drop_table("approved_manufacturers")
    op.drop_table("supplier_vendors")
    op.drop_table("manufacturers")
    op.drop_table("verification_records")
    op.drop_table("requirement_links")
    op.drop_table("requirements")
    op.drop_table("figure_hotspots")
    op.drop_table("ipc_figures")
    op.drop_table("effectivity_ranges")
    op.drop_table("supersessions")
    op.drop_table("document_links")
    op.drop_table("document_versions")
    op.drop_table("documents")

    # Recreate deprecated tables for downgrade
    # (This is abbreviated - full recreation would match initial schema)
    op.create_table(
        "inventory_locations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location_type", sa.String(50), nullable=False),
        sa.Column("address", sa.Text),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("project_id", sa.String(36), index=True),
        sa.Column("vendor_id", sa.String(36), index=True),
    )

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("inventory_locations.id"), nullable=False, index=True),
        sa.Column("on_hand", sa.Numeric(12, 4), default=0),
        sa.Column("allocated", sa.Numeric(12, 4), default=0),
        sa.Column("on_order", sa.Numeric(12, 4), default=0),
        sa.Column("unit_cost", sa.Numeric(12, 4), default=0),
        sa.Column("total_value", sa.Numeric(12, 4), default=0),
        sa.Column("last_count_date", sa.DateTime),
        sa.Column("last_receipt_date", sa.DateTime),
        sa.Column("last_issue_date", sa.DateTime),
        sa.Column("reorder_point", sa.Numeric(12, 4)),
        sa.Column("reorder_qty", sa.Numeric(12, 4)),
    )

    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("part_id", sa.String(36), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_of_measure", sa.String(10), nullable=False),
        sa.Column("location_id", sa.String(36), nullable=False, index=True),
        sa.Column("from_location_id", sa.String(36)),
        sa.Column("to_location_id", sa.String(36)),
        sa.Column("po_id", sa.String(36), index=True),
        sa.Column("project_id", sa.String(36), index=True),
        sa.Column("work_order_id", sa.String(36)),
        sa.Column("unit_cost", sa.Numeric(12, 4), default=0),
        sa.Column("total_cost", sa.Numeric(12, 4), default=0),
        sa.Column("transaction_date", sa.DateTime, default=sa.func.now(), index=True),
        sa.Column("created_by", sa.String(100), default=""),
        sa.Column("notes", sa.Text),
        sa.Column("lot_number", sa.String(100)),
        sa.Column("serial_number", sa.String(100)),
    )

    op.create_table(
        "vendors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("vendor_code", sa.String(20), nullable=False, unique=True),
        sa.Column("address", sa.Text),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(50)),
        sa.Column("postal_code", sa.String(20)),
        sa.Column("country", sa.String(50), default="USA"),
        sa.Column("phone", sa.String(50)),
        sa.Column("email", sa.String(255)),
        sa.Column("website", sa.String(500)),
        sa.Column("contacts", sa.JSON, default=[]),
        sa.Column("payment_terms", sa.String(50), default="Net 30"),
        sa.Column("freight_terms", sa.String(50), default="FOB Origin"),
        sa.Column("minimum_order", sa.Numeric(12, 2), default=0),
        sa.Column("categories", sa.JSON, default=[]),
        sa.Column("on_time_rate", sa.Numeric(5, 2), default=0),
        sa.Column("quality_rate", sa.Numeric(5, 2), default=0),
        sa.Column("avg_lead_time_days", sa.Integer, default=0),
        sa.Column("is_approved", sa.Boolean, default=True),
        sa.Column("insurance_expiry", sa.Date),
        sa.Column("w9_on_file", sa.Boolean, default=False),
        sa.Column("certifications", sa.JSON, default=[]),
        sa.Column("is_active", sa.Boolean, default=True, index=True),
        sa.Column("notes", sa.Text),
    )

    op.create_table(
        "price_agreements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("vendor_id", sa.String(36), sa.ForeignKey("vendors.id"), nullable=False, index=True),
        sa.Column("part_id", sa.String(36), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("effective_date", sa.Date, default=sa.func.current_date()),
        sa.Column("expiration_date", sa.Date),
        sa.Column("min_quantity", sa.Numeric(12, 4), default=1),
        sa.Column("price_breaks", sa.JSON, default={}),
        sa.Column("contract_number", sa.String(50)),
        sa.Column("notes", sa.Text),
    )

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("po_number", sa.String(50), nullable=False, unique=True),
        sa.Column("vendor_id", sa.String(36), sa.ForeignKey("vendors.id"), nullable=False, index=True),
        sa.Column("vendor_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), default="draft", index=True),
        sa.Column("subtotal", sa.Numeric(12, 2), default=0),
        sa.Column("tax", sa.Numeric(12, 2), default=0),
        sa.Column("shipping", sa.Numeric(12, 2), default=0),
        sa.Column("total", sa.Numeric(12, 2), default=0),
        sa.Column("order_date", sa.Date),
        sa.Column("required_date", sa.Date),
        sa.Column("promised_date", sa.Date),
        sa.Column("ship_to_location_id", sa.String(36)),
        sa.Column("ship_to_address", sa.Text),
        sa.Column("freight_terms", sa.String(50), default="FOB Origin"),
        sa.Column("payment_terms", sa.String(50), default="Net 30"),
        sa.Column("project_id", sa.String(36), index=True),
        sa.Column("requisition_id", sa.String(36)),
        sa.Column("notes", sa.Text),
        sa.Column("created_by", sa.String(100), default=""),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "po_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("po_id", sa.String(36), sa.ForeignKey("purchase_orders.id"), nullable=False, index=True),
        sa.Column("line_number", sa.Integer, nullable=False),
        sa.Column("part_id", sa.String(36), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_of_measure", sa.String(10), nullable=False),
        sa.Column("received_quantity", sa.Numeric(12, 4), default=0),
        sa.Column("unit_price", sa.Numeric(12, 4), default=0),
        sa.Column("extended_price", sa.Numeric(12, 2), default=0),
        sa.Column("required_date", sa.Date),
        sa.Column("promised_date", sa.Date),
        sa.Column("project_id", sa.String(36)),
        sa.Column("planned_order_id", sa.String(36)),
        sa.Column("is_closed", sa.Boolean, default=False),
    )

    op.create_table(
        "receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("receipt_number", sa.String(50), nullable=False, unique=True),
        sa.Column("po_id", sa.String(36), sa.ForeignKey("purchase_orders.id"), nullable=False, index=True),
        sa.Column("po_number", sa.String(50), nullable=False),
        sa.Column("vendor_id", sa.String(36), nullable=False, index=True),
        sa.Column("receipt_date", sa.Date, default=sa.func.current_date()),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("packing_slip", sa.String(100)),
        sa.Column("carrier", sa.String(100)),
        sa.Column("tracking_number", sa.String(100)),
        sa.Column("received_by", sa.String(100), default=""),
        sa.Column("location_id", sa.String(36)),
        sa.Column("is_complete", sa.Boolean, default=False),
        sa.Column("notes", sa.Text),
    )

    op.create_table(
        "receipt_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("receipt_id", sa.String(36), sa.ForeignKey("receipts.id"), nullable=False, index=True),
        sa.Column("po_item_id", sa.String(36), nullable=False),
        sa.Column("part_id", sa.String(36), nullable=False),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("quantity_received", sa.Numeric(12, 4), nullable=False),
        sa.Column("quantity_accepted", sa.Numeric(12, 4), default=0),
        sa.Column("quantity_rejected", sa.Numeric(12, 4), default=0),
        sa.Column("unit_of_measure", sa.String(10), default="EA"),
        sa.Column("lot_number", sa.String(100)),
        sa.Column("serial_numbers", sa.JSON, default=[]),
        sa.Column("location_id", sa.String(36)),
        sa.Column("inspection_required", sa.Boolean, default=False),
        sa.Column("inspection_status", sa.String(50)),
        sa.Column("inspection_notes", sa.Text),
    )
