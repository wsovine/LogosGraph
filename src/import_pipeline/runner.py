"""Import pipeline orchestration."""

import logging
import time

from src.data.downloader import download_all
from src.data.cpdv_parser import parse_cpdv
from src.data.tsk_parser import parse_tsk_crossrefs
from src.data.haydock_parser import parse_haydock_crossrefs
from src.data.catechism_parser import parse_catechism_paragraphs, parse_catechism_internal_refs
from src.data.catechism_html_parser import parse_catechism_html_pages
from src.data.book_mapping import load_book_metadata
from src.db.connection import get_connection
from src.db.schema import setup_schema, drop_all_data
from src.import_pipeline.verse_importer import import_verses
from src.import_pipeline.crossref_importer import import_crossrefs
from src.import_pipeline.book_importer import (
    import_books,
    import_book_verse_relationships,
    prepare_books_for_import,
)
from src.import_pipeline.catechism_importer import (
    import_catechism_paragraphs,
    import_catechism_internal_refs,
    prepare_scripture_refs,
    import_catechism_scripture_refs,
    prepare_external_refs,
    import_external_documents,
    import_catechism_external_refs,
)
from src.data.typology_parser import (
    parse_all_types,
    parse_seed_prefigures,
    parse_approved_prefigures,
    parse_seed_memberships,
    parse_approved_memberships,
    parse_teaches,
)
from src.data.typology_schemas import validate_all_seed_files
from src.import_pipeline.typology_importer import (
    import_types,
    import_prefigures,
    import_verse_memberships,
    import_teaches,
)

logger = logging.getLogger(__name__)


