"""add SAVED to applicationstatus enum

Revision ID: a1b2c3d4e5f6
Revises: 84c9df68bbb4
Create Date: 2026-04-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '84c9df68bbb4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE job_applications MODIFY COLUMN status "
        "ENUM('SAVED','APPLIED','PHONE_SCREEN','INTERVIEW','OFFER','REJECTED','WITHDRAWN') "
        "NOT NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE job_applications MODIFY COLUMN status "
        "ENUM('APPLIED','PHONE_SCREEN','INTERVIEW','OFFER','REJECTED','WITHDRAWN') "
        "NOT NULL"
    )
