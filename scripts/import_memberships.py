#!/usr/bin/env python3
"""Import human-approved crossref-mined MEMBER_OF edges into Neo4j.

Reads data/reviewed/member_of_approved.jsonl (produced by
scripts/review_memberships.py) and MERGEs MEMBER_OF edges with provenance
(source='crossref-mined', confidence, corroboration, reviewed). Idempotent:
existing edges are never modified.

Usage:
    python scripts/import_memberships.py
    python scripts/import_memberships.py --dry-run
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.db.connection import get_connection
from src.import_pipeline.typology_importer import import_mined_memberships

DEFAULT_INPUT = Path("data/reviewed/member_of_approved.jsonl")


def main():
    parser = argparse.ArgumentParser(
        description="Import approved crossref-mined MEMBER_OF edges"
    )
    parser.add_argument(
        "-i", "--input", type=Path, default=DEFAULT_INPUT,
        help=f"Approved memberships JSONL (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be imported without writing to the database",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        print("Run: python scripts/review_memberships.py")
        sys.exit(1)

    rows = []
    with args.input.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    print(f"Loaded {len(rows):,} approved memberships from {args.input}")

    if args.dry_run:
        print("\nDry run -- would import:")
        for row in rows[:20]:
            conf = row.get("adjudication", {}).get("confidence", "?")
            print(f"  {row['verse_id']} -[:MEMBER_OF]-> {row['type_id']} "
                  f"(confidence: {conf})")
        if len(rows) > 20:
            print(f"  ... and {len(rows) - 20} more")
        return

    connection = get_connection()
    connection.verify()

    created, skipped = import_mined_memberships(rows, connection)
    print(f"\nMEMBER_OF edges processed: {created} (skipped: {skipped})")
    print("\nNext step:")
    print("  python scripts/validate_import.py")

    connection.close()


if __name__ == "__main__":
    main()