def run_full_import(
    skip_download: bool = False,
    drop_existing: bool = False,
) -> dict:
    """Run the complete import pipeline.

    Args:
        skip_download: If True, skip downloading data files.
        drop_existing: If True, drop all existing data before import.

    Returns:
        Dictionary with import statistics.
    """
    stats = {}
    start_time = time.time()

    print("\n" + "=" * 60)
    print("LogosGraph Import Pipeline")
    print("=" * 60)

    # Step 1: Download data
    if not skip_download:
        print("\n📥 Step 1: Downloading data files...")
        step_start = time.time()
        download_all()
        stats["download_time"] = time.time() - step_start
        print(f"   ✓ Download complete ({stats['download_time']:.1f}s)")
    else:
        print("\n📥 Step 1: Skipping download (--skip-download)")

    # Step 2: Connect to Neo4j
    print("\n🔌 Step 2: Connecting to Neo4j...")
    connection = get_connection()
    connection.connect()
    connection.verify()
    print("   ✓ Connected")

    # Step 3: Setup schema (and optionally drop existing data)
    print("\n📋 Step 3: Setting up schema...")
    if drop_existing:
        print("   ⚠️  Dropping existing data...")
        drop_all_data(connection)
    setup_schema(connection)
    print("   ✓ Schema ready")

    # Step 4: Import books
    print("\n📚 Step 4: Importing books...")
    step_start = time.time()
    book_metadata = load_book_metadata()
    books = prepare_books_for_import(book_metadata)
    book_count = import_books(books, connection)
    stats["book_count"] = book_count
    stats["book_import_time"] = time.time() - step_start
    print(f"   ✓ Imported {book_count} books ({stats['book_import_time']:.1f}s)")

    # Step 5: Import verses
    print("\n📖 Step 5: Importing verses...")
    step_start = time.time()
    verses = parse_cpdv()
    verse_count = import_verses(verses, connection)
    stats["verse_count"] = verse_count
    stats["verse_import_time"] = time.time() - step_start
    print(f"   ✓ Imported {verse_count:,} verses ({stats['verse_import_time']:.1f}s)")

    # Step 6: Link books to verses
    print("\n🔗 Step 6: Linking books to verses...")
    step_start = time.time()
    book_verse_links = import_book_verse_relationships(connection)
    stats["book_verse_links"] = book_verse_links
    stats["book_verse_link_time"] = time.time() - step_start
    print(f"   ✓ Created {book_verse_links:,} Book→Verse links ({stats['book_verse_link_time']:.1f}s)")

    # Step 7: Import TSK cross-references
    print("\n🔗 Step 7: Importing TSK cross-references...")
    step_start = time.time()
    crossrefs = parse_tsk_crossrefs()
    tsk_created, tsk_skipped = import_crossrefs(crossrefs, connection)
    stats["tsk_created"] = tsk_created
    stats["tsk_skipped"] = tsk_skipped
    stats["tsk_import_time"] = time.time() - step_start
    print(f"   ✓ Created {tsk_created:,} edges ({stats['tsk_import_time']:.1f}s)")
    if tsk_skipped > 0:
        print(f"   ⚠️  Skipped {tsk_skipped:,} (missing verse references)")

    # Step 8: Import Haydock cross-references
    print("\n🔗 Step 8: Importing Haydock cross-references...")
    step_start = time.time()
    haydock_refs = parse_haydock_crossrefs()
    haydock_created, haydock_skipped = import_crossrefs(haydock_refs, connection)
    stats["haydock_created"] = haydock_created
    stats["haydock_skipped"] = haydock_skipped
    stats["haydock_import_time"] = time.time() - step_start
    print(f"   ✓ Created/updated {haydock_created:,} edges ({stats['haydock_import_time']:.1f}s)")
    if haydock_skipped > 0:
        print(f"   ⚠️  Skipped {haydock_skipped:,} (missing verse references)")

    # Step 9: Import CCC paragraphs
    print("\n📜 Step 9: Importing CCC paragraphs...")
    step_start = time.time()
    paragraphs = parse_catechism_paragraphs()
    ccc_para_count = import_catechism_paragraphs(paragraphs, connection)
    stats["ccc_paragraphs"] = ccc_para_count
    stats["ccc_para_import_time"] = time.time() - step_start
    print(f"   ✓ Imported {ccc_para_count:,} paragraphs ({stats['ccc_para_import_time']:.1f}s)")

    # Step 10: Import CCC internal cross-references
    print("\n🔗 Step 10: Importing CCC internal cross-references...")
    step_start = time.time()
    internal_refs = parse_catechism_internal_refs()
    ccc_internal_created, ccc_internal_skipped = import_catechism_internal_refs(internal_refs, connection)
    stats["ccc_internal_created"] = ccc_internal_created
    stats["ccc_internal_skipped"] = ccc_internal_skipped
    stats["ccc_internal_import_time"] = time.time() - step_start
    print(f"   ✓ Created {ccc_internal_created:,} edges ({stats['ccc_internal_import_time']:.1f}s)")
    if ccc_internal_skipped > 0:
        print(f"   ⚠️  Skipped {ccc_internal_skipped:,} (missing paragraph references)")

    # Step 11: Import CCC→Verse citations
    print("\n📖 Step 11: Importing CCC Scripture citations...")
    step_start = time.time()
    html_citations = list(parse_catechism_html_pages())
    scripture_refs = list(prepare_scripture_refs(html_citations))
    ccc_scripture_created, ccc_scripture_skipped = import_catechism_scripture_refs(scripture_refs, connection)
    stats["ccc_scripture_created"] = ccc_scripture_created
    stats["ccc_scripture_skipped"] = ccc_scripture_skipped
    stats["ccc_scripture_import_time"] = time.time() - step_start
    print(f"   ✓ Created {ccc_scripture_created:,} edges ({stats['ccc_scripture_import_time']:.1f}s)")
    if ccc_scripture_skipped > 0:
        print(f"   ⚠️  Skipped {ccc_scripture_skipped:,} (missing verse references)")

    # Step 12: Import external documents
    print("\n📚 Step 12: Importing external document references...")
    step_start = time.time()
    external_refs = list(prepare_external_refs(html_citations))
    ext_doc_count = import_external_documents(external_refs, connection)
    ccc_external_created, ccc_external_skipped = import_catechism_external_refs(external_refs, connection)
    stats["external_docs"] = ext_doc_count
    stats["ccc_external_created"] = ccc_external_created
    stats["ccc_external_skipped"] = ccc_external_skipped
    stats["ccc_external_import_time"] = time.time() - step_start
    print(f"   ✓ Created {ext_doc_count:,} document nodes, {ccc_external_created:,} edges ({stats['ccc_external_import_time']:.1f}s)")
    if ccc_external_skipped > 0:
        print(f"   ⚠️  Skipped {ccc_external_skipped:,} (missing references)")

    # Step 13: Import biblical typology (seed + reviewed)
    print("\n⛪ Step 13: Importing biblical typology...")
    step_start = time.time()
    seed_valid, seed_errors = validate_all_seed_files()
    if not seed_valid:
        raise ValueError(f"Typology seed files failed validation: {seed_errors}")

    type_count = import_types(parse_all_types(), connection)
    prefigures = list(parse_seed_prefigures()) + list(parse_approved_prefigures())
    prefigures_created, prefigures_skipped = import_prefigures(prefigures, connection)
    memberships = list(parse_seed_memberships()) + list(parse_approved_memberships())
    member_created, member_skipped = import_verse_memberships(memberships, connection)
    teaches_created, teaches_skipped = import_teaches(list(parse_teaches()), connection)

    stats["type_count"] = type_count
    stats["prefigures_created"] = prefigures_created
    stats["prefigures_skipped"] = prefigures_skipped
    stats["member_of_created"] = member_created
    stats["member_of_skipped"] = member_skipped
    stats["teaches_created"] = teaches_created
    stats["teaches_skipped"] = teaches_skipped
    stats["typology_import_time"] = time.time() - step_start
    print(
        f"   ✓ {type_count} Type nodes, {prefigures_created:,} PREFIGURES, "
        f"{member_created:,} MEMBER_OF, {teaches_created:,} TEACHES "
        f"({stats['typology_import_time']:.1f}s)"
    )
    if prefigures_skipped or member_skipped or teaches_skipped:
        print(
            f"   ⚠️  Skipped (missing endpoints): "
            f"{prefigures_skipped} PREFIGURES, {member_skipped} MEMBER_OF, "
            f"{teaches_skipped} TEACHES"
        )

    # Cleanup
    connection.close()

    # Summary
    total_time = time.time() - start_time
    stats["total_time"] = total_time
    total_crossrefs = tsk_created + haydock_created
    total_ccc_edges = ccc_internal_created + ccc_scripture_created + ccc_external_created

    print("\n" + "=" * 60)
    print("Import Complete!")
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   • Books imported: {book_count}")
    print(f"   • Verses imported: {verse_count:,}")
    print(f"   • Book→Verse links: {book_verse_links:,}")
    print(f"   • TSK cross-references: {tsk_created:,}")
    print(f"   • Haydock cross-references: {haydock_created:,}")
    print(f"   • CCC paragraphs: {ccc_para_count:,}")
    print(f"   • CCC internal refs: {ccc_internal_created:,}")
    print(f"   • CCC→Scripture citations: {ccc_scripture_created:,}")
    print(f"   • External documents: {ext_doc_count:,}")
    print(f"   • CCC→ExtDoc citations: {ccc_external_created:,}")
    print(f"   • Type nodes: {type_count:,}")
    print(f"   • PREFIGURES edges: {prefigures_created:,}")
    print(f"   • MEMBER_OF edges: {member_created:,}")
    print(f"   • TEACHES edges: {teaches_created:,}")
    print(f"   • Total cross-ref edges: {total_crossrefs:,}")
    print(f"   • Total CCC edges: {total_ccc_edges:,}")
    print(f"   • Total time: {total_time:.1f}s")
    print(f"\n🌐 Open Neo4j Browser at http://localhost:7474")
    print("=" * 60 + "\n")

    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_full_import()