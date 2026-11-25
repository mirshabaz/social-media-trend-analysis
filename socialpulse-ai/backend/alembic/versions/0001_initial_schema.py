"""Initial PostgreSQL schema for SOCIALPULSE AI.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table(
		"users",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("email", sa.String(length=255), nullable=False),
		sa.Column("full_name", sa.String(length=255), nullable=False),
		sa.Column("role", sa.String(length=120), nullable=False),
		sa.Column("organization", sa.String(length=255), nullable=False),
		sa.Column("bio", sa.Text(), nullable=False),
		sa.Column("password_hash", sa.String(length=255), nullable=False),
		sa.Column("is_active", sa.Boolean(), nullable=False),
		sa.Column("created_at", sa.DateTime(), nullable=False),
		sa.Column("updated_at", sa.DateTime(), nullable=False),
		sa.PrimaryKeyConstraint("id", name="pk_users"),
	)
	op.create_index("ix_users_id", "users", ["id"], unique=False)
	op.create_index("ix_users_email", "users", ["email"], unique=True)

	op.create_table(
		"dataset_records",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("name", sa.String(length=255), nullable=False),
		sa.Column("original_filename", sa.String(length=255), nullable=False),
		sa.Column("stored_filename", sa.String(length=255), nullable=False),
		sa.Column("cleaned_filename", sa.String(length=255), nullable=False),
		sa.Column("row_count", sa.Integer(), nullable=False),
		sa.Column("cleaned_row_count", sa.Integer(), nullable=False),
		sa.Column("column_count", sa.Integer(), nullable=False),
		sa.Column("duplicate_count", sa.Integer(), nullable=False),
		sa.Column("missing_value_count", sa.Integer(), nullable=False),
		sa.Column("invalid_record_count", sa.Integer(), nullable=False),
		sa.Column("status", sa.String(length=50), nullable=False),
		sa.Column("column_mapping_json", sa.Text(), nullable=False),
		sa.Column("cleaning_summary_json", sa.Text(), nullable=False),
		sa.Column("is_bundled", sa.Boolean(), nullable=False),
		sa.Column("is_active", sa.Boolean(), nullable=False),
		sa.Column("owner_id", sa.Integer(), nullable=True),
		sa.Column("created_at", sa.DateTime(), nullable=False),
		sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_dataset_records_owner_id_users", ondelete="SET NULL"),
		sa.PrimaryKeyConstraint("id", name="pk_dataset_records"),
	)
	op.create_index("ix_dataset_records_id", "dataset_records", ["id"], unique=False)
	op.create_index("ix_dataset_records_owner_id", "dataset_records", ["owner_id"], unique=False)

	op.create_table(
		"dataset_activations",
		sa.Column("user_id", sa.Integer(), nullable=False),
		sa.Column("dataset_id", sa.Integer(), nullable=False),
		sa.Column("updated_at", sa.DateTime(), nullable=False),
		sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_dataset_activations_user_id_users", ondelete="CASCADE"),
		sa.ForeignKeyConstraint(["dataset_id"], ["dataset_records.id"], name="fk_dataset_activations_dataset_id_dataset_records", ondelete="CASCADE"),
		sa.PrimaryKeyConstraint("user_id", name="pk_dataset_activations"),
	)
	op.create_index("ix_dataset_activations_dataset_id", "dataset_activations", ["dataset_id"], unique=False)

	op.create_table(
		"notifications",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("user_id", sa.Integer(), nullable=True),
		sa.Column("title", sa.String(length=255), nullable=False),
		sa.Column("message", sa.Text(), nullable=False),
		sa.Column("category", sa.String(length=64), nullable=False),
		sa.Column("severity", sa.String(length=32), nullable=False),
		sa.Column("is_read", sa.Boolean(), nullable=False),
		sa.Column("meta_json", sa.Text(), nullable=False),
		sa.Column("created_at", sa.DateTime(), nullable=False),
		sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_notifications_user_id_users", ondelete="SET NULL"),
		sa.PrimaryKeyConstraint("id", name="pk_notifications"),
	)
	op.create_index("ix_notifications_id", "notifications", ["id"], unique=False)
	op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)

	op.create_table(
		"activity_logs",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("user_id", sa.Integer(), nullable=True),
		sa.Column("action", sa.String(length=120), nullable=False),
		sa.Column("target_type", sa.String(length=64), nullable=False),
		sa.Column("target_name", sa.String(length=255), nullable=False),
		sa.Column("details", sa.Text(), nullable=False),
		sa.Column("created_at", sa.DateTime(), nullable=False),
		sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_activity_logs_user_id_users", ondelete="SET NULL"),
		sa.PrimaryKeyConstraint("id", name="pk_activity_logs"),
	)
	op.create_index("ix_activity_logs_id", "activity_logs", ["id"], unique=False)
	op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"], unique=False)

	op.create_table(
		"reports",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("user_id", sa.Integer(), nullable=True),
		sa.Column("dataset_id", sa.Integer(), nullable=True),
		sa.Column("dataset_name", sa.String(length=255), nullable=False),
		sa.Column("report_type", sa.String(length=64), nullable=False),
		sa.Column("format", sa.String(length=16), nullable=False),
		sa.Column("filename", sa.String(length=255), nullable=False),
		sa.Column("title", sa.String(length=255), nullable=False),
		sa.Column("summary_json", sa.Text(), nullable=False),
		sa.Column("created_at", sa.DateTime(), nullable=False),
		sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_reports_user_id_users", ondelete="SET NULL"),
		sa.ForeignKeyConstraint(["dataset_id"], ["dataset_records.id"], name="fk_reports_dataset_id_dataset_records", ondelete="SET NULL"),
		sa.PrimaryKeyConstraint("id", name="pk_reports"),
	)
	op.create_index("ix_reports_id", "reports", ["id"], unique=False)
	op.create_index("ix_reports_user_id", "reports", ["user_id"], unique=False)
	op.create_index("ix_reports_dataset_id", "reports", ["dataset_id"], unique=False)


def downgrade() -> None:
	op.drop_table("reports")
	op.drop_table("activity_logs")
	op.drop_table("notifications")
	op.drop_table("dataset_activations")
	op.drop_table("dataset_records")
	op.drop_table("users")
