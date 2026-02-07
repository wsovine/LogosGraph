"""Import Catechism of the Catholic Church into Neo4j."""

import logging
from typing import Generator, Iterable

from tqdm import tqdm

from src.config import settings
from src.db.connection import Neo4jConnection, get_connection

logger = logging.getLogger(__name__)


def prepare_scripture_refs(
    html_citations: Iterable[dict],
) -> Generator[dict, None, None]:
    """Transform HTML citations into scripture reference dicts for import.

    Parses citation text from HTML footnotes and yields formatted refs
    suitable for import_catechism_scripture_refs().

    Args:
        html_citations: Iterable of dicts with keys: paragraph, footnote, citation_text

    Yields:
        Dicts with keys: from_id, to_id, footnote, source, passage_group
    """
    from src.data.catechism_citation_parser import parse_footnote_citations

    citations_list = list(html_citations)
    logger.info(f"Parsing {len(citations_list)} HTML citations for Scripture refs")

    parsed_count = 0
    for parsed in parse_footnote_citations(citations_list):
        parsed_count += 1
        yield {
            "from_id": f"CCC-{parsed['paragraph']}",
            "to_id": parsed["verse_id"],
            "footnote": None,  # footnote number not preserved in parse_footnote_citations
            "source": "CCC-HTML",
            "passage_group": parsed.get("passage_group"),
        }

    logger.info(f"Prepared {parsed_count} Scripture citations for import")


def import_catechism_paragraphs(
    paragraphs: Iterable[dict],
    connection: Neo4jConnection | None = None,
    batch_size: int | None = None,
) -> int:
    """Import CatechismParagraph nodes into Neo4j using batch processing.

    Args:
        paragraphs: Iterable of paragraph dictionaries with keys:
            id, paragraph, text
        connection: Neo4j connection. Defaults to singleton connection.
        batch_size: Number of nodes per batch. Defaults to settings.BATCH_SIZE.

    Returns:
        Total number of paragraphs imported.
    """
    if connection is None:
        connection = get_connection()

    if batch_size is None:
        batch_size = settings.BATCH_SIZE

    batch: list[dict] = []
    total_imported = 0

    # Convert to list to get count for progress bar
    paragraphs_list = list(paragraphs)
    total_paragraphs = len(paragraphs_list)

    logger.info(f"Importing {total_paragraphs} CatechismParagraph nodes in batches of {batch_size}")

    with tqdm(total=total_paragraphs, desc="Importing CCC paragraphs") as pbar:
        for para in paragraphs_list:
            batch.append(para)

            if len(batch) >= batch_size:
                _import_paragraph_batch(connection, batch)
                total_imported += len(batch)
                pbar.update(len(batch))
                batch = []

        # Import remaining paragraphs
        if batch:
            _import_paragraph_batch(connection, batch)
            total_imported += len(batch)
            pbar.update(len(batch))

    logger.info(f"Imported {total_imported} CatechismParagraph nodes")
    return total_imported


def _import_paragraph_batch(connection: Neo4jConnection, batch: list[dict]) -> None:
    """Import a batch of CatechismParagraph nodes using UNWIND.

    Args:
        connection: Neo4j connection.
        batch: List of paragraph dictionaries.
    """
    query = """
        UNWIND $paragraphs AS p
        CREATE (c:CatechismParagraph {
            id: p.id,
            paragraph: p.paragraph,
            text: p.text
        })
    """

    with connection.session() as session:
        session.run(query, paragraphs=batch)


def import_catechism_internal_refs(
    refs: Iterable[dict],
    connection: Neo4jConnection | None = None,
    batch_size: int | None = None,
) -> tuple[int, int]:
    """Import CCC internal cross-references into Neo4j.

    Creates CROSS_REFERENCES edges between CatechismParagraph nodes.
    Uses MERGE to handle duplicates. Only creates edges when both
    source and target paragraphs exist.

    Args:
        refs: Iterable of reference dictionaries with keys:
            from_id, to_id, source, passage_group (optional)
        connection: Neo4j connection. Defaults to singleton connection.
        batch_size: Number of edges per batch. Defaults to settings.BATCH_SIZE * 2.

    Returns:
        Tuple of (edges_created, edges_skipped).
    """
    if connection is None:
        connection = get_connection()

    if batch_size is None:
        batch_size = settings.BATCH_SIZE * 2

    batch: list[dict] = []
    total_created = 0
    total_skipped = 0

    # Convert to list to get count for progress bar
    refs_list = list(refs)
    total_refs = len(refs_list)

    logger.info(f"Importing {total_refs} CCC internal cross-references in batches of {batch_size}")

    with tqdm(total=total_refs, desc="Importing CCC internal refs") as pbar:
        for ref in refs_list:
            batch.append(ref)

            if len(batch) >= batch_size:
                created, skipped = _import_internal_ref_batch(connection, batch)
                total_created += created
                total_skipped += skipped
                pbar.update(len(batch))
                batch = []

        # Import remaining refs
        if batch:
            created, skipped = _import_internal_ref_batch(connection, batch)
            total_created += created
            total_skipped += skipped
            pbar.update(len(batch))

    logger.info(f"Created {total_created} CCC internal edges, skipped {total_skipped}")
    return total_created, total_skipped


