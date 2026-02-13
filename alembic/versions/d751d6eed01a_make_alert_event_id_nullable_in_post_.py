"""make alert_event_id nullable in post_mortems

Revision ID: d751d6eed01a
Revises: d2f224889c86
Create Date: 2026-02-12 23:51:01.320770

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd751d6eed01a'
down_revision: Union[str, Sequence[str], None] = 'd2f224889c86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Make alert_event_id nullable to allow standalone post-mortems
    op.alter_column('post_mortems', 'alert_event_id',
                    existing_type=sa.BigInteger(),
                    nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert alert_event_id back to NOT NULL
    op.alter_column('post_mortems', 'alert_event_id',
                    existing_type=sa.BigInteger(),
                    nullable=False)
