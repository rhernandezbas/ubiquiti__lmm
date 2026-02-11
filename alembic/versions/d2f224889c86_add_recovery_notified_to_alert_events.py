"""add_recovery_notified_to_alert_events

Revision ID: d2f224889c86
Revises: 
Create Date: 2026-02-11 01:52:24.313853

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2f224889c86'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add recovery_notified column to alert_events table."""
    # Add the recovery_notified column
    op.add_column('alert_events',
        sa.Column('recovery_notified', sa.Boolean(), nullable=False, server_default='0')
    )

    # Create index for faster queries on pending notifications
    op.create_index(
        'idx_alert_events_recovery_pending',
        'alert_events',
        ['status', 'auto_resolved', 'recovery_notified'],
        unique=False
    )


def downgrade() -> None:
    """Remove recovery_notified column from alert_events table."""
    # Drop index first
    op.drop_index('idx_alert_events_recovery_pending', table_name='alert_events')

    # Drop column
    op.drop_column('alert_events', 'recovery_notified')
