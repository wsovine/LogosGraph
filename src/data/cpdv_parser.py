"""Parse CPDV Bible JSON file."""

import json
import logging
from pathlib import Path
from typing import Generator

from src.config import settings
from src.data.book_mapping import (
    CPDV_BOOK_ID_TO_ABBREV,
    build_verse_id,
)

logger = logging.getLogger(__name__)

# Map CPDV book names to numeric IDs (matching CPDV_BOOK_ID_TO_ABBREV)
# CPDV uses Roman numerals (I, II, III) for numbered books
CPDV_BOOK_NAME_TO_ID: dict[str, int] = {
    "Genesis": 1, "Exodus": 2, "Leviticus": 3, "Numbers": 4, "Deuteronomy": 5,
    "Joshua": 6, "Judges": 7, "Ruth": 8,
    "I Samuel": 9, "II Samuel": 10,
    "I Kings": 11, "II Kings": 12,
    "I Chronicles": 13, "II Chronicles": 14,
    "Ezra": 15, "Nehemiah": 16,
    "Tobit": 17, "Judith": 18, "Esther": 19,
    "I Maccabees": 20, "II Maccabees": 21,
    "Job": 22, "Psalms": 23, "Proverbs": 24, "Ecclesiastes": 25, "Song of Solomon": 26,
    "Wisdom": 27, "Sirach": 28,
    "Isaiah": 29, "Jeremiah": 30, "Lamentations": 31, "Baruch": 32,
    "Ezekiel": 33, "Daniel": 34, "Hosea": 35, "Joel": 36, "Amos": 37,
    "Obadiah": 38, "Jonah": 39, "Micah": 40, "Nahum": 41, "Habakkuk": 42,
    "Zephaniah": 43, "Haggai": 44, "Zechariah": 45, "Malachi": 46,
    "Matthew": 47, "Mark": 48, "Luke": 49, "John": 50, "Acts": 51,
    "Romans": 52,
    "I Corinthians": 53, "II Corinthians": 54,
    "Galatians": 55, "Ephesians": 56, "Philippians": 57, "Colossians": 58,
    "I Thessalonians": 59, "II Thessalonians": 60,
    "I Timothy": 61, "II Timothy": 62,
    "Titus": 63, "Philemon": 64, "Hebrews": 65, "James": 66,
    "I Peter": 67, "II Peter": 68,
    "I John": 69, "II John": 70, "III John": 71,
    "Jude": 72,
    "Revelation": 73, "Revelation of John": 73,
}


def parse_cpdv(file_path: Path | None = None) -> Generator[dict, None, None]:
    """Parse CPDV JSON file and yield verse dictionaries.

    The CPDV JSON structure is: books[] -> chapters[] -> verses[]

    Args:
        file_path: Path to CPDV.json. Defaults to settings.DATA_DIR / "CPDV.json".

    Yields:
        Dictionaries with keys: id, book_id, book_name, chapter, verse, text
    """
    if file_path is None:
        file_path = settings.DATA_DIR / "CPDV.json"

    logger.info(f"Parsing CPDV from {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    unknown_books: set[str] = set()

    for book in data.get("books", []):
        book_name = book["name"]

        # Map book name to numeric ID, then to standard abbreviation
        book_id = CPDV_BOOK_NAME_TO_ID.get(book_name)
        if book_id is None:
            if book_name not in unknown_books:
                logger.warning(f"Unknown CPDV book name: {book_name}")
                unknown_books.add(book_name)
            continue

        standard_abbrev = CPDV_BOOK_ID_TO_ABBREV.get(book_id)
        if standard_abbrev is None:
            continue

        for chapter_data in book.get("chapters", []):
            chapter = chapter_data["chapter"]

            for verse_data in chapter_data.get("verses", []):
                verse_num = verse_data["verse"]
                text = verse_data["text"].strip()

                verse_id = build_verse_id(standard_abbrev, chapter, verse_num)

                yield {
                    "id": verse_id,
                    "book_id": standard_abbrev,
                    "book_name": book_name,
                    "chapter": chapter,
                    "verse": verse_num,
                    "text": text,
                }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    count = 0
    books = set()

    for verse in parse_cpdv():
        count += 1
        books.add(verse["book_id"])

        if count <= 3:
            print(f"{verse['id']}: {verse['text'][:50]}...")

    print(f"\nTotal verses: {count}")
    print(f"Total books: {len(books)}")