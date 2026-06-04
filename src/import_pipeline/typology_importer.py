"""Import typology (Type nodes and PREFIGURES/MEMBER_OF/TEACHES edges) into Neo4j.

Mirrors the conventions in crossref_importer.py / catechism_importer.py:
UNWIND batches, MERGE for idempotency, tqdm progress, (created, skipped) returns.
"""

import logging
from typing import Callable, Iterable

from tqdm import tqdm

from src.config import settings
from src.db.connection import Neo4jConnection, get_connection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Type nodes
# ---------------------------------------------------------------------------

def import_types(
    types: Iterable[dict],
    connection: Neo4jConnection | None = None,
    batch_size: int | None = None,
) -> int:
    """Import Type nodes into Neo4j using batch processing.

    Uses MERGE on id so the import is idempotent / re-runnable. Reviewed types
    have no category; the property is set null-safe.

    Args:
        types: Iterable of dicts with keys id, name, testament, category,
            description, source, confidence, reviewed.
        connection: Neo4j connection. Defaults to singleton connection.
        batch_size: Nodes per batch. Defaults to settings.BATCH_SIZE.

    Returns:
        Number of Type nodes processed.
    """
    if connection is None:
        connection = get_connection()
    if batch_size is None:
        batch_size = settings.BATCH_SIZE

    query = """
        UNWIND $types AS t
        MERGE (n:Type {id: t.id})
        SET n.name = t.name,
            n.testament = t.testament,
            n.category = t.category,
            n.description = t.description,
            n.source = t.source,
            n.confidence = t.confidence,
            n.reviewed = t.reviewed
        RETURN count(n) AS processed
    """

    types_list = list(types)
    total = 0

    logger.info(f"Importing {len(types_list)} Type nodes in batches of {batch_size}")
    with tqdm(total=len(types_list), desc="Importing Type nodes") as pbar:
        for i in range(0, len(types_list), batch_size):
            batch = types_list[i : i + batch_size]
            with connection.session() as session:
                record = session.run(query, types=batch).single()
                total += record["processed"] if record else 0
            pbar.update(len(batch))

    logger.info(f"Imported {total} Type nodes")
    return total


# ---------------------------------------------------------------------------
# Relationship importers
# ---------------------------------------------------------------------------

def import_prefigures(
    relationships: Iterable[dict],
    connection: Neo4jConnection | None = None,
    batch_size: int | None = None,
) -> tuple[int, int]:
    """Import PREFIGURES edges (OT type -> NT antitype).

    One edge per (from, to) pair, MERGEd, accumulating ``sources`` and
    ``source_verses`` arrays across all attesting sources (CCC paragraphs and
    Haydock verses) -- mirrors the cross-reference sources-array convention.

    Args:
        relationships: dicts with keys from, to, source, confidence, category,
            notes, source_verse (source_verse may be None for CCC seed rows).

    Returns:
        Tuple of (edges_processed, edges_skipped) where skipped rows had a
        missing Type endpoint.
    """
    query = """
        UNWIND $rels AS rel
        MATCH (a:Type {id: rel.from})
        MATCH (b:Type {id: rel.to})
        MERGE (a)-[r:PREFIGURES]->(b)
        ON CREATE SET
            r.category = rel.category,
            r.confidence = rel.confidence,
            r.notes = rel.notes,
            r.sources = [rel.source],
            r.source_verses = CASE
                WHEN rel.source_verse IS NOT NULL THEN [rel.source_verse] ELSE []
            END
        ON MATCH SET
            r.sources = CASE
                WHEN rel.source IN r.sources THEN r.sources
                ELSE r.sources + [rel.source]
            END,
            r.source_verses = CASE
                WHEN rel.source_verse IS NULL OR rel.source_verse IN r.source_verses
                    THEN r.source_verses
                ELSE r.source_verses + [rel.source_verse]
            END,
            r.category = CASE WHEN r.category IS NULL THEN rel.category ELSE r.category END,
            r.confidence = CASE WHEN r.confidence IS NULL THEN rel.confidence ELSE r.confidence END
        RETURN count(r) AS created
    """
    return _import_edges(
        relationships, query, "rels", lambda batch: len(batch),
        "Importing PREFIGURES edges", connection, batch_size,
    )


def import_verse_memberships(
    memberships: Iterable[dict],
    connection: Neo4jConnection | None = None,
    batch_size: int | None = None,
) -> tuple[int, int]:
    """Import MEMBER_OF edges (Verse -> Type) from {type_id, verse_ids[]} rows.

    Returns (edges_processed, verse_refs_skipped) -- skipped counts verse
    references whose Verse (or the Type) did not exist.
    """
    query = """
        UNWIND $rows AS m
        MATCH (t:Type {id: m.type_id})
        UNWIND m.verse_ids AS vid
        MATCH (v:Verse {id: vid})
        MERGE (v)-[r:MEMBER_OF]->(t)
        RETURN count(r) AS created
    """
    return _import_edges(
        memberships, query, "rows",
        lambda batch: sum(len(m.get("verse_ids", [])) for m in batch),
        "Importing MEMBER_OF edges", connection, batch_size,
    )


def import_teaches(
    teaches: Iterable[dict],
    connection: Neo4jConnection | None = None,
    batch_size: int | None = None,
) -> tuple[int, int]:
    """Import TEACHES edges (CatechismParagraph -> Type) from {ccc_id, type_ids[]}.

    Returns (edges_processed, type_refs_skipped).
    """
    query = """
        UNWIND $rows AS x
        MATCH (c:CatechismParagraph {id: x.ccc_id})
        UNWIND x.type_ids AS tid
        MATCH (t:Type {id: tid})
        MERGE (c)-[r:TEACHES]->(t)
        RETURN count(r) AS created
    """
    return _import_edges(
        teaches, query, "rows",
        lambda batch: sum(len(x.get("type_ids", [])) for x in batch),
        "Importing TEACHES edges", connection, batch_size,
    )


def _import_edges(
    records: Iterable[dict],
    query: str,
    params_key: str,
    count_rows: Callable[[list[dict]], int],
    desc: str,
    connection: Neo4jConnection | None,
    batch_size: int | None,
) -> tuple[int, int]:
    """Run an edge-import query in batches; aggregate (created, skipped).

    ``count_rows`` returns the number of edge rows a batch represents (so that
    skipped = rows - created accounts for missing endpoints).
    """
    if connection is None:
        connection = get_connection()
    if batch_size is None:
        batch_size = settings.BATCH_SIZE

    records_list = list(records)
    total_created = 0
    total_skipped = 0

    logger.info(f"{desc}: {len(records_list)} rows in batches of {batch_size}")
    with tqdm(total=len(records_list), desc=desc) as pbar:
        for i in range(0, len(records_list), batch_size):
            batch = records_list[i : i + batch_size]
            with connection.session() as session:
                record = session.run(query, **{params_key: batch}).single()
                created = record["created"] if record else 0
            total_created += created
            total_skipped += count_rows(batch) - created
            pbar.update(len(batch))

    logger.info(f"{desc}: created {total_created}, skipped {total_skipped} (missing endpoints)")
    return total_created, total_skipped
