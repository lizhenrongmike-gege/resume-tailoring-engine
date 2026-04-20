"""add company_url to jobs

Revision ID: 002
Revises: 001
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("jobs", sa.Column("company_url", sa.String(2048), nullable=True))

def downgrade():
    op.drop_column("jobs", "company_url")
