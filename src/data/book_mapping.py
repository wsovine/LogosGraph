"""Book abbreviation mapping between data sources.

Maps between:
- CPDV numeric book IDs (1-73)
- TSK abbreviations (Gen, Exod, Prov, etc.)
- USFM book codes (GEN, EXO, MAT, etc.)
- Haydock/Douay-Rheims book names (3 Kings, Ecclesiasticus, etc.)
- Standard 3-letter abbreviations (GEN, EXO, PRO, etc.)
"""

import logging
import re
from typing import NamedTuple

logger = logging.getLogger(__name__)

# CPDV numeric ID (1-73) to standard 3-letter abbreviation
CPDV_BOOK_ID_TO_ABBREV: dict[int, str] = {
    # Old Testament (Protestant canon)
    1: "GEN",
    2: "EXO",
    3: "LEV",
    4: "NUM",
    5: "DEU",
    6: "JOS",
    7: "JDG",
    8: "RUT",
    9: "1SA",
    10: "2SA",
    11: "1KI",
    12: "2KI",
    13: "1CH",
    14: "2CH",
    15: "EZR",
    16: "NEH",
    # Deuterocanonical books
    17: "TOB",  # Tobit
    18: "JDT",  # Judith
    19: "EST",  # Esther (with Greek additions)
    20: "1MA",  # 1 Maccabees
    21: "2MA",  # 2 Maccabees
    # Wisdom Literature
    22: "JOB",
    23: "PSA",
    24: "PRO",
    25: "ECC",
    26: "SNG",
    27: "WIS",  # Wisdom of Solomon (Deuterocanonical)
    28: "SIR",  # Sirach/Ecclesiasticus (Deuterocanonical)
    # Prophets
    29: "ISA",
    30: "JER",
    31: "LAM",
    32: "BAR",  # Baruch (Deuterocanonical)
    33: "EZK",
    34: "DAN",
    35: "HOS",
    36: "JOL",
    37: "AMO",
    38: "OBA",
    39: "JON",
    40: "MIC",
    41: "NAM",
    42: "HAB",
    43: "ZEP",
    44: "HAG",
    45: "ZEC",
    46: "MAL",
    # New Testament
    47: "MAT",
    48: "MRK",
    49: "LUK",
    50: "JHN",
    51: "ACT",
    52: "ROM",
    53: "1CO",
    54: "2CO",
    55: "GAL",
    56: "EPH",
    57: "PHP",
    58: "COL",
    59: "1TH",
    60: "2TH",
    61: "1TI",
    62: "2TI",
    63: "TIT",
    64: "PHM",
    65: "HEB",
    66: "JAS",
    67: "1PE",
    68: "2PE",
    69: "1JN",
    70: "2JN",
    71: "3JN",
    72: "JUD",
    73: "REV",
}

# TSK abbreviation to standard 3-letter abbreviation
TSK_ABBREV_TO_STANDARD: dict[str, str] = {
    "Gen": "GEN",
    "Exod": "EXO",
    "Lev": "LEV",
    "Num": "NUM",
    "Deut": "DEU",
    "Josh": "JOS",
    "Judg": "JDG",
    "Ruth": "RUT",
    "1Sam": "1SA",
    "2Sam": "2SA",
    "1Kgs": "1KI",
    "2Kgs": "2KI",
    "1Chr": "1CH",
    "2Chr": "2CH",
    "Ezra": "EZR",
    "Neh": "NEH",
    "Esth": "EST",
    "Job": "JOB",
    "Ps": "PSA",
    "Prov": "PRO",
    "Eccl": "ECC",
    "Song": "SNG",
    "Isa": "ISA",
    "Jer": "JER",
    "Lam": "LAM",
    "Ezek": "EZK",
    "Dan": "DAN",
    "Hos": "HOS",
    "Joel": "JOL",
    "Amos": "AMO",
    "Obad": "OBA",
    "Jonah": "JON",
    "Mic": "MIC",
    "Nah": "NAM",
    "Hab": "HAB",
    "Zeph": "ZEP",
    "Hag": "HAG",
    "Zech": "ZEC",
    "Mal": "MAL",
    "Matt": "MAT",
    "Mark": "MRK",
    "Luke": "LUK",
    "John": "JHN",
    "Acts": "ACT",
    "Rom": "ROM",
    "1Cor": "1CO",
    "2Cor": "2CO",
    "Gal": "GAL",
    "Eph": "EPH",
    "Phil": "PHP",
    "Col": "COL",
    "1Thess": "1TH",
    "2Thess": "2TH",
    "1Tim": "1TI",
    "2Tim": "2TI",
    "Titus": "TIT",
    "Phlm": "PHM",
    "Heb": "HEB",
    "Jas": "JAS",
    "1Pet": "1PE",
    "2Pet": "2PE",
    "1John": "1JN",
    "2John": "2JN",
    "3John": "3JN",
    "Jude": "JUD",
    "Rev": "REV",
}

