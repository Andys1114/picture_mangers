"""Media pipeline: md5 dedup, phash, thumbnails, Post ingest (slice 3).

Covers AC1-AC4 + AC6 of the media-pipeline task. Each test runs against the tmp
DB (migrated schema via the ``client`` fixture) and a tmp media dir so nothing
touches the real ``backend/media``.
"""
from __future__ import annotations

import io
from pathlib import Path

import imagehash
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app import db as db_module
from app.config import settings
from app.models.post import Post
from app.services import media
from app.services.errors import DuplicateError


# --- fixtures --------------------------------------------------------------

@pytest.fixture()
def media_dir(tmp_path, monkeypatch) -> Path:
    """Redirect the media store to a tmp dir for the duration of the test."""
    d = tmp_path / "media"
    d.mkdir(parents=True, exist_ok=True)
    # media.media_path reads settings.media_path, so patch settings.
    monkeypatch.setattr(settings, "media_dir", str(d))
    return settings.media_path


@pytest.fixture()
def db():
    """A fresh ORM session against the test DB (schema already migrated)."""
    s = db_module.SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _png_bytes(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """A solid-color PNG (RGB) as bytes — the canonical ingest input."""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), rgb).save(buf, format="PNG")
    return buf.getvalue()


def _textured_png(width: int, height: int, seed: int) -> bytes:
    """A PNG with real spatial structure (gradient + checker) so pHash can
    discriminate it. Solid colors collapse to a single-DC hash and cannot test
    phash discrimination; this builds two distinct textured fields from ``seed``.
    """
    img = Image.new("RGB", (width, height))
    px = img.load()
    for y in range(height):
        for x in range(width):
            # diagonal gradient XOR a checkerboard — seed shifts the phase
            base = (x * 4 + y * 3 + seed * 17) & 0xFF
            if ((x // 16 + y // 16 + seed) % 2) == 0:
                base ^= 0x80
            r = base & 0xFF
            g = (base * 2 + seed * 7) & 0xFF
            b = (base * 3 + seed * 13) & 0xFF
            px[x, y] = (r, g, b)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _gif_bytes(frames: int, width: int = 120, height: int = 80) -> bytes:
    """A genuinely multi-frame animated GIF (distinct RGB content per frame).

    Each frame carries a different gradient so Pillow registers them as real
    separate frames (single-color palette frames collapse to n_frames=1).
    """
    imgs: list[Image.Image] = []
    for i in range(max(frames, 2)):
        img = Image.new("RGB", (width, height))
        px = img.load()
        for y in range(height):
            for x in range(width):
                px[x, y] = (((x + i * 10) * 2) & 0xFF, ((y + i * 5) * 2) & 0xFF, (i * 60) & 0xFF)
        imgs.append(img)
    buf = io.BytesIO()
    imgs[0].save(
        buf, format="GIF", save_all=True, append_images=imgs[1:],
        duration=100, loop=0,
    )
    return buf.getvalue()


# --- AC1: ingest creates files + Post row ----------------------------------

def test_ingest_creates_files_and_post(client: TestClient, media_dir: Path, db) -> None:
    """AC1: ingest writes original/preview/thumb under posts/{id}/ and a Post row
    with relative paths + correct width/height/file_size/md5/rating."""
    data = _png_bytes(400, 600, (59, 130, 246))
    post = media.ingest(
        db, data,
        source_site="local", source_id=None, source_url=None,
        file_ext="png", is_animated=False, rating="safe",
    )

    # Files exist on disk under posts/{id}/.
    post_dir = media_dir / "posts" / str(post.id)
    assert (post_dir / "original.png").read_bytes() == data
    assert (post_dir / "preview.png").exists()
    assert (post_dir / "thumb.png").exists()

    # Post row stores relative paths (portable across media dir moves).
    assert post.file_path == f"posts/{post.id}/original.png"
    assert post.preview_path == f"posts/{post.id}/preview.png"
    assert post.thumb_path == f"posts/{post.id}/thumb.png"

    assert post.width == 400
    assert post.height == 600
    assert post.file_size == len(data)
    assert post.md5 == media.compute_md5(data)
    assert post.rating == "safe"
    assert post.is_animated is False
    # phash left to AC3, duplicate fields to later slices
    assert post.is_duplicate is False
    assert post.duplicate_of_id is None


# --- AC2: md5 exact dedup --------------------------------------------------

def test_ingest_md5_duplicate_raises(client: TestClient, media_dir: Path, db) -> None:
    """AC2: a second ingest of the same bytes raises DuplicateError (code 409),
    produces no second Post row, and writes no second directory."""
    data = _png_bytes(300, 300, (10, 20, 30))
    first = media.ingest(
        db, data,
        source_site="local", source_id=None, source_url=None,
        file_ext="png", is_animated=False,
    )

    with pytest.raises(DuplicateError) as exc:
        media.ingest(
            db, data,
            source_site="local", source_id=None, source_url=None,
            file_ext="png", is_animated=False,
        )
    assert exc.value.code == "duplicate"
    assert exc.value.status_code == 409

    # Exactly one Post row, exactly one post directory.
    assert db.query(Post).count() == 1
    dirs = [p for p in (media_dir / "posts").iterdir()] if (media_dir / "posts").exists() else []
    assert len(dirs) == 1
    assert dirs[0].name == str(first.id)


# --- AC3: phash computed + sane distance -----------------------------------

def test_ingest_computes_phash(client: TestClient, media_dir: Path, db) -> None:
    """AC3: ingest stores a non-null phash; a duplicate of the same bytes hashes
    identically, and a distinct textured image hashes far apart.

    Uses textured fields because pHash on a solid color collapses to a single
    DC coefficient and cannot discriminate colors — texture is what pHash keys
    on.
    """
    base = _textured_png(256, 256, seed=1)
    post = media.ingest(
        db, base,
        source_site="local", source_id=None, source_url=None,
        file_ext="png", is_animated=False,
    )
    assert post.phash is not None and len(post.phash) > 0

    def _hamming(h1: str, h2: str) -> int:
        return bin(int(h1, 16) ^ int(h2, 16)).count("1")

    # Same bytes → identical phash.
    same = media.compute_phash(Image.open(io.BytesIO(base)))
    assert _hamming(post.phash, same) == 0

    # A differently-textured image → large Hamming distance.
    other = media.compute_phash(Image.open(io.BytesIO(_textured_png(256, 256, seed=99))))
    assert _hamming(post.phash, other) >= 8


# --- AC4: thumbnail dimensions + animated first frame ----------------------

def test_thumbnail_dimensions_static(client: TestClient, media_dir: Path, db) -> None:
    """AC4: thumb ≤ 150, preview ≤ 850 (longest edge), aspect preserved."""
    data = _png_bytes(1600, 900, (40, 200, 120))
    post = media.ingest(
        db, data,
        source_site="local", source_id=None, source_url=None,
        file_ext="png", is_animated=False,
    )
    thumb = Image.open(media_dir / post.thumb_path)
    preview = Image.open(media_dir / post.preview_path)
    assert max(thumb.size) <= media.THUMB_SIZE
    assert max(preview.size) <= media.PREVIEW_SIZE
    # 1600x900 aspect (16:9) preserved on the longest edge.
    assert abs(thumb.size[0] / thumb.size[1] - 1600 / 900) < 0.05


def test_animated_gif_first_frame_static_original_kept(client: TestClient, media_dir: Path, db) -> None:
    """AC4: an animated ingest keeps the animated original, but thumb/preview are
    static single-frame PNGs (first frame) and is_animated is True."""
    data = _gif_bytes(frames=3)
    post = media.ingest(
        db, data,
        source_site="local", source_id=None, source_url=None,
        file_ext="gif", is_animated=True,
    )
    assert post.is_animated is True

    # Original retains animation.
    original = Image.open(media_dir / post.file_path)
    assert getattr(original, "is_animated", False) is True

    # Thumbnails are static.
    thumb = Image.open(media_dir / post.thumb_path)
    assert getattr(thumb, "is_animated", False) is False
    assert thumb.format == "PNG"


# --- AC6: rollback on disk failure -----------------------------------------

def test_ingest_rollback_on_disk_failure(client: TestClient, media_dir: Path, db, monkeypatch) -> None:
    """AC6: if the directory write fails after flush, no Post row is committed.

    We point ``media.settings.media_path`` at a path whose ``posts`` subdir
    cannot be created (an existing file blocks it), forcing ``mkdir`` to raise.
    ingest must propagate the error without leaving a committed Post behind —
    the session rolls back when the caller closes it.
    """
    data = _png_bytes(200, 200, (1, 2, 3))

    # Place a regular file where ingest wants to mkdir a directory.
    blocker = media_dir / "posts_blocker"
    blocker.write_text("not a directory")
    monkeypatch.setattr(settings, "media_dir", str(blocker))

    with pytest.raises(OSError):
        media.ingest(
            db, data,
            source_site="local", source_id=None, source_url=None,
            file_ext="png", is_animated=False,
        )

    # The failed row was flushed but never committed; rollback discards it.
    db.rollback()
    assert db.query(Post).count() == 0
