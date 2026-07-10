"""Tag write-side: implication materialization + post_count + tag CRUD.

Implements ADR-0001 (``docs/adr/0001-implication-materialized-at-write-time.md``):
implications are materialized at write time into ``post_tags`` (the expanded
closure), so the read side (``services/search.py``) does a plain AND match
with no read-time recursion. Three invariants from the ADR:

1. **Materialize at write time** — ``tag_post`` computes the full antecedent
   closure (A→B→C) and writes all of it into ``post_tags`` in one pass.
2. **Backfill on implication add** — ``create_implication`` finds every post
   already tagged with the antecedent and writes the new consequent (and its
   downstream closure) onto them, so ``post_tags`` stays the full set.
3. **Sticky delete** — this slice does NOT delete implications or tags; the
   ADR's "delete is sticky (don't retract consequents)" rule is honored by
   omission. DELETE endpoints are intentionally absent.

Cycle prevention: before inserting an implication A→B, a reverse-reachability
check ("can B already reach A?") rejects the edge with ``ConflictError`` (409).
The closure computation also carries a visited-set guard as belt-and-suspenders
against any pre-existing cycle.
"""
from __future__ import annotations

from sqlalchemy import literal, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.tag import PostTag, Tag, TagImplication
from app.services.errors import ConflictError, NotFoundError

# Reverse-lookup index on PostTag.tag_id already exists (ix_post_tags_tag_id);
# no new indexes needed here.


# --- read helpers (for endpoints) -----------------------------------------

def get_tag(db: Session, tag_id: int) -> Tag:
    """Return a tag by id or raise 404."""
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise NotFoundError("标签不存在")
    return tag


def list_tags(
    db: Session,
    *,
    search: str = "",
    category: str | None = None,
    order: str = "count",
    limit: int = 200,
) -> list[Tag]:
    """List tags for the /tags page + autocomplete.

    - ``search``: substring match on name (case-insensitive).
    - ``category``: filter by category.
    - ``order``: ``count`` (post_count desc) or ``name`` (alphabetical).
    """
    stmt = select(Tag)
    if search:
        stmt = stmt.where(Tag.name.ilike(f"%{search}%"))
    if category:
        stmt = stmt.where(Tag.category == category)
    if order == "name":
        stmt = stmt.order_by(Tag.name)
    else:
        stmt = stmt.order_by(Tag.post_count.desc(), Tag.name)
    stmt = stmt.limit(limit)
    return list(db.execute(stmt).scalars().all())


def tag_tree(db: Session) -> list[tuple[Tag, list[Tag]]]:
    """Return the implication tree: for each antecedent, its direct consequents.

    Used by ``GET /api/tags/tree`` for the collapsible tree view. Only tags that
    are antecedents of at least one active implication appear as roots.
    """
    rows = db.execute(
        select(Tag, TagImplication.consequent_id)
        .join(TagImplication, TagImplication.antecedent_id == Tag.id)
        .where(TagImplication.status == "active")
        .order_by(Tag.category, Tag.name)
    ).all()
    if not rows:
        return []

    # Group consequent ids by antecedent, preserving first-seen order.
    antecedent_ids: list[int] = []
    members: dict[int, list[int]] = {}
    antecedents: dict[int, Tag] = {}
    for ant, consequent_id in rows:
        if ant.id not in members:
            members[ant.id] = []
            antecedent_ids.append(ant.id)
            antecedents[ant.id] = ant
        members[ant.id].append(consequent_id)

    consequent_ids = sorted({c for ids in members.values() for c in ids})
    consequent_map: dict[int, Tag] = {}
    if consequent_ids:
        for c in db.execute(select(Tag).where(Tag.id.in_(consequent_ids))).scalars():
            consequent_map[c.id] = c

    result: list[tuple[Tag, list[Tag]]] = []
    for aid in antecedent_ids:
        cons = [consequent_map[c] for c in members[aid] if c in consequent_map]
        result.append((antecedents[aid], cons))
    return result


# --- closure (write-time only) --------------------------------------------

