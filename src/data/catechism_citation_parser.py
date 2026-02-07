"""Parse scripture citations from CCC footnote text.

Handles formats like:
- Single verse: "Mt 28:19"
- Multiple verses: "Rom 10:9; I Cor 15:3-5"
- Verse ranges: "Mt 5:3-12"
- Cf. prefix: "Cf. Dt 32:6; Mal 2:10"
- Single-chapter books: "Jude 3" means Jude 1:3
- Comma-separated verses: "Jn 4:8, 16" means Jn 4:8 and Jn 4:16
"""

import logging
import re
import uuid
from typing import Generator

from src.data.book_mapping import CCC_ABBREV_TO_STANDARD, EXTERNAL_DOC_TYPES, build_ccc_verse_id

logger = logging.getLogger(__name__)

# Single-chapter books - when referenced as "Book N", N is the verse, not chapter
SINGLE_CHAPTER_BOOKS = {"JUD", "OBA", "PHM", "2JN", "3JN"}

# Regex pattern for scripture references in CCC footnotes
# Matches: "Book ch:v" or "Book ch:v-v" with optional Roman numeral prefix
# Examples: Mt 28:19, I Cor 15:3-5, 2 Sam 7:28, Ps 115:15
_CCC_SCRIPTURE_PATTERN = re.compile(
    r"""
    (?P<prefix>(?:I{1,3}|[1-4l])\s+)?  # Optional number prefix (I, II, III, 1-4, lowercase L)
    (?P<name>[A-Za-z]+)                 # Book name
    \s+
    (?P<chapter>\d+)
    (?:
        \s*:\s*(?P<verse>\d+)           # Verse number (allow spaces around colon)
        (?:\s*-\s*(?P<end_verse>\d+))?  # Optional end verse for range
    )?
    (?P<extra_verses>(?:\s*,\s*\d+(?:\s*-\s*\d+)?)*)?  # Optional comma-separated verses
    """,
    re.VERBOSE,
)

# Pattern to detect scripture-like references (for is_scripture_citation)
_SCRIPTURE_INDICATOR_PATTERN = re.compile(
    r"\b(?:Mt|Mk|Lk|Jn|Gen|Ex|Lev|Num|Dt|Is|Jer|Ps|Rom|Cor|Gal|Eph|Col|"
    r"Thess|Tim|Heb|Pet|Jn|Jude|Rev|Acts|Job|Prov|Wis|Sir|Dan|Hos|Am|"
    r"Mal|Zech|Hab|Joel|Amos|Mic|Nah|Zep|Hag|Bar|Lam|Ezek|Esth|Tob|"
    r"Jdt|Mac|Sam|Kgs|Chr|Ezra|Neh|Ruth|Judg|Josh|Song|Cant|Eccl|Obad)\b",
    re.IGNORECASE,
)


def is_scripture_citation(text: str) -> bool:
    """Check if text contains a scripture citation.

    Used to distinguish scripture references from external document refs.

    Args:
        text: Footnote citation text.

    Returns:
        True if text appears to contain scripture reference.
    """
    # Look for patterns like "Book ch:v" with known book abbreviations
    return bool(_SCRIPTURE_INDICATOR_PATTERN.search(text))


def _add_verses(
    verse_ids: list[str],
    book: str,
    chapter: int,
    verse: int,
    end_verse: int | None = None,
) -> None:
    """Add verse(s) to the list, expanding ranges if needed."""
    if end_verse:
        for v in range(verse, end_verse + 1):
            verse_ids.append(build_ccc_verse_id(book, chapter, v))
    else:
        verse_ids.append(build_ccc_verse_id(book, chapter, verse))


