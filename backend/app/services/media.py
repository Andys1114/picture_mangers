"""Media processing core: md5/phash/thumbnails + minimal Post ingestion.

This is slice 3 of the gallery app (parent ``06-28-gallery-app`` design.md §4):
the reusable ingestion kernel consumed by the future scraper (slice 4) and the
import API (slice 8). It owns no route, no scheduler, no tag materialization —
those land in later slices.

Dedup contract (``database-guidelines.md``「Duplicate Images」):
- md5 exact dedup is **synchronous** here: a second ingest of the same bytes
  raises ``DuplicateError`` (no row, no file).
- phash is computed **synchronously and stored**, but the *neighbor lookup*
  that would set ``duplicate_of_id`` is **deferred** to a later slice's async
  scheduler — computing the hash value is fast, scanning the table for near
  neighbors is not. So an ingested post always has ``phash`` set but leaves
  ``is_duplicate=False`` and ``duplicate_of_id=None``.
"""
from __future__ import annotations

import hashlib
import io

import imagehash
from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.post import Post
from app.services.errors import DuplicateError

# Longest-edge caps for the two thumbnail tiers (px), per design.md §4.
THUMB_SIZE = 150
PREVIEW_SIZE = 850

# Original / thumbnail file names inside a post's directory. Preview + thumb are
# always static PNG (first frame for animations); original keeps the source ext
# and, for animations, the full animated bytes.
_ORIGINAL_NAME = "original"
_PREVIEW_NAME = "preview.png"
_THUMB_NAME = "thumb.png"


def compute_md5(data: bytes) -> str:
    """Return the hex md5 of the raw image bytes (exact-dedup key)."""
    return hashlib.md5(data).hexdigest()


def compute_phash(image: Image.Image) -> str:
    """Return the perceptual hash (64-bit, as 16-char hex) of ``image``.

    Uses ``imagehash.phash`` (DCT-based) for robustness to scaling/recompression.
    The returned string is the ``ImageHash.__str__`` form (hex of the bit pack).
    """
    return str(imagehash.phash(image))


def _to_rgb(image: Image.Image) -> Image.Image:
    """Flatten RGBA/palette/transparency onto white, returning an RGB image.

    PNGs with alpha or palette mode would raise when saved as JPEG and produce
    unexpected black backgrounds when thumbnailed; flatten to RGB on white for a
    consistent thumbnail. The original bytes are untouched.
    """
    if image.mode == "RGB":
        return image
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        background = Image.new("RGB", image.size, (255, 255, 255))
        base = image.convert("RGBA")
        background.paste(base, mask=base.split()[-1])
        return background
    return image.convert("RGB")


def make_thumbnails(image: Image.Image) -> tuple[bytes, bytes]:
    """Return ``(thumb_bytes, preview_bytes)`` as static PNG.

    Both are longest-edge-capped (``THUMB_SIZE`` / ``PREVIEW_SIZE``) and
    aspect-preserved via ``ImageOps.contain`` (which never upscales). The caller
    must pass a single frame — animated images are reduced to their first frame
    before this call (see :func:`ingest`).
    """
    rgb = _to_rgb(image)
    thumb = ImageOps.contain(rgb, (THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
    preview = ImageOps.contain(rgb, (PREVIEW_SIZE, PREVIEW_SIZE), Image.LANCZOS)

    def _png(img: Image.Image) -> bytes:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    return _png(thumb), _png(preview)


def ingest(
    db: Session,
    data: bytes,
    *,
    source_site: str | None,
    source_id: str | None,
    source_url: str | None,
    file_ext: str,
    is_animated: bool,
    rating: str = "safe",
) -> Post:
    """Ingest raw image ``data``: dedup, process, persist, and write the Post row.

    Steps (see design.md §2):
    1. md5 → reject exact duplicates (``DuplicateError``).
    2. Pillow decode → width/height + phash + thumbnails.
    3. Insert Post with placeholder paths, ``flush`` to obtain ``id``.
    4. Create ``media/posts/{id}/`` and write original/preview/thumb.
    5. Backfill the relative paths and commit.

    Because the directory write happens after ``flush`` but before ``commit``,
    a disk failure rolls the row back via the caller's session lifecycle (the
    ``get_db`` ``finally`` or test fixture) — no half-committed Post survives.
    A possibly-empty ``posts/{id}/`` directory may linger on failure and is
    accepted (reuse on next id, or cleared by re-running seed).

    ``source_site``/``source_id`` are trusted caller inputs; the partial unique
    index on ``(source_site, source_id)`` enforces source dedup for non-null
    sources at the DB level (see ``database-guidelines.md``「Scrape Dedup」).
    """
    md5 = compute_md5(data)

    existing = db.execute(select(Post.id).where(Post.md5 == md5)).first()
    if existing is not None:
        raise DuplicateError("图片已存在(md5 重复)")

    img = Image.open(io.BytesIO(data))
    width, height = img.size
    phash = compute_phash(img)

    # For animated images, thumbnails use the first frame; the original keeps
    # its animated bytes verbatim.
    frame = img
    if is_animated:
        try:
            img.seek(0)
            frame = img.copy()
        except (EOFError, AttributeError):
            frame = img
    thumb_bytes, preview_bytes = make_thumbnails(frame)

    rel_dir = ""  # filled after flush
    post = Post(
        source_site=source_site,
        source_id=source_id,
        source_url=source_url,
        file_path="",  # placeholder; backfilled post-flush
        thumb_path="",
        preview_path="",
        file_ext=file_ext,
        is_animated=is_animated,
        width=width,
        height=height,
        file_size=len(data),
        md5=md5,
        phash=phash,
        is_duplicate=False,
        duplicate_of_id=None,
        rating=rating,
    )
    db.add(post)
    db.flush()  # assign post.id without committing

    rel_dir = f"posts/{post.id}"
    post_dir = settings.media_path / rel_dir
    post_dir.mkdir(parents=True, exist_ok=True)
    (post_dir / f"{_ORIGINAL_NAME}.{file_ext}").write_bytes(data)
    (post_dir / _PREVIEW_NAME).write_bytes(preview_bytes)
    (post_dir / _THUMB_NAME).write_bytes(thumb_bytes)

    post.file_path = f"{rel_dir}/{_ORIGINAL_NAME}.{file_ext}"
    post.preview_path = f"{rel_dir}/{_PREVIEW_NAME}"
    post.thumb_path = f"{rel_dir}/{_THUMB_NAME}"

    db.commit()
    db.refresh(post)
    return post
