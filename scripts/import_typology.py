#!/usr/bin/env python3
"""CLI script to import biblical typology into Neo4j.

Loads Type nodes and PREFIGURES / MEMBER_OF / TEACHES relationships from the
curated CCC seed files and the reviewed Haydock extractions. Can run the whole
typology import or individual steps, and can restrict to seed-only or
reviewed-only sources for incremental loads.

Examples:
    python scripts/import_typology.py                 # import everything
    python scripts/import_typology.py --seed-only     # only curated CCC seed data
    python scripts/import_typology.py --types --prefigures   # only those steps
    python scripts/import_typology.py --reviewed-only -v
"""

import argparse
import logging
import sys
import time

from src.data.typology_parser import (
    parse_all_types,
    parse_seed_types,
    parse_reviewed_types,
    parse_seed_prefigures,
    parse_approved_prefigures,
    parse_seed_memberships,
    parse_approved_memberships,
    parse_teaches,
)
from src.data.typology_schemas import validate_all_seed_files
from src.db.connection import get_connection
from src.db.schema import setup_schema
from src.import_pipeline.typology_importer import (
    import_types,
    import_prefigures,
    import_verse_memberships,
    import_teaches,
)


def main():
    parser = argparse.ArgumentParser(
        description="Import biblical typology (Type nodes + relationships) into Neo4j"
    )
    # Step selection (if none given, all steps run)
    parser.add_argument("--types", action="store_true", help="Import Type nodes")
    parser.add_argument("--prefigures", action="store_true", help="Import PREFIGURES edges")
    parser.add_argument("--memberships", action="store_true", help="Import MEMBER_OF edges")
    parser.add_argument("--teaches", action="store_true", help="Import TEACHES edges")
    # Source selection
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--seed-only", action="store_true", help="Only curated CCC seed data")
    source.add_argument("--reviewed-only", action="store_true", help="Only reviewed Haydock data")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # If no step flag is set, run them all.
    run_all_steps = not (args.types or args.prefigures or args.memberships or args.teaches)
    do_types = run_all_steps or args.types
    do_prefigures = run_all_steps or args.prefigures
    do_memberships = run_all_steps or args.memberships
    do_teaches = run_all_steps or args.teaches

    try:
        print("\n" + "=" * 60)
        print("LogosGraph Typology Import")
        print("=" * 60)

        connection = get_connection()
        connection.connect()
        connection.verify()
        print("   ✓ Connected to Neo4j")

        setup_schema(connection)
        print("   ✓ Schema ready (Type constraint + indexes)")

        # Seed files are needed for every mode except reviewed-only steps that
        # use no seed input; validate them whenever they will be read.
        if not args.reviewed_only:
            seed_valid, seed_errors = validate_all_seed_files()
            if not seed_valid:
                raise ValueError(f"Typology seed files failed validation: {seed_errors}")
            print("   ✓ Seed files validated")

        stats = {}
        start = time.time()

        if do_types:
            print("\n📦 Importing Type nodes...")
            if args.seed_only:
                types = parse_seed_types()
            elif args.reviewed_only:
                types = parse_reviewed_types()
            else:
                types = parse_all_types()
            stats["types"] = import_types(types, connection)
            print(f"   ✓ {stats['types']} Type nodes")

        if do_prefigures:
            print("\n🔗 Importing PREFIGURES edges...")
            rels = []
            if not args.reviewed_only:
                rels += list(parse_seed_prefigures())
            if not args.seed_only:
                rels += list(parse_approved_prefigures())
            created, skipped = import_prefigures(rels, connection)
            stats["prefigures"] = (created, skipped)
            print(f"   ✓ {created:,} PREFIGURES edges" + (f" ({skipped} skipped)" if skipped else ""))

        if do_memberships:
            print("\n🔗 Importing MEMBER_OF edges...")
            mems = []
            if not args.reviewed_only:
                mems += list(parse_seed_memberships())
            if not args.seed_only:
                mems += list(parse_approved_memberships())
            created, skipped = import_verse_memberships(mems, connection)
            stats["memberships"] = (created, skipped)
            print(f"   ✓ {created:,} MEMBER_OF edges" + (f" ({skipped} skipped)" if skipped else ""))

        if do_teaches:
            if args.reviewed_only:
                print("\n🔗 Skipping TEACHES (no reviewed CCC teaching data)")
            else:
                print("\n🔗 Importing TEACHES edges...")
                created, skipped = import_teaches(list(parse_teaches()), connection)
                stats["teaches"] = (created, skipped)
                print(f"   ✓ {created:,} TEACHES edges" + (f" ({skipped} skipped)" if skipped else ""))

        connection.close()

        print("\n" + "=" * 60)
        print(f"Typology import complete ({time.time() - start:.1f}s)")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
