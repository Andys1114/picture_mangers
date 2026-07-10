"""favorites name unique + rating/duplicate/favorite-item indexes

Revision ID: 0a12b23de454
Revises: ffcb2b9d04bb
Create Date: 2026-07-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a12b23de454'
down_revision: Union[str, Sequence[str], None] = 'ffcb2b9d04bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Lightweight table handle for the data fix-up (no model import in migrations).
_favorites = sa.table(
    "favorites",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
)


def upgrade() -> None:
    """Enforce unique favorite names and add read-path indexes.

    - De-duplicate favorites.name first: for each name the lowest-id row is
      kept as-is and every later row is renamed to "<name>-<id>" (one-way
      cleanup, not reversed on downgrade). Then uniqueness is enforced via a
      unique INDEX, deliberately not a table constraint: a constraint would
      need a batch-mode table rebuild, and dropping the old favorites table
      under PRAGMA foreign_keys=ON (set by env.py) fires favorite_items'
      ON DELETE CASCADE — wiping every membership row. The index enforces the
      same rule with no rebuild.
    - Index posts.rating and posts.duplicate_of_id (every gallery list request
      COUNTs with these filters) and favorite_items.post_id (membership checks
      and the star toggle query by post_id, which the composite PK on
      (favorite_id, post_id) cannot serve).
    """
    conn = op.get_bind()
    keepers = sa.select(sa.func.min(_favorites.c.id)).group_by(_favorites.c.name)
    conn.execute(
        sa.update(_favorites)
        .where(_favorites.c.id.notin_(keepers))
        .values(name=_favorites.c.name + "-" + sa.cast(_favorites.c.id, sa.String))
    )

    op.create_index("ux_favorites_name", "favorites", ["name"], unique=True)
    op.create_index("ix_posts_rating", "posts", ["rating"])
    op.create_index("ix_posts_duplicate_of_id", "posts", ["duplicate_of_id"])
    op.create_index("ix_favorite_items_post_id", "favorite_items", ["post_id"])


def downgrade() -> None:
    """Drop the four indexes. The de-dup renames are not reversed."""
    op.drop_index("ix_favorite_items_post_id", table_name="favorite_items")
    op.drop_index("ix_posts_duplicate_of_id", table_name="posts")
    op.drop_index("ix_posts_rating", table_name="posts")
    op.drop_index("ux_favorites_name", table_name="favorites")
