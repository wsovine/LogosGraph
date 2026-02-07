"""Neo4j schema setup - constraints and indexes."""

import logging

from src.db.connection import Neo4jConnection, get_connection

logger = logging.getLogger(__name__)


def setup_schema(connection: Neo4jConnection | None = None) -> None:
    """Create database constraints and indexes.

    All statements use IF NOT EXISTS for idempotency.

    Args:
        connection: Neo4j connection. Defaults to singleton connection.
    """
    if connection is None:
        connection = get_connection()

    with connection.session() as session:
        # Unique constraint on verse ID
        logger.info("Creating unique constraint on Verse.id")
        session.run("""
            CREATE CONSTRAINT verse_id_unique IF NOT EXISTS
            FOR (v:Verse) REQUIRE v.id IS UNIQUE
        """)

        # Index for book queries
        logger.info("Creating index on Verse.book_id")
        session.run("""
            CREATE INDEX verse_book_idx IF NOT EXISTS
            FOR (v:Verse) ON (v.book_id)
        """)

        # Composite index for chapter queries
        logger.info("Creating index on Verse.book_id, Verse.chapter")
        session.run("""
            CREATE INDEX verse_chapter_idx IF NOT EXISTS
            FOR (v:Verse) ON (v.book_id, v.chapter)
        """)

        # CatechismParagraph constraints and indexes
        logger.info("Creating unique constraint on CatechismParagraph.id")
        session.run("""
            CREATE CONSTRAINT ccc_id_unique IF NOT EXISTS
            FOR (c:CatechismParagraph) REQUIRE c.id IS UNIQUE
        """)

        logger.info("Creating index on CatechismParagraph.paragraph")
        session.run("""
            CREATE INDEX ccc_paragraph_idx IF NOT EXISTS
            FOR (c:CatechismParagraph) ON (c.paragraph)
        """)

        # ExternalDocument constraint
        logger.info("Creating unique constraint on ExternalDocument.id")
        session.run("""
            CREATE CONSTRAINT external_doc_id_unique IF NOT EXISTS
            FOR (d:ExternalDocument) REQUIRE d.id IS UNIQUE
        """)

        # Writing constraint (covers all writing types: Book, Encyclical, etc.)
        logger.info("Creating unique constraint on Writing.id")
        session.run("""
            CREATE CONSTRAINT writing_id_unique IF NOT EXISTS
            FOR (w:Writing) REQUIRE w.id IS UNIQUE
        """)

        # Book-specific indexes
        logger.info("Creating index on Book.testament")
        session.run("""
            CREATE INDEX book_testament_idx IF NOT EXISTS
            FOR (b:Book) ON (b.testament)
        """)

        logger.info("Creating index on Book.order")
        session.run("""
            CREATE INDEX book_order_idx IF NOT EXISTS
            FOR (b:Book) ON (b.order)
        """)

        logger.info("Schema setup complete")


def drop_all_data(connection: Neo4jConnection | None = None) -> None:
    """Drop all nodes and relationships. Use with caution!

    Args:
        connection: Neo4j connection. Defaults to singleton connection.
    """
    if connection is None:
        connection = get_connection()

    with connection.session() as session:
        logger.warning("Dropping all nodes and relationships")
        session.run("MATCH (n) DETACH DELETE n")
        logger.info("All data dropped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    conn = get_connection()
    conn.connect()
    conn.verify()
    setup_schema(conn)
    conn.close()