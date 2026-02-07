"""Import books into Neo4j with :Writing:Book labels."""

import logging
from typing import Iterable

from tqdm import tqdm

from src.config import settings
from src.db.connection import Neo4jConnection, get_connection

logger = logging.getLogger(__name__)


def import_books(
    books: Iterable[dict],
    connection: Neo4jConnection | None = None,
    batch_size: int | None = None,
) -> int:
    """Import Book nodes into Neo4j using batch processing.

    Creates nodes with both :Writing and :Book labels for the multi-label pattern.

    Args:
        books: Iterable of book dictionaries with keys:
            id, name, order, testament, isDeuterocanonical,
            dateWrittenStart, dateWrittenEnd, dateEventsStart, dateEventsEnd
        connection: Neo4j connection. Defaults to singleton connection.
        batch_size: Number of books per batch. Defaults to settings.BATCH_SIZE.

    Returns:
        Total number of books imported.
    """
    if connection is None:
        connection = get_connection()

    if batch_size is None:
        batch_size = settings.BATCH_SIZE

    batch: list[dict] = []
    total_imported = 0

    # Convert to list to get count for progress bar
    books_list = list(books)
    total_books = len(books_list)

    logger.info(f"Importing {total_books} books in batches of {batch_size}")

    with tqdm(total=total_books, desc="Importing books") as pbar:
        for book in books_list:
            batch.append(book)

            if len(batch) >= batch_size:
                _import_book_batch(connection, batch)
                total_imported += len(batch)
                pbar.update(len(batch))
                batch = []

        # Import remaining books
        if batch:
            _import_book_batch(connection, batch)
            total_imported += len(batch)
            pbar.update(len(batch))

    logger.info(f"Imported {total_imported} books")
    return total_imported


def _import_book_batch(connection: Neo4jConnection, batch: list[dict]) -> None:
    """Import a batch of books using UNWIND.

    Args:
        connection: Neo4j connection.
        batch: List of book dictionaries.
    """
    query = """
        UNWIND $books AS book
        CREATE (b:Writing:Book {
            id: book.id,
            name: book.name,
            order: book.order,
            testament: book.testament,
            isDeuterocanonical: book.isDeuterocanonical,
            dateWrittenStart: book.dateWrittenStart,
            dateWrittenEnd: book.dateWrittenEnd,
            dateEventsStart: book.dateEventsStart,
            dateEventsEnd: book.dateEventsEnd
        })
    """

    with connection.session() as session:
        session.run(query, books=batch)


def import_book_verse_relationships(
    connection: Neo4jConnection | None = None,
) -> int:
    """Create CONTAINS relationships from Book to Verse nodes.

    Links each Book node to all Verse nodes that have a matching book_id.

    Args:
        connection: Neo4j connection. Defaults to singleton connection.

    Returns:
        Total number of relationships created.
    """
    if connection is None:
        connection = get_connection()

    logger.info("Creating Book-[:CONTAINS]->Verse relationships")

    query = """
        MATCH (b:Book)
        MATCH (v:Verse)
        WHERE v.book_id = b.id
        CREATE (b)-[:CONTAINS]->(v)
        RETURN count(*) AS relationships_created
    """

    with connection.session() as session:
        result = session.run(query)
        record = result.single()
        relationships_created = record["relationships_created"] if record else 0

    logger.info(f"Created {relationships_created:,} Book->Verse relationships")
    return relationships_created


def prepare_books_for_import(metadata: dict[str, dict]) -> list[dict]:
    """Prepare book metadata for import.

    Transforms the metadata dictionary into a list of book dictionaries
    ready for import_books().

    Args:
        metadata: Dictionary from load_book_metadata().

    Returns:
        List of book dictionaries with id added.
    """
    books = []
    for book_id, book_data in metadata.items():
        book = {"id": book_id, **book_data}
        books.append(book)

    # Sort by order for consistent import
    books.sort(key=lambda b: b["order"])
    return books