# USFM filename book codes to standard abbreviation
# These are extracted from Haydock filenames like "01-GEN-ENG[B]DRC1750[pd].p.sfm"
USFM_BOOK_TO_STANDARD: dict[str, str] = {
    # Old Testament
    "GEN": "GEN", "EXO": "EXO", "LEV": "LEV", "NUM": "NUM", "DEU": "DEU",
    "JOS": "JOS", "JDG": "JDG", "RUT": "RUT",
    "1SA": "1SA", "2SA": "2SA", "1KI": "1KI", "2KI": "2KI",
    "1CH": "1CH", "2CH": "2CH", "EZR": "EZR", "NEH": "NEH",
    "EST": "EST", "JOB": "JOB", "PSA": "PSA", "PRO": "PRO",
    "ECC": "ECC", "SNG": "SNG", "ISA": "ISA", "JER": "JER",
    "LAM": "LAM", "EZK": "EZK", "DAN": "DAN",
    "HOS": "HOS", "JOL": "JOL", "AMO": "AMO", "OBA": "OBA",
    "JON": "JON", "MIC": "MIC", "NAM": "NAM", "HAB": "HAB",
    "ZEP": "ZEP", "HAG": "HAG", "ZEC": "ZEC", "MAL": "MAL",
    # Deuterocanonical
    "TOB": "TOB", "JDT": "JDT", "WIS": "WIS", "SIR": "SIR",
    "BAR": "BAR", "1MA": "1MA", "2MA": "2MA",
    # New Testament
    "MAT": "MAT", "MRK": "MRK", "LUK": "LUK", "JHN": "JHN",
    "ACT": "ACT", "ROM": "ROM", "1CO": "1CO", "2CO": "2CO",
    "GAL": "GAL", "EPH": "EPH", "PHP": "PHP", "COL": "COL",
    "1TH": "1TH", "2TH": "2TH", "1TI": "1TI", "2TI": "2TI",
    "TIT": "TIT", "PHM": "PHM", "HEB": "HEB",
    "JAM": "JAS",  # Haydock uses JAM, we use JAS
    "1PE": "1PE", "2PE": "2PE",
    "1JN": "1JN", "2JN": "2JN", "3JN": "3JN",
    "JUD": "JUD", "REV": "REV",
}

