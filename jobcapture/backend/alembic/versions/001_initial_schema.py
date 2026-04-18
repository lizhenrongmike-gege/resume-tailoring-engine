"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("application_url", sa.String(2048), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("team", sa.String(255), nullable=True),
        sa.Column("source_site", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active_batch"),
        sa.Column("batch_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_user_status", "jobs", ["user_id", "status"])

    op.create_table(
        "application_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resume_version", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("outcome", sa.String(50), nullable=True),
    )
    op.create_index("ix_history_user", "application_history", ["user_id"])

    # Insert default user
    op.execute(
        "INSERT INTO users (id, email, created_at) VALUES "
        "('00000000-0000-0000-0000-000000000001', NULL, NOW())"
    )

def downgrade():
    op.drop_table("application_history")
    op.drop_table("jobs")
    op.drop_table("users")