def closure_of(db: Session, tag_ids: list[int]) -> set[int]:
    """Return the full consequent closure of ``tag_ids``: every tag reachable
    by following antecedent→consequent edges transitively (including the seeds
    themselves).

    Write-time only (ADR-0001); the read side never calls this. Implemented as
    an application-layer BFS with a visited set — semantically equivalent to a
    recursive CTE, and the visited set is the ADR's belt-and-suspenders guard
    against any pre-existing cycle. A recursive CTE was the spec preference,
    but SQLAlchemy 2.0's recursive CTE construction on SQLite is finicky enough
    that the BFS form is clearer and equally correct for single-user scale.
    """
    result: set[int] = set()
    frontier = [tid for tid in tag_ids if tid is not None]
    while frontier:
        next_frontier: list[int] = []
        edges = db.execute(
            select(TagImplication.consequent_id)
            .where(
                TagImplication.antecedent_id.in_(frontier),
                TagImplication.status == "active",
            )
        ).scalars().all()
        for consequent_id in edges:
            if consequent_id not in result and consequent_id not in frontier:
                next_frontier.append(consequent_id)
        result.update(frontier)
        frontier = next_frontier
    # Seeds are part of the closure (the post is tagged with them directly).
    result.update(tid for tid in tag_ids if tid is not None)
    return result


def _reaches(db: Session, source_id: int, target_id: int) -> bool:
    """True if ``target_id`` is reachable from ``source_id`` via active edges.

    Used for cycle prevention: before adding A→B, check ``_reaches(B, A)`` —
    if B can already reach A, then A→B would close a cycle.
    """
    return target_id in closure_of(db, [source_id])


# --- tag CRUD -------------------------------------------------------------

def create_tag(db: Session, name: str, category: str = "general") -> Tag:
    """Create a tag. Raises ConflictError (409) if the name is taken."""
    existing = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"标签已存在: {name}")
    tag = Tag(name=name, category=category, post_count=0)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(
    db: Session,
    tag_id: int,
    *,
    name: str | None = None,
    category: str | None = None,
) -> Tag:
    """Rename and/or recategorize a tag.

    Renaming only touches the Tag row; ``post_tags`` references tag_id (not
    name), so the materialized set is unaffected. A name collision raises
    ConflictError (409).
    """
    tag = get_tag(db, tag_id)
    if name is not None and name != tag.name:
        clash = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
        if clash is not None:
            raise ConflictError(f"标签名已被占用: {name}")
        tag.name = name
    if category is not None:
        tag.category = category
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


# --- write side: tag_post + create_implication ----------------------------

def tag_post(
    db: Session,
    post_id: int,
    names: list[str],
    commit: bool = True,
) -> list[Tag]:
    """Attach tags to a post, materializing the implication closure.

    For each name: get-or-create the Tag, then compute the full closure of the
    direct tag set and write every closure member into ``post_tags`` that isn't
    already there. ``post_count`` is bumped (+1) for each newly-inserted
    ``post_tags`` row. Idempotent: re-tagging with an already-present tag is a
    no-op (the composite PK dedupes; post_count is not double-counted).

    Transaction ownership: with ``commit=True`` (default) this call owns the
    transaction — it commits on success, and if the tag get-or-create loses a
    concurrent create race on the ``Tag.name`` unique constraint it rolls back
    and reruns the whole pass once (the re-query then finds the winner's row).
    With ``commit=False`` the caller owns the transaction: changes are flushed
    only, and errors propagate for the caller to roll back.

    This is the entry point the scraper (slice 4) and the edit endpoint
    (slice 6) call. It does not expose an HTTP endpoint itself.
    """
    if commit:
        try:
            closure = _tag_post_pass(db, post_id, names)
            db.commit()
        except IntegrityError:
            # Lost a get-or-create race: a concurrent session committed the
            # same tag name between our SELECT and flush. The whole pass is
            # rerun rather than a single re-query because the rollback also
            # discarded any tags created earlier in this pass.
            db.rollback()
            try:
                closure = _tag_post_pass(db, post_id, names)
                db.commit()
            except Exception:
                db.rollback()
                raise
    else:
        closure = _tag_post_pass(db, post_id, names)
        # Sessions run with autoflush=False: flush so the caller's follow-up
        # queries in the same transaction see the new post_tags rows.
        db.flush()

    return list(db.execute(select(Tag).where(Tag.id.in_(closure))).scalars().all())


