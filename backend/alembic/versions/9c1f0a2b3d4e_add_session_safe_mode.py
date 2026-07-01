"""add session.safe_mode

Revision ID: 9c1f0a2b3d4e
Revises: 74035bafb648
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c1f0a2b3d4e'
down_revision: Union[str, Sequence[str], None] = '74035bafb648'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Session.safe_mode (server-authoritative, defaults to true).

    Safe mode is per-session: the gallery main view injects rating=safe while
    it is on, and new sessions default to safe. Hand-written (not autogenerate)
    so the server_default is explicit; render_as_batch handles SQLite ALTER.
    """
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "safe_mode",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )


def downgrade() -> None:
    """Drop Session.safe_mode."""
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_column("safe_mode")
