"""Import cross-references into Neo4j."""

import logging
from typing import Iterable

from tqdm import tqdm

from src.config import settings
from src.db.connection import Neo4jConnection, get_connection

logger = logging.getLogger(__name__)


def import_crossrefs(
    crossrefs: Iterable[dict],
    connection: Neo4jConnection | None = None,
    batch_size: int | None = None,
) -> tuple[int, int]:
    """Import cross-references into Neo4j using batch processing.

    Uses MERGE to handle duplicates gracefully. Only creates edges
    when both source and target verses exist.

    Args:
        crossrefs: Iterable of cross-reference dictionaries with keys:
            from_id, to_id, votes, source, passage_group (optional)
        connection: Neo4j connection. Defaults to singleton connection.
        batch_size: Number of edges per batch. Defaults to settings.BATCH_SIZE * 2.

    Returns:
        Tuple of (edges_created, edges_skipped).
    """
    if connection is None:
        connection = get_connection()

    if batch_size is None:
        batch_size = settings.BATCH_SIZE * 2  # Cross-refs can be larger batches

    # Collect cross-refs into batches
    batch: list[dict] = []
    total_created = 0
    total_skipped = 0

    # Convert to list to get count for progress bar
    crossrefs_list = list(crossrefs)
    total_crossrefs = len(crossrefs_list)

    logger.info(f"Importing {total_crossrefs} cross-references in batches of {batch_size}")

    with tqdm(total=total_crossrefs, desc="Importing cross-refs") as pbar:
        for crossref in crossrefs_list:
            batch.append(crossref)

            if len(batch) >= batch_size:
                created, skipped = _import_batch(connection, batch)
                total_created += created
                total_skipped += skipped
                pbar.update(len(batch))
                batch = []

        # Import remaining cross-refs
        if batch:
            created, skipped = _import_batch(connection, batch)
            total_created += created
            total_skipped += skipped
            pbar.update(len(batch))

    logger.info(f"Created {total_created} edges, skipped {total_skipped} (missing verses)")
    return total_created, total_skipped


def _import_batch(connection: Neo4jConnection, batch: list[dict]) -> tuple[int, int]:
    """Import a batch of cross-references using UNWIND and MERGE.

    Handles multi-source edges:
    - ON CREATE: Initialize sources array and set properties
    - ON MATCH: Append source if not already present

    Args:
        connection: Neo4j connection.
        batch: List of cross-reference dictionaries.

    Returns:
        Tuple of (edges_created, edges_skipped).
    """
    query = """
        UNWIND $refs AS ref
        MATCH (from:Verse {id: ref.from_id})
        MATCH (to:Verse {id: ref.to_id})
        MERGE (from)-[r:CROSS_REFERENCES]->(to)
        ON CREATE SET
            r.sources = [ref.source],
            r.votes = CASE WHEN ref.votes IS NOT NULL THEN ref.votes ELSE null END,
            r.passage_group = ref.passage_group
        ON MATCH SET
            r.sources = CASE
                WHEN ref.source IN r.sources THEN r.sources
                ELSE r.sources + [ref.source]
            END
        RETURN count(r) AS created
    """

    with connection.session() as session:
        result = session.run(query, refs=batch)
        record = result.single()
        created = record["created"] if record else 0

    skipped = len(batch) - created
    return created, skipped