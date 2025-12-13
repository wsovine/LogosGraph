"""Import pipeline orchestration."""

import logging
import time

from src.data.downloader import download_all
from src.data.cpdv_parser import parse_cpdv
from src.data.tsk_parser import parse_tsk_crossrefs
from src.data.haydock_parser import parse_haydock_crossrefs
from src.db.connection import get_connection
from src.db.schema import setup_schema, drop_all_data
from src.import_pipeline.verse_importer import import_verses
from src.import_pipeline.crossref_importer import import_crossrefs

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

    # Step 4: Import verses
    print("\n📖 Step 4: Importing verses...")
    step_start = time.time()
    verses = parse_cpdv()
    verse_count = import_verses(verses, connection)
    stats["verse_count"] = verse_count
    stats["verse_import_time"] = time.time() - step_start
    print(f"   ✓ Imported {verse_count:,} verses ({stats['verse_import_time']:.1f}s)")

    # Step 5: Import TSK cross-references
    print("\n🔗 Step 5: Importing TSK cross-references...")
    step_start = time.time()
    crossrefs = parse_tsk_crossrefs()
    tsk_created, tsk_skipped = import_crossrefs(crossrefs, connection)
    stats["tsk_created"] = tsk_created
    stats["tsk_skipped"] = tsk_skipped
    stats["tsk_import_time"] = time.time() - step_start
    print(f"   ✓ Created {tsk_created:,} edges ({stats['tsk_import_time']:.1f}s)")
    if tsk_skipped > 0:
        print(f"   ⚠️  Skipped {tsk_skipped:,} (missing verse references)")

    # Step 6: Import Haydock cross-references
    print("\n🔗 Step 6: Importing Haydock cross-references...")
    step_start = time.time()
    haydock_refs = parse_haydock_crossrefs()
    haydock_created, haydock_skipped = import_crossrefs(haydock_refs, connection)
    stats["haydock_created"] = haydock_created
    stats["haydock_skipped"] = haydock_skipped
    stats["haydock_import_time"] = time.time() - step_start
    print(f"   ✓ Created/updated {haydock_created:,} edges ({stats['haydock_import_time']:.1f}s)")
    if haydock_skipped > 0:
        print(f"   ⚠️  Skipped {haydock_skipped:,} (missing verse references)")

    # Cleanup
    connection.close()

    # Summary
    total_time = time.time() - start_time
    stats["total_time"] = total_time
    total_edges = tsk_created + haydock_created

    print("\n" + "=" * 60)
    print("Import Complete!")
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   • Verses imported: {verse_count:,}")
    print(f"   • TSK cross-references: {tsk_created:,}")
    print(f"   • Haydock cross-references: {haydock_created:,}")
    print(f"   • Total edges: {total_edges:,}")
    print(f"   • Total time: {total_time:.1f}s")
    print(f"\n🌐 Open Neo4j Browser at http://localhost:7474")
    print("=" * 60 + "\n")

    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_full_import()