def _tag_post_pass(db: Session, post_id: int, names: list[str]) -> set[int]:
    """One flush-only tagging pass; returns the closure's tag ids.

    Commit/rollback is the caller's job (``tag_post``), so a lost
    get-or-create race can discard and rerun the pass as a unit.
    """
    direct_ids: list[int] = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        tag = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
        if tag is None:
            tag = Tag(name=name, category="general", post_count=0)
            db.add(tag)
            db.flush()  # get tag.id without committing
        direct_ids.append(tag.id)

    closure = closure_of(db, direct_ids)

    existing = {
        tid
        for (tid,) in db.execute(
            select(PostTag.tag_id).where(PostTag.post_id == post_id)
        ).all()
    }

    for tid in closure:
        if tid in existing:
            continue
        db.add(PostTag(post_id=post_id, tag_id=tid))
        tag = db.get(Tag, tid)
        if tag is not None:
            tag.post_count += 1

    return closure


def create_implication(
    db: Session,
    antecedent_id: int,
    consequent_id: int,
) -> TagImplication:
    """Create an antecedent→consequent implication and backfill existing posts.

    Steps:
    1. Self-loop: A→A is rejected (ConflictError 409).
    2. Cycle prevention: if ``consequent`` can already reach ``antecedent``,
       adding the edge would close a cycle → ConflictError 409.
    3. Insert the TagImplication row (the unique-pair constraint dedupes a
       literal duplicate; a re-add of the exact same edge is a no-op return of
       the existing row).
    4. Backfill: every post already tagged with ``antecedent`` gets the new
       consequent (and its downstream closure) written into ``post_tags``,
       bumping the affected tags' ``post_count``. This keeps ``post_tags`` the
       full expanded set (ADR-0001 invariant 2).

    The ADR's "sticky delete" rule is honored by omission — this slice provides
    no deletion path for implications.
    """
    if antecedent_id == consequent_id:
        raise ConflictError("不能创建自环 implication")

    # Cycle prevention: can consequent already reach antecedent?
    if _reaches(db, consequent_id, antecedent_id):
        raise ConflictError("该 implication 会形成环")

    # Insert (or return the existing active row if the exact pair is already there).
    existing = db.execute(
        select(TagImplication).where(
            TagImplication.antecedent_id == antecedent_id,
            TagImplication.consequent_id == consequent_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.status != "active":
            existing.status = "active"
            db.add(existing)
            db.commit()
            db.refresh(existing)
        return existing

    impl = TagImplication(antecedent_id=antecedent_id, consequent_id=consequent_id, status="active")
    db.add(impl)
    db.flush()

    # Backfill: posts already tagged with the antecedent must gain the new
    # consequent (and its downstream closure).
    affected_post_ids = [
        pid for (pid,) in db.execute(
            select(PostTag.post_id).where(PostTag.tag_id == antecedent_id)
        ).all()
    ]
    if affected_post_ids:
        new_closure = closure_of(db, [antecedent_id])
        # new_closure now includes consequent_id and its downstream.
        # Batched reads: one IN query builds the existing (post_id → tag_ids)
        # map instead of one SELECT per affected post, the closure's Tag rows
        # are fetched once, and post_count bumps are aggregated per tag.
        existing_pairs: dict[int, set[int]] = {pid: set() for pid in affected_post_ids}
        for pid, tid in db.execute(
            select(PostTag.post_id, PostTag.tag_id).where(
                PostTag.post_id.in_(affected_post_ids)
            )
        ).all():
            existing_pairs[pid].add(tid)

        tags_by_id: dict[int, Tag] = {
            t.id: t
            for t in db.execute(select(Tag).where(Tag.id.in_(new_closure))).scalars()
        }
        added_counts: dict[int, int] = {}
        for pid in affected_post_ids:
            already = existing_pairs[pid]
            for tid in new_closure:
                if tid in already:
                    continue
                db.add(PostTag(post_id=pid, tag_id=tid))
                added_counts[tid] = added_counts.get(tid, 0) + 1
        for tid, count in added_counts.items():
            tag = tags_by_id.get(tid)
            if tag is not None:
                tag.post_count += count

    db.commit()
    db.refresh(impl)
    return impl
