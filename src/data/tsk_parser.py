"""Parse TSK cross-references file."""

import logging
import uuid
from pathlib import Path
from typing import Generator

from src.config import settings
from src.data.book_mapping import (
    build_verse_id,
    normalize_tsk_reference,
    parse_verse_range,
)

logger = logging.getLogger(__name__)


def parse_tsk_crossrefs(file_path: Path | None = None) -> Generator[dict, None, None]:
    """Parse TSK cross-references file and yield edge dictionaries.

    Handles verse ranges by expanding them to individual edges with a shared
    passage_group UUID for semantic grouping.

    Args:
        file_path: Path to cross_references.txt. Defaults to settings.DATA_DIR.

    Yields:
        Dictionaries with keys: from_id, to_id, votes, source, passage_group (optional)
    """
    if file_path is None:
        file_path = settings.DATA_DIR / "cross_references.txt"

    logger.info(f"Parsing TSK cross-references from {file_path}")

    unknown_books: set[str] = set()
    line_count = 0
    skipped_count = 0

    with open(file_path, "r", encoding="utf-8") as f:
        # Skip header line
        header = f.readline()
        logger.debug(f"Header: {header.strip()}")

        for line in f:
            line_count += 1
            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) != 3:
                logger.warning(f"Line {line_count}: Invalid format: {line[:50]}")
                skipped_count += 1
                continue

            from_ref, to_ref, votes_str = parts

            # Parse the source verse
            from_parsed = normalize_tsk_reference(from_ref)
            if from_parsed is None:
                # Extract book name for logging
                book_part = from_ref.split(".")[0] if "." in from_ref else from_ref
                if book_part not in unknown_books:
                    logger.debug(f"Unknown book in 'from' reference: {book_part}")
                    unknown_books.add(book_part)
                skipped_count += 1
                continue

            from_id = build_verse_id(from_parsed.book, from_parsed.chapter, from_parsed.verse)

            # Parse votes
            try:
                votes = int(votes_str)
            except ValueError:
                votes = 0

            # Parse target verse(s) - may be a range
            to_refs = parse_verse_range(to_ref)
            if not to_refs:
                book_part = to_ref.split(".")[0] if "." in to_ref else to_ref
                if book_part not in unknown_books:
                    logger.debug(f"Unknown book in 'to' reference: {book_part}")
                    unknown_books.add(book_part)
                skipped_count += 1
                continue

            # Generate passage_group UUID if this is a range (multiple targets)
            passage_group = str(uuid.uuid4()) if len(to_refs) > 1 else None

            for to_parsed in to_refs:
                to_id = build_verse_id(to_parsed.book, to_parsed.chapter, to_parsed.verse)

                yield {
                    "from_id": from_id,
                    "to_id": to_id,
                    "votes": votes,
                    "source": "TSK",
                    "passage_group": passage_group,
                }

    if unknown_books:
        logger.info(f"Unknown books encountered: {sorted(unknown_books)}")
    logger.info(f"Processed {line_count} lines, skipped {skipped_count}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    count = 0
    passage_groups = set()

    for ref in parse_tsk_crossrefs():
        count += 1
        if ref["passage_group"]:
            passage_groups.add(ref["passage_group"])

        if count <= 5:
            print(f"{ref['from_id']} -> {ref['to_id']} (votes: {ref['votes']})")

    print(f"\nTotal cross-reference edges: {count}")
    print(f"Total passage groups: {len(passage_groups)}")