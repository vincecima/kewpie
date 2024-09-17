"""create accesstoken table

Revision ID: 95070838e48a
Revises: 702fbc6aeab6
Create Date: 2024-09-01 18:57:12.015913

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "95070838e48a"
down_revision: Union[str, None] = "702fbc6aeab6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accesstoken",
        sa.Column("token", sa.String, primary_key=True),
        sa.Column("user_id", sa.UUID, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table("accesstoken")