def parse_scripture_citation(text: str) -> list[str]:
    """Parse scripture citations from footnote text into verse IDs.

    Args:
        text: Footnote citation text like "Mt 28:19" or "Cf. Dt 32:6; Mal 2:10"

    Returns:
        List of verse IDs like ["MAT-28-19", "DEU-32-6", "MAL-2-10"].
        For verse ranges, expands to individual verses.
    """
    verse_ids: list[str] = []

    # Clean the text: remove Cf., cf., etc. anywhere in string
    text = re.sub(r"\bcf\.?\s*", "", text, flags=re.IGNORECASE)

    # Split on semicolons for multiple book references (NOT commas - those are same-chapter verses)
    parts = re.split(r";\s*", text)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Try to match scripture pattern
        match = _CCC_SCRIPTURE_PATTERN.search(part)
        if not match:
            continue

        # Build book abbreviation
        prefix = match.group("prefix")
        name = match.group("name")

        if prefix:
            # Normalize prefix: "I " -> "I ", "1 " -> "1 ", "l " -> "1 "
            prefix = prefix.strip()
            if prefix.lower() == "l":
                prefix = "1"
            book_key = f"{prefix} {name}"
        else:
            book_key = name

        # Look up standard abbreviation
        standard_book = CCC_ABBREV_TO_STANDARD.get(book_key)
        if not standard_book:
            # Try just the name without prefix
            standard_book = CCC_ABBREV_TO_STANDARD.get(name)
        if not standard_book:
            logger.debug(f"Unknown book in CCC citation: {book_key!r} from {part!r}")
            continue

        chapter_str = match.group("chapter")
        verse_str = match.group("verse")
        end_verse_str = match.group("end_verse")
        extra_verses_str = match.group("extra_verses")

        # Handle single-chapter books: "Jude 3" means Jude 1:3
        if not verse_str and standard_book in SINGLE_CHAPTER_BOOKS:
            chapter = 1
            verse = int(chapter_str)
            _add_verses(verse_ids, standard_book, chapter, verse)
            continue

        if not verse_str:
            # Chapter-only reference (e.g., "Is 43") - skip for now
            logger.debug(f"Chapter-only reference skipped: {part!r}")
            continue

        chapter = int(chapter_str)
        verse = int(verse_str)
        end_verse = int(end_verse_str) if end_verse_str else None

        _add_verses(verse_ids, standard_book, chapter, verse, end_verse)

        # Handle comma-separated verses in same chapter: "Jn 4:8, 16"
        if extra_verses_str:
            for extra_match in re.finditer(r"(\d+)(?:-(\d+))?", extra_verses_str):
                extra_verse = int(extra_match.group(1))
                extra_end = int(extra_match.group(2)) if extra_match.group(2) else None
                _add_verses(verse_ids, standard_book, chapter, extra_verse, extra_end)

    return verse_ids


def parse_footnote_citations(
    citations: list[dict],
) -> Generator[dict, None, None]:
    """Parse footnote citations and yield verse references with passage groups.

    For verse ranges within a single citation, assigns a shared passage_group UUID.

    Args:
        citations: List of dicts with keys: paragraph, footnote, citation_text

    Yields:
        Dicts with keys: paragraph, verse_id, passage_group (optional)
    """
    for citation in citations:
        paragraph = citation["paragraph"]
        text = citation["citation_text"]

        if not is_scripture_citation(text):
            continue

        verse_ids = parse_scripture_citation(text)

        if not verse_ids:
            continue

        # If multiple verses from a single footnote, they share a passage_group
        passage_group = str(uuid.uuid4()) if len(verse_ids) > 1 else None

        for verse_id in verse_ids:
            yield {
                "paragraph": paragraph,
                "verse_id": verse_id,
                "passage_group": passage_group,
            }


# Pattern for external document references like "DS 150", "LG 12", "PG 7/1, 549"
_EXTERNAL_DOC_PATTERN = re.compile(
    r"\b(?P<abbrev>[A-Z][A-Za-z]{1,4})\s+(?P<ref>\d+(?:[/-]\d+)?(?:\s*,\s*\d+(?:-\d+)?)*)",
)


def parse_external_citation(text: str) -> list[dict]:
    """Parse external document citations from footnote text.

    Args:
        text: Footnote citation text like "DS 150" or "LG 12; GS 22"

    Returns:
        List of dicts with keys: abbreviation, reference, doc_type, title
        Only returns citations for known document types.
    """
    results: list[dict] = []

    # Find all potential external doc references
    for match in _EXTERNAL_DOC_PATTERN.finditer(text):
        abbrev = match.group("abbrev")
        ref = match.group("ref")

        # Check if this is a known document type
        if abbrev in EXTERNAL_DOC_TYPES:
            doc_type, title = EXTERNAL_DOC_TYPES[abbrev]
            results.append({
                "abbreviation": abbrev,
                "reference": ref,
                "doc_type": doc_type,
                "title": title,
            })

    return results


