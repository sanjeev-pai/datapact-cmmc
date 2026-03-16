"""add datapact_tenant_id to organizations

Revision ID: a3c7e9f1b2d4
Revises: 8662414cfeb7
Create Date: 2026-03-16 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3c7e9f1b2d4'
down_revision: Union[str, None] = '8662414cfeb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('organizations', sa.Column('datapact_tenant_id', sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column('organizations', 'datapact_tenant_id')