# Douay-Rheims book names to standard abbreviation
# Haydock uses DR naming conventions in cross-references
DOUAY_RHEIMS_TO_STANDARD: dict[str, str] = {
    # Old Testament - standard names (passthrough)
    "Genesis": "GEN", "Exodus": "EXO", "Leviticus": "LEV",
    "Numbers": "NUM", "Deuteronomy": "DEU",
    "Judges": "JDG", "Ruth": "RUT",

    # DR unique naming - Historical books
    "Josue": "JOS",              # Joshua
    "1 Kings": "1SA",            # DR "Kings" = Protestant "Samuel"
    "2 Kings": "2SA",
    "3 Kings": "1KI",            # DR "3 Kings" = Protestant "1 Kings"
    "4 Kings": "2KI",
    "1 Paralipomenon": "1CH",    # Chronicles
    "2 Paralipomenon": "2CH",
    "1 Esdras": "EZR",           # Ezra
    "2 Esdras": "NEH",           # Nehemiah
    "Esther": "EST",

    # Deuterocanonical
    "Tobias": "TOB",             # Tobit
    "Judith": "JDT",
    "1 Machabees": "1MA",        # Maccabees spelling
    "2 Machabees": "2MA",

    # Wisdom Literature
    "Job": "JOB",
    "Psalm": "PSA",              # Singular form
    "Psalms": "PSA",
    "Proverbs": "PRO",
    "Ecclesiastes": "ECC",
    "Canticle of Canticles": "SNG",  # Song of Solomon
    "Wisdom": "WIS",
    "Ecclesiasticus": "SIR",     # Sirach

    # Prophets - unique DR names
    "Isaias": "ISA",             # Isaiah
    "Jeremias": "JER",           # Jeremiah
    "Lamentations": "LAM",
    "Baruch": "BAR",
    "Ezechiel": "EZK",           # Ezekiel
    "Daniel": "DAN",
    "Osee": "HOS",               # Hosea
    "Joel": "JOL",
    "Amos": "AMO",
    "Abdias": "OBA",             # Obadiah
    "Jonas": "JON",              # Jonah
    "Micheas": "MIC",            # Micah
    "Nahum": "NAM",
    "Habacuc": "HAB",            # Habakkuk
    "Sophonias": "ZEP",          # Zephaniah
    "Aggeus": "HAG",             # Haggai
    "Zacharias": "ZEC",          # Zechariah
    "Malachias": "MAL",          # Malachi

    # New Testament (mostly standard)
    "Matthew": "MAT", "Mark": "MRK", "Luke": "LUK", "John": "JHN",
    "Acts": "ACT", "Romans": "ROM",
    "1 Corinthians": "1CO", "2 Corinthians": "2CO",
    "Galatians": "GAL", "Ephesians": "EPH",
    "Philippians": "PHP", "Colossians": "COL",
    "1 Thessalonians": "1TH", "2 Thessalonians": "2TH",
    "1 Timothy": "1TI", "2 Timothy": "2TI",
    "Titus": "TIT", "Philemon": "PHM", "Hebrews": "HEB",
    "James": "JAS",
    "1 Peter": "1PE", "2 Peter": "2PE",
    "1 John": "1JN", "2 John": "2JN", "3 John": "3JN",
    "Jude": "JUD",
    "Apocalypse": "REV",         # Revelation
}

