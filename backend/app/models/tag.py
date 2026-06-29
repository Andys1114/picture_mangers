"""Tag, PostTag, TagImplication models."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Tag(Base):
    """A tag. Category drives UI color; post_count is a denormalized counter."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    # 'general' | 'character' | 'copyright' | 'artist' | 'meta'
    category: Mapped[str] = mapped_column(String(16), nullable=False, default="general")
    post_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_deprecated: Mapped[bool] = mapped_column(default=False, nullable=False)


class PostTag(Base):
    """Association: a post is tagged with a tag."""

    __tablename__ = "post_tags"

    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (
        # Reverse lookup: "all posts with this tag".
        Index("ix_post_tags_tag_id", "tag_id"),
    )


class TagImplication(Base):
    """Antecedent implies consequent: tagging antecedent auto-includes consequent.

    Search expands the chain recursively. Danbooru-imported data populates this.
    """

    __tablename__ = "tag_implications"

    id: Mapped[int] = mapped_column(primary_key=True)
    antecedent_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )
    consequent_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")

    __table_args__ = (
        UniqueConstraint("antecedent_id", "consequent_id", name="uq_implication_pair"),
    )
