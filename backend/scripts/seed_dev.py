"""Dev-only seed: create the single user + a handful of real posts with
hand-written PNG images, so the browse page is visually verifiable without
the import pipeline (which lands in a later subtask).

Run from backend/:
    python -m scripts.seed_dev

Idempotent: skips posts whose md5 already exists; creates the user only if
none exists. Not imported by tests; not production code.
"""
from __future__ import annotations

import struct
import zlib

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models.post import Post
from app.models.tag import PostTag, Tag
from app.models.user import User
from app.services import auth


def _png_solid(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """Encode a minimal solid-color PNG (8-bit RGB, no compression tricks).

    Hand-rolled to avoid a Pillow dependency. PNG = signature + IHDR + IDAT
    (zlib-compressed scanlines) + IEND, each chunk CRC-protected.
    """
    sig = b"\x89PNG\r\n\x1a\n"

    def _chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(
            ">I", zlib.crc32(tag + data) & 0xFFFFFFFF
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    row = bytes([0]) + bytes(rgb) * width  # filter byte 0 + RGB pixels
    raw = b"".join(row for _ in range(height))
    idat = zlib.compress(raw)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


# (w, h, rgb, rating, tags[(name, category)])
_POSTS: list[tuple[int, int, tuple[int, int, int], str, list[tuple[str, str]]]] = [
    (400, 600, (59, 130, 246), "safe", [("miku", "character"), ("vocaloid", "copyright"), ("blue_hair", "general")]),
    (600, 400, (168, 85, 247), "safe", [("vocaloid", "copyright"), ("purple", "general")]),
    (500, 500, (245, 158, 11), "safe", [("miku", "character"), ("yellow", "general")]),
    (800, 600, (34, 197, 94), "safe", [("landscape", "general"), ("green", "general")]),
    (300, 450, (239, 68, 68), "questionable", [("miku", "character"), ("red", "general")]),
    (450, 300, (20, 184, 166), "safe", [("vocaloid", "copyright"), ("teal", "general")]),
    (700, 500, (99, 102, 241), "safe", [("miku", "character"), ("vocaloid", "copyright")]),
    (400, 400, (236, 72, 153), "safe", [("pink", "general"), ("character", "meta")]),
    (600, 800, (148, 163, 184), "safe", [("gray", "general"), ("portrait", "general")]),
    (500, 350, (250, 204, 21), "explicit", [("miku", "character"), ("yellow", "general")]),
    (350, 500, (14, 165, 233), "safe", [("sky", "general"), ("blue", "general")]),
    (650, 450, (217, 70, 239), "safe", [("vocaloid", "copyright"), ("magenta", "general")]),
]


def _ensure_user(db) -> None:  # type: ignore[no-untyped-def]
    if db.execute(select(User.id).limit(1)).first() is not None:
        return
    auth.create_user(db, "admin", "pw12345678")
    print("created user: admin / pw12345678")


def _get_or_create_tag(db, name: str, category: str) -> Tag:  # type: ignore[no-untyped-def]
    tag = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
    if tag is None:
        tag = Tag(name=name, category=category, post_count=0)
        db.add(tag)
        db.commit()
        db.refresh(tag)
    return tag


def _seed_posts(db) -> None:  # type: ignore[no-untyped-def]
    """Seed posts via the real media pipeline (services/media.ingest).

    Replaces the earlier hand-rolled byte-writing + Post construction so dev
    data uses real thumbnails + phash. Dedup is delegated to ingest's md5 check:
    a DuplicateError means the post was already seeded (idempotent skip).
    Tag attachment stays here — materialization of implications is the import
    pipeline subtask's job, and seed inserts the materialized rows directly.
    """
    from app.services import media as media_svc
    from app.services.errors import DuplicateError

    created = 0
    skipped = 0
    for w, h, rgb, rating, tags in _POSTS:
        png = _png_solid(w, h, rgb)
        try:
            post = media_svc.ingest(
                db, png,
                source_site="local", source_id=None, source_url=None,
                file_ext="png", is_animated=False, rating=rating,
            )
        except DuplicateError:
            skipped += 1
            continue
        # Materialized tag set: implications expanded at write time. For the
        # miku->vocaloid demo we insert both rows directly (the real write-time
        # closure logic lands with the import pipeline subtask).
        for name, category in tags:
            tag = _get_or_create_tag(db, name, category)
            db.add(PostTag(post_id=post.id, tag_id=tag.id))
            tag.post_count += 1
        db.commit()
        created += 1
    print(f"posts ready ({created} new, {skipped} already present)")


def main() -> None:
    media = settings.media_path
    media.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        _ensure_user(db)
        _seed_posts(db)
    print(f"media dir: {media}")
    print("done. start the API with:  uvicorn app.main:app --reload --port 8000")


if __name__ == "__main__":
    main()
