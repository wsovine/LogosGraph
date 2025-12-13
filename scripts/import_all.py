#!/usr/bin/env python3
"""CLI script to run the full import pipeline."""

import argparse
import logging
import sys

from src.import_pipeline.runner import run_full_import


def main():
    parser = argparse.ArgumentParser(
        description="Import Bible data into Neo4j graph database"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading data files (use existing files)",
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop all existing data before import",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        run_full_import(
            skip_download=args.skip_download,
            drop_existing=args.drop_existing,
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()