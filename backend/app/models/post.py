"""Post (image) model."""
from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
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
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    rating: Mapped[str] = mapped_column(String(16), nullable=False, default="safe")
    fav_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