def _import_internal_ref_batch(connection: Neo4jConnection, batch: list[dict]) -> tuple[int, int]:
    """Import a batch of internal cross-references using UNWIND and MERGE.

    Args:
        connection: Neo4j connection.
        batch: List of reference dictionaries.

    Returns:
        Tuple of (edges_created, edges_skipped).
    """
    query = """
        UNWIND $refs AS ref
        MATCH (from:CatechismParagraph {id: ref.from_id})
        MATCH (to:CatechismParagraph {id: ref.to_id})
        MERGE (from)-[r:CROSS_REFERENCES]->(to)
        ON CREATE SET
            r.source = ref.source,
            r.passage_group = ref.passage_group
        RETURN count(r) AS created
    """

    with connection.session() as session:
        result = session.run(query, refs=batch)
        record = result.single()
        created = record["created"] if record else 0

    skipped = len(batch) - created
    return created, skipped


def import_catechism_scripture_refs(
    refs: Iterable[dict],
    connection: Neo4jConnection | None = None,
    batch_size: int | None = None,
) -> tuple[int, int]:
    """Import CCC Scripture citations into Neo4j.

    Creates CITES edges from CatechismParagraph to Verse nodes.
    Uses MERGE to handle duplicates. Only creates edges when both
    source paragraph and target verse exist.

    Args:
        refs: Iterable of citation dictionaries with keys:
            from_id, to_id, footnote, source, passage_group (optional)
        connection: Neo4j connection. Defaults to singleton connection.
        batch_size: Number of edges per batch. Defaults to settings.BATCH_SIZE * 2.

    Returns:
        Tuple of (edges_created, edges_skipped).
    """
    if connection is None:
        connection = get_connection()

    if batch_size is None:
        batch_size = settings.BATCH_SIZE * 2

    batch: list[dict] = []
    total_created = 0
    total_skipped = 0

    # Convert to list to get count for progress bar
    refs_list = list(refs)
    total_refs = len(refs_list)

    logger.info(f"Importing {total_refs} CCC Scripture citations in batches of {batch_size}")

    with tqdm(total=total_refs, desc="Importing CCC Scripture refs") as pbar:
        for ref in refs_list:
            batch.append(ref)

            if len(batch) >= batch_size:
                created, skipped = _import_scripture_ref_batch(connection, batch)
                total_created += created
                total_skipped += skipped
                pbar.update(len(batch))
                batch = []

        # Import remaining refs
        if batch:
            created, skipped = _import_scripture_ref_batch(connection, batch)
            total_created += created
            total_skipped += skipped
            pbar.update(len(batch))

    logger.info(f"Created {total_created} CCC->Verse CITES edges, skipped {total_skipped}")
    return total_created, total_skipped


def _import_scripture_ref_batch(connection: Neo4jConnection, batch: list[dict]) -> tuple[int, int]:
    """Import a batch of Scripture citations using UNWIND and MERGE.

    Args:
        connection: Neo4j connection.
        batch: List of citation dictionaries.

    Returns:
        Tuple of (edges_created, edges_skipped).
    """
    query = """
        UNWIND $refs AS ref
        MATCH (ccc:CatechismParagraph {id: ref.from_id})
        MATCH (v:Verse {id: ref.to_id})
        MERGE (ccc)-[r:CITES]->(v)
        ON CREATE SET
            r.footnote = ref.footnote,
            r.source = ref.source,
            r.passage_group = ref.passage_group
        RETURN count(r) AS created
    """

    with connection.session() as session:
        result = session.run(query, refs=batch)
        record = result.single()
        created = record["created"] if record else 0

    skipped = len(batch) - created
    return created, skipped


def prepare_external_refs(
    html_citations: Iterable[dict],
) -> Generator[dict, None, None]:
    """Transform HTML citations into external document refs for import.

    Args:
        html_citations: Iterable of dicts with keys: paragraph, footnote, citation_text

    Yields:
        Dicts with keys: from_id, doc_id, abbreviation, reference, doc_type, title
    """
    from src.data.catechism_citation_parser import parse_external_footnote_citations

    citations_list = list(html_citations)
    logger.info(f"Parsing {len(citations_list)} HTML citations for external doc refs")

    parsed_count = 0
    for parsed in parse_external_footnote_citations(citations_list):
        parsed_count += 1
        # Create a unique doc_id from abbreviation + reference
        doc_id = f"{parsed['abbreviation']}-{parsed['reference']}"
        yield {
            "from_id": f"CCC-{parsed['paragraph']}",
            "doc_id": doc_id,
            "abbreviation": parsed["abbreviation"],
            "reference": parsed["reference"],
            "doc_type": parsed["doc_type"],
            "title": parsed["title"],
        }

    logger.info(f"Prepared {parsed_count} external document citations for import")


