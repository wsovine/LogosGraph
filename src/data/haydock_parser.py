"""Parse Haydock commentary cross-references from USFM files.

The Haydock Catholic Bible Commentary (1811-1859) includes cross-references
embedded in USFM format using \\x ... \\x* markers.
"""

import logging
import re
import uuid
from collections.abc import Generator
from pathlib import Path

from usfm_grammar import USFMParser

from src.config import settings
from src.data.book_mapping import (
    USFM_BOOK_TO_STANDARD,
    VerseRef,
    build_verse_id,
    parse_haydock_reference,
)

logger = logging.getLogger(__name__)

# Pattern to extract book code from filename
# Example: "65-2TI-ENG[B]DRC1750[pd].p.sfm" -> "2TI"
_FILENAME_PATTERN = re.compile(r"^\d+-([A-Z0-9]+)-")

# Pattern to extract cross-reference content
# Matches: \x + \xo 1:7\xt Romans 8:15.\x*
_CROSSREF_PATTERN = re.compile(
    r"\\x\s*\+?\s*\\xo\s*(\d+):(\d+)\s*\\xt\s*([^\\]+)\\x\*"
)


def _extract_book_code(filename: str) -> str | None:
    """Extract the USFM book code from a filename.

    Args:
        filename: Filename like "65-2TI-ENG[B]DRC1750[pd].p.sfm"

    Returns:
        Book code like "2TI", or None if not a Bible book file.
    """
    match = _FILENAME_PATTERN.match(filename)
    if not match:
        return None

    code = match.group(1)

    # Skip non-Bible files (front matter, introductions, etc.)
    if code in ("FRT", "INT", "BAK"):
        return None

    return code


def parse_haydock_crossrefs(
    data_dir: Path | None = None,
) -> Generator[dict, None, None]:
    """Parse cross-references from all Haydock USFM files.

    Args:
        data_dir: Directory containing Haydock .sfm files.
                  Defaults to settings.HAYDOCK_DIR.

    Yields:
        Dicts with cross-reference data:
        {
            "from_id": "2TI-1-7",
            "to_id": "ROM-8-15",
            "source": "Haydock",
            "passage_group": None or UUID string,
        }
    """
    if data_dir is None:
        data_dir = settings.HAYDOCK_DIR

    if not data_dir.exists():
        logger.error(f"Haydock directory not found: {data_dir}")
        return

    sfm_files = sorted(data_dir.glob("*.sfm"))
    if not sfm_files:
        logger.error(f"No .sfm files found in {data_dir}")
        return

    total_refs = 0
    skipped_refs = 0
    unknown_books = set()

    for sfm_path in sfm_files:
        # Extract book code from filename
        book_code = _extract_book_code(sfm_path.name)
        if book_code is None:
            logger.debug(f"Skipping non-Bible file: {sfm_path.name}")
            continue

        # Map to standard abbreviation
        standard_book = USFM_BOOK_TO_STANDARD.get(book_code)
        if standard_book is None:
            logger.warning(f"Unknown USFM book code: {book_code}")
            unknown_books.add(book_code)
            continue

        logger.debug(f"Processing {sfm_path.name} ({standard_book})")

        # Read and parse file content
        try:
            content = sfm_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Error reading {sfm_path}: {e}")
            continue

        # Find all cross-references using regex
        # We use regex instead of usfm_grammar for reliability with edge cases
        for match in _CROSSREF_PATTERN.finditer(content):
            chapter = int(match.group(1))
            verse = int(match.group(2))
            target_text = match.group(3).strip()

            from_id = build_verse_id(standard_book, chapter, verse)

            # Parse the target reference text
            target_refs = parse_haydock_reference(target_text)

            if not target_refs:
                skipped_refs += 1
                logger.debug(
                    f"Could not parse reference in {standard_book} {chapter}:{verse}: "
                    f"{target_text!r}"
                )
                continue

            # Generate passage_group UUID for verse ranges (multiple refs from same \xt)
            passage_group = str(uuid.uuid4()) if len(target_refs) > 1 else None

            for ref in target_refs:
                to_id = build_verse_id(ref.book, ref.chapter, ref.verse)

                yield {
                    "from_id": from_id,
                    "to_id": to_id,
                    "source": "Haydock",
                    "passage_group": passage_group,
                }
                total_refs += 1

    logger.info(f"Parsed {total_refs:,} Haydock cross-references")
    if skipped_refs:
        logger.info(f"Skipped {skipped_refs:,} unparseable references")
    if unknown_books:
        logger.warning(f"Unknown book codes encountered: {unknown_books}")


if __name__ == "__main__":
    # Quick test of the parser
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    print("Testing Haydock parser...")
    print()

    count = 0
    sample_refs = []

    for ref in parse_haydock_crossrefs():
        count += 1
        if count <= 20:
            sample_refs.append(ref)

    print(f"Total cross-references: {count:,}")
    print()
    print("Sample references:")
    for ref in sample_refs:
        print(f"  {ref['from_id']} -> {ref['to_id']}")