# Build abbreviation mappings for reference parsing
# Maps common abbreviations used in Haydock cross-references
HAYDOCK_ABBREV_TO_STANDARD: dict[str, str] = {
    # Full names (from DOUAY_RHEIMS_TO_STANDARD)
    **DOUAY_RHEIMS_TO_STANDARD,

    # Common abbreviations found in Haydock references
    # Old Testament
    "Gen": "GEN", "Gen.": "GEN",
    "Exod": "EXO", "Exod.": "EXO", "Ex": "EXO", "Ex.": "EXO",
    "Lev": "LEV", "Lev.": "LEV",
    "Num": "NUM", "Num.": "NUM",
    "Deut": "DEU", "Deut.": "DEU", "Dt": "DEU", "Dt.": "DEU",
    "Jos": "JOS", "Jos.": "JOS",
    "Judg": "JDG", "Judg.": "JDG",
    "1 Sam": "1SA", "2 Sam": "2SA",  # Sometimes uses Samuel
    "1 Kgs": "1KI", "2 Kgs": "2KI",  # Sometimes uses standard Kings
    "1 Chr": "1CH", "2 Chr": "2CH",
    "1 Par": "1CH", "2 Par": "2CH",  # Paralipomenon abbreviations
    "Neh": "NEH", "Neh.": "NEH",
    "Tob": "TOB", "Tob.": "TOB",
    "Jud": "JDT",  # Judith (context dependent - also Jude in NT)
    "Est": "EST", "Est.": "EST", "Esth": "EST", "Esth.": "EST",
    "1 Mac": "1MA", "2 Mac": "2MA", "1 Mach": "1MA", "2 Mach": "2MA",
    "Ps": "PSA", "Ps.": "PSA", "Psa": "PSA", "Psa.": "PSA",
    "Prov": "PRO", "Prov.": "PRO", "Pro": "PRO", "Pro.": "PRO",
    "Eccles": "ECC", "Eccles.": "ECC", "Eccl": "ECC", "Eccl.": "ECC",
    "Cant": "SNG", "Cant.": "SNG",  # Canticle
    "Wis": "WIS", "Wis.": "WIS", "Wisd": "WIS", "Wisd.": "WIS",
    "Ecclus": "SIR", "Ecclus.": "SIR",  # Ecclesiasticus
    "Isa": "ISA", "Isa.": "ISA", "Is": "ISA", "Is.": "ISA",
    "Jer": "JER", "Jer.": "JER",
    "Lam": "LAM", "Lam.": "LAM",
    "Bar": "BAR", "Bar.": "BAR",
    "Ezek": "EZK", "Ezek.": "EZK", "Ezech": "EZK", "Ezech.": "EZK",
    "Dan": "DAN", "Dan.": "DAN",
    "Hos": "HOS", "Hos.": "HOS", "Os": "HOS", "Os.": "HOS",
    "Am": "AMO", "Am.": "AMO",
    "Obad": "OBA", "Obad.": "OBA", "Abd": "OBA", "Abd.": "OBA",
    "Jon": "JON", "Jon.": "JON",
    "Mic": "MIC", "Mic.": "MIC", "Mich": "MIC", "Mich.": "MIC",
    "Nah": "NAM", "Nah.": "NAM",
    "Hab": "HAB", "Hab.": "HAB",
    "Zeph": "ZEP", "Zeph.": "ZEP", "Soph": "ZEP", "Soph.": "ZEP",
    "Hag": "HAG", "Hag.": "HAG", "Agg": "HAG", "Agg.": "HAG",
    "Zech": "ZEC", "Zech.": "ZEC", "Zach": "ZEC", "Zach.": "ZEC",
    "Mal": "MAL", "Mal.": "MAL", "Malach": "MAL", "Malach.": "MAL",

    # New Testament
    "Matt": "MAT", "Matt.": "MAT", "Mt": "MAT", "Mt.": "MAT",
    "Mk": "MRK", "Mk.": "MRK",
    "Lk": "LUK", "Lk.": "LUK",
    "Jn": "JHN", "Jn.": "JHN",
    "Rom": "ROM", "Rom.": "ROM",
    "1 Cor": "1CO", "2 Cor": "2CO",
    "Gal": "GAL", "Gal.": "GAL",
    "Eph": "EPH", "Eph.": "EPH",
    "Phil": "PHP", "Phil.": "PHP",
    "Col": "COL", "Col.": "COL",
    "1 Thess": "1TH", "2 Thess": "2TH",
    "1 Tim": "1TI", "2 Tim": "2TI",
    "Tit": "TIT", "Tit.": "TIT",
    "Phm": "PHM", "Phm.": "PHM", "Philem": "PHM", "Philem.": "PHM",
    "Heb": "HEB", "Heb.": "HEB",
    "Jam": "JAS", "Jam.": "JAS", "Jas": "JAS", "Jas.": "JAS",
    "1 Pet": "1PE", "2 Pet": "2PE",
    "1 Jn": "1JN", "2 Jn": "2JN", "3 Jn": "3JN",
    "Apoc": "REV", "Apoc.": "REV", "Rev": "REV", "Rev.": "REV",
}

