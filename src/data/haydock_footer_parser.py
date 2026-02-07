"""Parse Haydock commentary footer notes from USFM files.

The Haydock Catholic Bible Commentary (1811-1859) includes extensive footnotes
embedded in USFM format using \f ... \f* markers. These contain rich theological
commentary including typological interpretations.

Footer format: \f + \fr <chapter>:<verse> \ft <commentary text>\f*
"""

import logging
import re
from collections.abc import Generator
from pathlib import Path

from src.config import settings
from src.data.book_mapping import USFM_BOOK_TO_STANDARD, build_verse_id

logger = logging.getLogger(__name__)

# Pattern to extract book code from filename
# Example: "01-GEN-ENG[B]DRC1750[pd].p.sfm" -> "GEN"
_FILENAME_PATTERN = re.compile(r"^\d+-([A-Z0-9]+)-")

# Pattern to extract footer content
# Matches: \f + \fr 1:1 \ft Commentary text here.\f*
# Uses DOTALL to handle multi-line footnotes
_FOOTER_PATTERN = re.compile(
    r"\\f\s*\+\s*\\fr\s*(\d+):(\d+)\s*\\ft\s*(.+?)\\f\*",
    re.DOTALL,
)


def _extract_book_code(filename: str) -> str | None:
    """Extract the USFM book code from a filename.

    Args:
        filename: Filename like "01-GEN-ENG[B]DRC1750[pd].p.sfm"

    Returns:
        Book code like "GEN", or None if not a Bible book file.
    """
    match = _FILENAME_PATTERN.match(filename)
    if not match:
        return None

    code = match.group(1)

    # Skip non-Bible files (front matter, introductions, etc.)
    if code in ("FRT", "INT", "BAK"):
        return None

    return code


def _clean_footer_text(text: str) -> str:
    """Clean footer text by normalizing whitespace and removing markers.

    Args:
        text: Raw footer text from USFM

    Returns:
        Cleaned text with normalized whitespace
    """
    # Normalize newlines and whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove any remaining USFM markers that might be embedded
    text = re.sub(r"\\[a-z]+\*?", "", text)

    return text.strip()


def parse_haydock_footers(
    data_dir: Path | None = None,
) -> Generator[dict, None, None]:
    """Parse footer comments from all Haydock USFM files.

    Args:
        data_dir: Directory containing Haydock .sfm files.
                  Defaults to settings.HAYDOCK_DIR.

    Yields:
        Dicts with footer data:
        {
            "verse_id": "GEN-1-1",
            "book": "GEN",
            "chapter": 1,
            "verse": 1,
            "text": "Commentary text...",
            "source": "Haydock",
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

    total_footers = 0
    parse_failures = 0
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

        # Read file content
        try:
            content = sfm_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Error reading {sfm_path}: {e}")
            parse_failures += 1
            continue

        # Find all footers using regex
        file_footers = 0
        for match in _FOOTER_PATTERN.finditer(content):
            chapter = int(match.group(1))
            verse = int(match.group(2))
            raw_text = match.group(3)

            # Clean the text
            text = _clean_footer_text(raw_text)

            if not text:
                logger.debug(
                    f"Empty footer text at {standard_book} {chapter}:{verse}"
                )
                continue

            verse_id = build_verse_id(standard_book, chapter, verse)

            yield {
                "verse_id": verse_id,
                "book": standard_book,
                "chapter": chapter,
                "verse": verse,
                "text": text,
                "source": "Haydock",
            }

            file_footers += 1
            total_footers += 1

        logger.debug(f"  {standard_book}: {file_footers} footers")

    logger.info(f"Parsed {total_footers:,} Haydock footer comments")
    if parse_failures:
        logger.warning(f"Failed to read {parse_failures} files")
    if unknown_books:
        logger.warning(f"Unknown book codes encountered: {unknown_books}")


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    print("Testing Haydock footer parser...")
    print()

    count = 0
    sample_footers = []
    books_seen = set()

    for footer in parse_haydock_footers():
        count += 1
        books_seen.add(footer["book"])
        if count <= 5:
            sample_footers.append(footer)

    print(f"Total footers: {count:,}")
    print(f"Books processed: {len(books_seen)}")
    print()
    print("Sample footers:")
    for f in sample_footers:
        preview = f["text"][:100] + "..." if len(f["text"]) > 100 else f["text"]
        print(f"  {f['verse_id']}: {preview}")