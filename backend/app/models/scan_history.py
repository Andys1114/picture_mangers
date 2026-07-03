"""ScanHistory model — tracks locally-imported files for incremental scans."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ScanHistory(Base):
    """A file that has been scanned by a local import. Used to skip unchanged
    files on re-scan (mtime check) without re-reading bytes / re-computing md5.

    ``path`` is unique so a re-scan of the same file updates its row rather
    than inserting a duplicate.
    """

    __tablename__ = "scan_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    mtime: Mapped[float] = mapped_column(Float, nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
