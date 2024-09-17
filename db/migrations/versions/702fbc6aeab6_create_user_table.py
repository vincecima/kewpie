"""create user table

Revision ID: 702fbc6aeab6
Revises:
Create Date: 2024-09-01 18:34:52.983801

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "702fbc6aeab6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.UUID, primary_key=True),
        sa.Column("email", sa.String, nullable=False),
        sa.Column("hashed_password", sa.String),
        sa.Column("is_active", sa.Boolean),
        sa.Column("is_superuser", sa.Boolean),
        sa.Column("is_verified", sa.Boolean),
    )


def downgrade() -> None:
    op.drop_table("user")
