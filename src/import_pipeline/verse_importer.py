"""Import verses into Neo4j."""

import logging
from typing import Iterable

from tqdm import tqdm

from src.config import settings
from src.db.connection import Neo4jConnection, get_connection

logger = logging.getLogger(__name__)


def import_verses(
    verses: Iterable[dict],
    connection: Neo4jConnection | None = None,
    batch_size: int | None = None,
) -> int:
    """Import verses into Neo4j using batch processing.

    Args:
        verses: Iterable of verse dictionaries with keys:
            id, book_id, book_name, chapter, verse, text
        connection: Neo4j connection. Defaults to singleton connection.
        batch_size: Number of verses per batch. Defaults to settings.BATCH_SIZE.

    Returns:
        Total number of verses imported.
    """
    if connection is None:
        connection = get_connection()

    if batch_size is None:
        batch_size = settings.BATCH_SIZE

    # Collect verses into batches
    batch: list[dict] = []
    total_imported = 0

    # Convert to list to get count for progress bar
    verses_list = list(verses)
    total_verses = len(verses_list)

    logger.info(f"Importing {total_verses} verses in batches of {batch_size}")

    with tqdm(total=total_verses, desc="Importing verses") as pbar:
        for verse in verses_list:
            batch.append(verse)

            if len(batch) >= batch_size:
                _import_batch(connection, batch)
                total_imported += len(batch)
                pbar.update(len(batch))
                batch = []

        # Import remaining verses
        if batch:
            _import_batch(connection, batch)
            total_imported += len(batch)
            pbar.update(len(batch))

    logger.info(f"Imported {total_imported} verses")
    return total_imported


def _import_batch(connection: Neo4jConnection, batch: list[dict]) -> None:
    """Import a batch of verses using UNWIND.

    Args:
        connection: Neo4j connection.
        batch: List of verse dictionaries.
    """
    query = """
        UNWIND $verses AS verse
        CREATE (v:Verse {
            id: verse.id,
            book_id: verse.book_id,
            book_name: verse.book_name,
            chapter: verse.chapter,
            verse: verse.verse,
            text: verse.text
        })
    """

    with connection.session() as session:
        session.run(query, verses=batch)