def import_external_documents(
    refs: Iterable[dict],
    connection: Neo4jConnection | None = None,
    batch_size: int | None = None,
) -> int:
    """Import ExternalDocument nodes into Neo4j.

    Creates unique ExternalDocument nodes using MERGE. Each document
    is identified by its abbreviation + reference (e.g., "DS-150").

    Args:
        refs: Iterable of dicts with keys: doc_id, abbreviation, reference, doc_type, title
        connection: Neo4j connection. Defaults to singleton connection.
        batch_size: Number of nodes per batch. Defaults to settings.BATCH_SIZE.

    Returns:
        Total number of unique documents created/merged.
    """
    if connection is None:
        connection = get_connection()

    if batch_size is None:
        batch_size = settings.BATCH_SIZE

    # Deduplicate documents (same doc may be cited multiple times)
    seen_docs: dict[str, dict] = {}
    for ref in refs:
        doc_id = ref["doc_id"]
        if doc_id not in seen_docs:
            seen_docs[doc_id] = {
                "id": doc_id,
                "abbreviation": ref["abbreviation"],
                "reference": ref["reference"],
                "doc_type": ref["doc_type"],
                "title": ref["title"],
                "imported": False,
            }

    docs_list = list(seen_docs.values())
    total_docs = len(docs_list)
    logger.info(f"Importing {total_docs} unique ExternalDocument nodes in batches of {batch_size}")

    batch: list[dict] = []
    total_imported = 0

    with tqdm(total=total_docs, desc="Importing ExternalDocuments") as pbar:
        for doc in docs_list:
            batch.append(doc)

            if len(batch) >= batch_size:
                _import_external_doc_batch(connection, batch)
                total_imported += len(batch)
                pbar.update(len(batch))
                batch = []

        if batch:
            _import_external_doc_batch(connection, batch)
            total_imported += len(batch)
            pbar.update(len(batch))

    logger.info(f"Imported {total_imported} ExternalDocument nodes")
    return total_imported


def _import_external_doc_batch(connection: Neo4jConnection, batch: list[dict]) -> None:
    """Import a batch of ExternalDocument nodes using UNWIND and MERGE."""
    query = """
        UNWIND $docs AS doc
        MERGE (d:ExternalDocument {id: doc.id})
        ON CREATE SET
            d.abbreviation = doc.abbreviation,
            d.reference = doc.reference,
            d.doc_type = doc.doc_type,
            d.title = doc.title,
            d.imported = doc.imported
    """

    with connection.session() as session:
        session.run(query, docs=batch)


def import_catechism_external_refs(
    refs: Iterable[dict],
    connection: Neo4jConnection | None = None,
    batch_size: int | None = None,
) -> tuple[int, int]:
    """Import CCC external document citations into Neo4j.

    Creates CITES edges from CatechismParagraph to ExternalDocument nodes.

    Args:
        refs: Iterable of dicts with keys: from_id, doc_id
        connection: Neo4j connection. Defaults to singleton connection.
        batch_size: Number of edges per batch. Defaults to settings.BATCH_SIZE * 2.

    Returns:
        Tuple of (edges_created, edges_skipped).
    """
    if connection is None:
        connection = get_connection()

    if batch_size is None:
        batch_size = settings.BATCH_SIZE * 2

    batch: list[dict] = []
    total_created = 0
    total_skipped = 0

    refs_list = list(refs)
    total_refs = len(refs_list)

    logger.info(f"Importing {total_refs} CCC->ExternalDocument CITES edges in batches of {batch_size}")

    with tqdm(total=total_refs, desc="Importing CCC external refs") as pbar:
        for ref in refs_list:
            batch.append(ref)

            if len(batch) >= batch_size:
                created, skipped = _import_external_ref_batch(connection, batch)
                total_created += created
                total_skipped += skipped
                pbar.update(len(batch))
                batch = []

        if batch:
            created, skipped = _import_external_ref_batch(connection, batch)
            total_created += created
            total_skipped += skipped
            pbar.update(len(batch))

    logger.info(f"Created {total_created} CCC->ExternalDocument CITES edges, skipped {total_skipped}")
    return total_created, total_skipped


def _import_external_ref_batch(connection: Neo4jConnection, batch: list[dict]) -> tuple[int, int]:
    """Import a batch of external document citations using UNWIND and MERGE."""
    query = """
        UNWIND $refs AS ref
        MATCH (ccc:CatechismParagraph {id: ref.from_id})
        MATCH (doc:ExternalDocument {id: ref.doc_id})
        MERGE (ccc)-[r:CITES]->(doc)
        ON CREATE SET r.source = "CCC-HTML"
        RETURN count(r) AS created
    """

    with connection.session() as session:
        result = session.run(query, refs=batch)
        record = result.single()
        created = record["created"] if record else 0

    skipped = len(batch) - created
    return created, skipped