# Standard abbreviation to full book name
STANDARD_TO_BOOK_NAME: dict[str, str] = {
    "GEN": "Genesis",
    "EXO": "Exodus",
    "LEV": "Leviticus",
    "NUM": "Numbers",
    "DEU": "Deuteronomy",
    "JOS": "Joshua",
    "JDG": "Judges",
    "RUT": "Ruth",
    "1SA": "1 Samuel",
    "2SA": "2 Samuel",
    "1KI": "1 Kings",
    "2KI": "2 Kings",
    "1CH": "1 Chronicles",
    "2CH": "2 Chronicles",
    "EZR": "Ezra",
    "NEH": "Nehemiah",
    "TOB": "Tobit",
    "JDT": "Judith",
    "EST": "Esther",
    "1MA": "1 Maccabees",
    "2MA": "2 Maccabees",
    "JOB": "Job",
    "PSA": "Psalms",
    "PRO": "Proverbs",
    "ECC": "Ecclesiastes",
    "SNG": "Song of Solomon",
    "WIS": "Wisdom",
    "SIR": "Sirach",
    "ISA": "Isaiah",
    "JER": "Jeremiah",
    "LAM": "Lamentations",
    "BAR": "Baruch",
    "EZK": "Ezekiel",
    "DAN": "Daniel",
    "HOS": "Hosea",
    "JOL": "Joel",
    "AMO": "Amos",
    "OBA": "Obadiah",
    "JON": "Jonah",
    "MIC": "Micah",
    "NAM": "Nahum",
    "HAB": "Habakkuk",
    "ZEP": "Zephaniah",
    "HAG": "Haggai",
    "ZEC": "Zechariah",
    "MAL": "Malachi",
    "MAT": "Matthew",
    "MRK": "Mark",
    "LUK": "Luke",
    "JHN": "John",
    "ACT": "Acts",
    "ROM": "Romans",
    "1CO": "1 Corinthians",
    "2CO": "2 Corinthians",
    "GAL": "Galatians",
    "EPH": "Ephesians",
    "PHP": "Philippians",
    "COL": "Colossians",
    "1TH": "1 Thessalonians",
    "2TH": "2 Thessalonians",
    "1TI": "1 Timothy",
    "2TI": "2 Timothy",
    "TIT": "Titus",
    "PHM": "Philemon",
    "HEB": "Hebrews",
    "JAS": "James",
    "1PE": "1 Peter",
    "2PE": "2 Peter",
    "1JN": "1 John",
    "2JN": "2 John",
    "3JN": "3 John",
    "JUD": "Jude",
    "REV": "Revelation",
}


class VerseRef(NamedTuple):
    """A parsed verse reference."""

    book: str  # Standard 3-letter abbreviation
    chapter: int
    verse: int


def normalize_tsk_reference(ref: str) -> VerseRef | None:
    """Parse a TSK reference into a normalized VerseRef.

    Args:
        ref: TSK reference string like "Gen.1.1" or "Prov.8.22"

    Returns:
        VerseRef with standard abbreviation, or None if book unknown.
    """
    # Pattern: Book.Chapter.Verse (e.g., "Gen.1.1", "1Cor.13.4")
    match = re.match(r"^(\d?[A-Za-z]+)\.(\d+)\.(\d+)$", ref)
    if not match:
        return None

    tsk_book, chapter_str, verse_str = match.groups()

    standard_book = TSK_ABBREV_TO_STANDARD.get(tsk_book)
    if standard_book is None:
        return None

    return VerseRef(
        book=standard_book,
        chapter=int(chapter_str),
        verse=int(verse_str),
    )


def parse_verse_range(range_str: str) -> list[VerseRef]:
    """Parse a TSK verse range into individual VerseRefs.

    Args:
        range_str: Either a single ref "Gen.1.1" or range "Prov.8.22-Prov.8.30"

    Returns:
        List of VerseRef tuples. For ranges, expands to all verses in range.
    """
    if "-" not in range_str:
        ref = normalize_tsk_reference(range_str)
        return [ref] if ref else []

    # Range format: "Book.Ch.V-Book.Ch.V"
    parts = range_str.split("-")
    if len(parts) != 2:
        return []

    start_ref = normalize_tsk_reference(parts[0])
    end_ref = normalize_tsk_reference(parts[1])

    if not start_ref or not end_ref:
        return []

    # Only expand ranges within same book and chapter
    if start_ref.book != end_ref.book or start_ref.chapter != end_ref.chapter:
        # Cross-chapter or cross-book range - just return endpoints
        return [start_ref, end_ref]

    # Expand verse range within same chapter
    return [
        VerseRef(start_ref.book, start_ref.chapter, v)
        for v in range(start_ref.verse, end_ref.verse + 1)
    ]


def build_verse_id(book: str, chapter: int, verse: int) -> str:
    """Build a verse ID string.

    Args:
        book: Standard 3-letter abbreviation (e.g., "GEN")
        chapter: Chapter number
        verse: Verse number

    Returns:
        Verse ID string like "GEN-1-1"
    """
    return f"{book}-{chapter}-{verse}"