def parse_external_footnote_citations(
    citations: list[dict],
) -> Generator[dict, None, None]:
    """Parse footnote citations and yield external document references.

    Args:
        citations: List of dicts with keys: paragraph, footnote, citation_text

    Yields:
        Dicts with keys: paragraph, abbreviation, reference, doc_type, title
    """
    for citation in citations:
        paragraph = citation["paragraph"]
        text = citation["citation_text"]

        # Skip scripture citations (they're handled separately)
        if is_scripture_citation(text):
            continue

        ext_refs = parse_external_citation(text)

        for ref in ext_refs:
            yield {
                "paragraph": paragraph,
                "abbreviation": ref["abbreviation"],
                "reference": ref["reference"],
                "doc_type": ref["doc_type"],
                "title": ref["title"],
            }


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)

    # Test cases with expected results
    test_cases = [
        # (input, expected_output)
        ("Mt 28:19", ["MAT-28-19"]),
        ("Cf. Dt 32:6; Mal 2:10", ["DEU-32-6", "MAL-2-10"]),
        ("Rom 10:9; I Cor 15:3-5", ["ROM-10-9", "1CO-15-3", "1CO-15-4", "1CO-15-5"]),
        ("2 Sam 7:28", ["2SA-7-28"]),
        ("Ps 115:15; Wis 7:17-21", ["PSA-113-15", "WIS-7-17", "WIS-7-18", "WIS-7-19", "WIS-7-20", "WIS-7-21"]),  # Hebrew 115 = Vulgate 113
        ("I Tim 3:15; Jude 3", ["1TI-3-15", "JUD-1-3"]),  # Single-chapter book
        ("Cf. Eph 4:4-6", ["EPH-4-4", "EPH-4-5", "EPH-4-6"]),
        ("Jn 3:16; cf. Hos 11:1; Is 49:14-15", ["JHN-3-16", "HOS-11-1", "ISA-49-14", "ISA-49-15"]),
        ("l Jn 4:8, 16", ["1JN-4-8", "1JN-4-16"]),  # lowercase L typo + comma verses
        ("Wis 7: 17-22", ["WIS-7-17", "WIS-7-18", "WIS-7-19", "WIS-7-20", "WIS-7-21", "WIS-7-22"]),  # Space before colon
        ("II Cor 5:17", ["2CO-5-17"]),  # Roman numeral II
        ("III Jn 4", ["3JN-1-4"]),  # Single-chapter book with Roman numeral
    ]

    print("Testing parse_scripture_citation():")
    passed = 0
    failed = 0
    for text, expected in test_cases:
        result = parse_scripture_citation(text)
        if result == expected:
            passed += 1
            print(f"  ✓ {text!r}")
        else:
            failed += 1
            print(f"  ✗ {text!r}")
            print(f"      Expected: {expected}")
            print(f"      Got:      {result}")

    print(f"\nResults: {passed} passed, {failed} failed")

    # Test is_scripture_citation
    print("\nTesting is_scripture_citation():")
    scripture_tests = [
        ("Mt 28:19", True),
        ("St. Augustine, En. in Ps. 103", True),  # Has "Ps" so detected
        ("Council of Trent, DS 1545", False),
        ("LG 12", False),
        ("Rom 8:15", True),
    ]
    for text, expected in scripture_tests:
        result = is_scripture_citation(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {text!r} -> {result}")

    # Test parse_external_citation
    print("\nTesting parse_external_citation():")
    external_tests = [
        ("DS 150", [{"abbreviation": "DS", "reference": "150", "doc_type": "Reference", "title": "Denzinger-Schönmetzer"}]),
        ("LG 12", [{"abbreviation": "LG", "reference": "12", "doc_type": "Vatican II", "title": "Lumen Gentium"}]),
        ("PG 7/1, 549-552", [{"abbreviation": "PG", "reference": "7/1, 549-552", "doc_type": "Patristics", "title": "Patrologia Graeca"}]),
        ("Cf. DS 525-541; 800-802", [{"abbreviation": "DS", "reference": "525-541", "doc_type": "Reference", "title": "Denzinger-Schönmetzer"}]),
        ("Council of Florence (1439): DS 1300-1301", [{"abbreviation": "DS", "reference": "1300-1301", "doc_type": "Reference", "title": "Denzinger-Schönmetzer"}]),
        ("St. Thomas Aquinas, STh II-II", []),  # STh uses Roman numerals, not matched by simple pattern
    ]
    for text, expected in external_tests:
        result = parse_external_citation(text)
        # Compare just the first result if any
        if result == expected:
            print(f"  ✓ {text!r}")
        else:
            print(f"  ✗ {text!r}")
            print(f"      Expected: {expected}")
            print(f"      Got:      {result}")
