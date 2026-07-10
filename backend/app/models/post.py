"""Post (image) model."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Post(TimestampMixin, Base):
    """An image in the gallery. Media pipeline + scrapers populate this row."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Origin: 'danbooru' | 'local' | None
    source_site: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Original site post id (for scraped sources); NULL for local imports.
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Relative paths under media_dir.
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    thumb_path: Mapped[str] = mapped_column(String(512), nullable=False)
    preview_path: Mapped[str] = mapped_column(String(512), nullable=False)

    file_ext: Mapped[str] = mapped_column(String(8), nullable=False)
    is_animated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    md5: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    phash: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # is_duplicate is a fast-filter convenience; the authoritative signal is
    # `duplicate_of_id IS NOT NULL` (see CONTEXT.md「重复图」).
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("posts.id", ondelete="SET NULL"), nullable=True
    )

    rating: Mapped[str] = mapped_column(String(16), nullable=False, default="safe")

    __table_args__ = (
        # Partial unique index: a post records only its first source. Prevents
        # the same (source_site, source_id) being imported twice under concurrent
        # scrapes. NULL sources (local imports) are exempt.
        Index(
            "ix_posts_source_site_source_id",
            "source_site",
            "source_id",
            unique=True,
            sqlite_where=text("source_site IS NOT NULL AND source_id IS NOT NULL"),
        ),
        # Read-path indexes: every gallery list request filters on
        # duplicate_of_id IS NULL (and rating='safe' in safe mode) including
        # its COUNT — keep both off the full-table-scan path.
        Index("ix_posts_rating", "rating"),
        Index("ix_posts_duplicate_of_id", "duplicate_of_id"),
    )
