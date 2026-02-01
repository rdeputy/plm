"""Initial PLM schema

Revision ID: 0001
Revises:
Create Date: 2026-01-31

Creates all PLM tables:
- parts, part_revisions
- boms, bom_items
- change_orders, changes, approvals, impact_analyses
- inventory_locations, inventory_items, inventory_transactions
- vendors, price_agreements, purchase_orders, po_items, receipts, receipt_items
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Parts
    op.create_table(
        "parts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_number", sa.String(100), nullable=False, index=True),
        sa.Column("revision", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("part_type", sa.String(20), default="component"),
        sa.Column("status", sa.String(20), default="draft", index=True),
        sa.Column("category", sa.String(100)),
        sa.Column("csi_code", sa.String(20), index=True),
        sa.Column("uniformat_code", sa.String(20)),
        sa.Column("unit_of_measure", sa.String(10), default="EA"),
        sa.Column("unit_weight", sa.Numeric(12, 4)),
        sa.Column("unit_volume", sa.Numeric(12, 4)),
        sa.Column("unit_cost", sa.Numeric(12, 4)),
        sa.Column("cost_currency", sa.String(3), default="USD"),
        sa.Column("cost_effective_date", sa.Date),
        sa.Column("manufacturer", sa.String(255)),
        sa.Column("manufacturer_pn", sa.String(100)),
        sa.Column("vendor", sa.String(255)),
        sa.Column("lead_time_days", sa.Integer),
        sa.Column("min_order_qty", sa.Numeric(12, 4)),
        sa.Column("order_multiple", sa.Numeric(12, 4)),
        sa.Column("model_file", sa.String(500)),
        sa.Column("drawing_file", sa.String(500)),
        sa.Column("spec_file", sa.String(500)),
        sa.Column("created_by", sa.String(100)),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("released_by", sa.String(100)),
        sa.Column("released_at", sa.DateTime),
        sa.Column("obsoleted_by", sa.String(100)),
        sa.Column("obsoleted_at", sa.DateTime),
        sa.Column("attributes", sa.JSON, default={}),
        sa.Column("tags", sa.JSON, default=[]),
    )

    # Part Revisions
    op.create_table(
        "part_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("revision", sa.String(20), nullable=False),
        sa.Column("previous_revision", sa.String(20)),
        sa.Column("change_order_id", sa.String(36)),  # FK added after change_orders table
        sa.Column("change_summary", sa.Text, default=""),
        sa.Column("change_details", sa.Text),
        sa.Column("status", sa.String(20), default="draft"),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_at", sa.DateTime),
        sa.Column("approval_notes", sa.Text),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("released_at", sa.DateTime),
    )

    # BOMs
    op.create_table(
        "boms",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("bom_number", sa.String(100), nullable=False, index=True),
        sa.Column("revision", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("parent_part_id", sa.String(36), index=True),
        sa.Column("parent_part_revision", sa.String(20)),
        sa.Column("bom_type", sa.String(20), default="engineering"),
        sa.Column("effectivity", sa.String(20), default="as_designed"),
        sa.Column("effective_from", sa.Date),
        sa.Column("effective_to", sa.Date),
        sa.Column("status", sa.String(20), default="draft", index=True),
        sa.Column("created_by", sa.String(100)),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("released_by", sa.String(100)),
        sa.Column("released_at", sa.DateTime),
        sa.Column("project_id", sa.String(36), index=True),
    )

    # BOM Items
    op.create_table(
        "bom_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("bom_id", sa.String(36), sa.ForeignKey("boms.id"), nullable=False, index=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("parts.id"), nullable=False, index=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("part_revision", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_of_measure", sa.String(10), default="EA"),
        sa.Column("find_number", sa.Integer, default=0),
        sa.Column("reference_designator", sa.String(100), default=""),
        sa.Column("location", sa.String(255)),
        sa.Column("notes", sa.Text),
        sa.Column("is_optional", sa.Boolean, default=False),
        sa.Column("option_code", sa.String(50)),
        sa.Column("alternate_parts", sa.JSON, default=[]),
        sa.Column("has_sub_bom", sa.Boolean, default=False),
        sa.Column("low_level_code", sa.Integer, default=0),
    )

    # Change Orders (ECOs)
    op.create_table(
        "change_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("eco_number", sa.String(50), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, default=""),
        sa.Column("reason", sa.String(30), default="customer_request"),
        sa.Column("urgency", sa.String(20), default="standard"),
        sa.Column("project_id", sa.String(36), index=True),
        sa.Column("submission_id", sa.String(36)),
        sa.Column("affected_parts", sa.JSON, default=[]),
        sa.Column("affected_boms", sa.JSON, default=[]),
        sa.Column("affected_documents", sa.JSON, default=[]),
        sa.Column("status", sa.String(20), default="draft", index=True),
        sa.Column("submitted_by", sa.String(100)),
        sa.Column("submitted_at", sa.DateTime),
        sa.Column("required_approvals", sa.JSON, default=[]),
        sa.Column("implementation_date", sa.Date),
        sa.Column("implemented_by", sa.String(100)),
        sa.Column("implementation_notes", sa.Text),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("closed_at", sa.DateTime),
    )

    # Now add FK for part_revisions.change_order_id
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("part_revisions") as batch_op:
        batch_op.create_foreign_key(
            "fk_part_revisions_change_order",
            "change_orders",
            ["change_order_id"],
            ["id"],
        )

    # Changes
    op.create_table(
        "changes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("eco_id", sa.String(36), sa.ForeignKey("change_orders.id"), nullable=False, index=True),
        sa.Column("change_type", sa.String(20), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("field_name", sa.String(100)),
        sa.Column("old_value", sa.Text),
        sa.Column("new_value", sa.Text),
        sa.Column("replaced_by_id", sa.String(36)),
        sa.Column("justification", sa.Text, default=""),
        sa.Column("notes", sa.Text),
    )

    # Approvals
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("eco_id", sa.String(36), sa.ForeignKey("change_orders.id"), nullable=False, index=True),
        sa.Column("approver_id", sa.String(36), nullable=False),
        sa.Column("approver_name", sa.String(255), nullable=False),
        sa.Column("approver_role", sa.String(100), nullable=False),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("conditions", sa.Text),
        sa.Column("comments", sa.Text),
        sa.Column("decided_at", sa.DateTime, default=sa.func.now()),
        sa.Column("signature_file", sa.String(500)),
    )

    # Impact Analyses
    op.create_table(
        "impact_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("eco_id", sa.String(36), sa.ForeignKey("change_orders.id"), nullable=False, unique=True),
        sa.Column("analyzed_at", sa.DateTime, default=sa.func.now()),
        sa.Column("analyzed_by", sa.String(100)),
        sa.Column("material_cost_delta", sa.Numeric(12, 2), default=0),
        sa.Column("labor_cost_delta", sa.Numeric(12, 2), default=0),
        sa.Column("total_cost_delta", sa.Numeric(12, 2), default=0),
        sa.Column("schedule_delta_days", sa.Integer, default=0),
        sa.Column("critical_path_affected", sa.Boolean, default=False),
        sa.Column("arc_resubmission_required", sa.Boolean, default=False),
        sa.Column("permit_revision_required", sa.Boolean, default=False),
        sa.Column("variance_required", sa.Boolean, default=False),
        sa.Column("compliance_notes", sa.Text, default=""),
        sa.Column("affected_purchase_orders", sa.JSON, default=[]),
        sa.Column("affected_work_orders", sa.JSON, default=[]),
        sa.Column("affected_inspections", sa.JSON, default=[]),
        sa.Column("risk_level", sa.String(20), default="low"),
        sa.Column("risk_notes", sa.Text, default=""),
        sa.Column("recommendations", sa.JSON, default=[]),
    )

    # Inventory Locations
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

    # Inventory Items
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

    # Inventory Transactions
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

    # Vendors
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

    # Price Agreements
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

    # Purchase Orders
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

    # PO Items
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

    # Receipts
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

    # Receipt Items
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


def downgrade() -> None:
    op.drop_table("receipt_items")
    op.drop_table("receipts")
    op.drop_table("po_items")
    op.drop_table("purchase_orders")
    op.drop_table("price_agreements")
    op.drop_table("vendors")
    op.drop_table("inventory_transactions")
    op.drop_table("inventory_items")
    op.drop_table("inventory_locations")
    op.drop_table("impact_analyses")
    op.drop_table("approvals")
    op.drop_table("changes")
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("part_revisions") as batch_op:
        batch_op.drop_constraint("fk_part_revisions_change_order", type_="foreignkey")
    op.drop_table("change_orders")
    op.drop_table("bom_items")
    op.drop_table("boms")
    op.drop_table("part_revisions")
    op.drop_table("parts")