# Regex pattern for parsing Haydock reference text
# Matches: "Book Chapter:Verse" with optional verse range
# Examples: "Romans 8:15", "3 Kings 3:9", "Matthew 5:3-12", "1 Corinthians 3:16"
_HAYDOCK_REF_PATTERN = re.compile(
    r"""
    (?P<book>
        (?:\d\s*)?              # Optional number prefix (1, 2, 3, 4)
        [A-Za-z]+              # Book name
        (?:\s+of\s+[A-Za-z]+)? # Optional "of X" (Canticle of Canticles)
        \.?                    # Optional trailing period
    )
    \s*
    (?P<chapter>\d+)
    :
    (?P<verse>\d+)
    (?:-(?P<end_verse>\d+))?   # Optional verse range
    """,
    re.VERBOSE,
)


def _normalize_book_name(book_str: str) -> str | None:
    """Normalize a book name/abbreviation to standard 3-letter code.

    Args:
        book_str: Book name like "Romans", "3 Kings", "Rom.", etc.

    Returns:
        Standard 3-letter code, or None if not recognized.
    """
    # Clean up the book string
    book_clean = book_str.strip().rstrip(".")

    # Try direct lookup first
    if book_clean in HAYDOCK_ABBREV_TO_STANDARD:
        return HAYDOCK_ABBREV_TO_STANDARD[book_clean]

    # Try with trailing period (some abbreviations include it)
    if book_clean + "." in HAYDOCK_ABBREV_TO_STANDARD:
        return HAYDOCK_ABBREV_TO_STANDARD[book_clean + "."]

    # Try case-insensitive match on full names
    for name, code in DOUAY_RHEIMS_TO_STANDARD.items():
        if name.lower() == book_clean.lower():
            return code

    return None


def parse_haydock_reference(text: str) -> list[VerseRef]:
    """Parse a Haydock cross-reference text into VerseRefs.

    Handles various formats found in Haydock's \\xt fields:
    - Full names: "Romans 8:15"
    - Abbreviations: "Rom. 8:15", "1 Cor 3:16"
    - DR naming: "3 Kings 3:9", "Ecclesiasticus 6:6"
    - Multiple refs: "Romans 8:15.; 1 Corinthians 3:16."
    - Verse ranges: "Matthew 5:3-12" (expanded to individual verses)

    Args:
        text: Raw reference text from Haydock \\xt field.

    Returns:
        List of VerseRef tuples. May be empty if unparseable.
    """
    refs: list[VerseRef] = []

    # Split on semicolons and periods followed by space or end
    # This handles "Romans 8:15.; 1 Corinthians 3:16."
    # But we need to be careful not to split "Rom. 8:15"
    # Strategy: split on "; " or ".\s+(?=[A-Z0-9])" (period + space + capital/number)
    parts = re.split(r"[;]\s*|\.\s+(?=[1-4A-Z])", text)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Skip parts that are just annotations like "[17?]" or "--- **"
        if part.startswith("[") or part.startswith("-"):
            continue

        # Handle "and X:Y" patterns like "Romans 6:12-13. and 13:14"
        # These reference the same book as the previous reference
        if part.lower().startswith("and "):
            # Skip for now - these are complex to handle
            continue

        match = _HAYDOCK_REF_PATTERN.search(part)
        if not match:
            if part and not part.startswith("*"):
                logger.debug(f"Could not parse Haydock reference: {part!r}")
            continue

        book_str = match.group("book")
        chapter = int(match.group("chapter"))
        verse = int(match.group("verse"))
        end_verse_str = match.group("end_verse")

        # Normalize book name
        book_code = _normalize_book_name(book_str)
        if book_code is None:
            logger.debug(f"Unknown book in Haydock reference: {book_str!r}")
            continue

        if end_verse_str:
            # Verse range - expand to individual verses
            end_verse = int(end_verse_str)
            for v in range(verse, end_verse + 1):
                refs.append(VerseRef(book_code, chapter, v))
        else:
            refs.append(VerseRef(book_code, chapter, verse))

    return refs