"""align post schema: drop fav_count, add duplicate_of_id, add source partial unique index

Revision ID: 74035bafb648
Revises: f3d99311f0cf
Create Date: 2026-06-30 20:25:09.793490

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74035bafb648'
down_revision: Union[str, Sequence[str], None] = 'f3d99311f0cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Align posts schema with grilling decisions (ADR-0001 / CONTEXT.md).

    - Drop fav_count: favorite counts are not tracked (derivable from
      favorite_items membership).
    - Add duplicate_of_id: self-FK (ondelete SET NULL), nullable. Authoritative
      duplicate signal; is_duplicate is just a fast-filter.
    - Add partial unique index on (source_site, source_id) for non-null sources
      to prevent double-import under concurrent scrapes.

    Hand-written (not autogenerate): Alembic cannot reliably detect a partial
    index's WHERE predicate. render_as_batch handles SQLite ALTER + the
    self-referencing FK via table rebuild.
    """
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.drop_column("fav_count")
        batch_op.add_column(
            sa.Column("duplicate_of_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_posts_duplicate_of_id_posts",
            "posts",
            ["duplicate_of_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_posts_source_site_source_id",
            ["source_site", "source_id"],
            unique=True,
            sqlite_where=sa.text(
                "source_site IS NOT NULL AND source_id IS NOT NULL"
            ),
        )


def downgrade() -> None:
    """Reverse the schema alignment back to the initial migration shape."""
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.drop_index("ix_posts_source_site_source_id")
        batch_op.drop_constraint("fk_posts_duplicate_of_id_posts", type_="foreignkey")
        batch_op.drop_column("duplicate_of_id")
        batch_op.add_column(
            sa.Column(
                "fav_count", sa.Integer(), nullable=False, server_default="0"
            )
        )
