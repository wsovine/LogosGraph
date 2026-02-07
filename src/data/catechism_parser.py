"""Parse Catechism of the Catholic Church JSON file."""

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Generator

from src.config import settings

logger = logging.getLogger(__name__)

# Regex to match internal cross-references like (446), (446, 152), (888-892)
INTERNAL_REF_PATTERN = re.compile(r'\((\d+(?:[-–,]\s*\d+)*)\)')


def parse_catechism_paragraphs(
    file_path: Path | None = None
) -> Generator[dict, None, None]:
    """Parse catechism.json and yield paragraph dictionaries.

    The JSON structure is a list of objects with 'id' and 'text' fields.

    Args:
        file_path: Path to catechism.json. Defaults to data/raw/catechism/catechism.json.

    Yields:
        Dictionaries with keys: id, paragraph, text
    """
    if file_path is None:
        file_path = settings.DATA_DIR / "catechism" / "catechism.json"

    logger.info(f"Parsing Catechism from {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for entry in data:
        paragraph_num = entry["id"]
        text = entry["text"].strip()

        yield {
            "id": f"CCC-{paragraph_num}",
            "paragraph": paragraph_num,
            "text": text,
        }


def parse_catechism_internal_refs(
    file_path: Path | None = None
) -> Generator[dict, None, None]:
    """Extract internal cross-references from paragraph text.

    Parses patterns like (446), (446, 152, 42), (888-892) from text.
    Ranges like (888-892) expand to individual references sharing a passage_group UUID.
    Comma-separated single refs like (446, 152) do NOT share a passage_group.

    Args:
        file_path: Path to catechism.json. Defaults to data/raw/catechism/catechism.json.

    Yields:
        Dictionaries with keys: from_id, to_id, source, passage_group (optional)
    """
    if file_path is None:
        file_path = settings.DATA_DIR / "catechism" / "catechism.json"

    logger.info(f"Parsing internal cross-references from {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for entry in data:
        from_paragraph = entry["id"]
        from_id = f"CCC-{from_paragraph}"
        text = entry["text"]

        # Find all parenthetical references
        matches = INTERNAL_REF_PATTERN.findall(text)

        for match in matches:
            # Parse the reference content (e.g., "446", "446, 152", "888-892")
            refs = _parse_ref_content(match)

            for ref_list, passage_group in refs:
                for to_paragraph in ref_list:
                    # Skip self-references
                    if to_paragraph == from_paragraph:
                        continue

                    yield {
                        "from_id": from_id,
                        "to_id": f"CCC-{to_paragraph}",
                        "source": "CCC",
                        "passage_group": passage_group,
                    }


def _parse_ref_content(content: str) -> list[tuple[list[int], str | None]]:
    """Parse reference content into lists of paragraph numbers.

    Args:
        content: String like "446", "446, 152, 42", "888-892", or "888-892, 2032-2040"

    Returns:
        List of tuples: (list of paragraph numbers, passage_group UUID or None)
        - Single refs and comma-separated singles get passage_group=None
        - Ranges get a shared passage_group UUID
    """
    results = []

    # Split by comma to handle "888-892, 2032-2040" or "446, 152, 42"
    parts = [p.strip() for p in content.split(",")]

    for part in parts:
        # Check if this part is a range (contains dash)
        if "-" in part or "–" in part:
            # Normalize dash type
            part = part.replace("–", "-")
            try:
                start, end = part.split("-")
                start_num = int(start.strip())
                end_num = int(end.strip())

                # Expand range and assign passage_group
                if start_num <= end_num:
                    ref_list = list(range(start_num, end_num + 1))
                    # Only assign passage_group if range has multiple items
                    passage_group = str(uuid.uuid4()) if len(ref_list) > 1 else None
                    results.append((ref_list, passage_group))
            except ValueError:
                logger.warning(f"Could not parse range: {part}")
                continue
        else:
            # Single reference, no passage_group
            try:
                num = int(part.strip())
                results.append(([num], None))
            except ValueError:
                logger.warning(f"Could not parse reference: {part}")
                continue

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test paragraph parsing
    print("Testing paragraph parsing...")
    count = 0
    for para in parse_catechism_paragraphs():
        count += 1
        if count <= 3:
            print(f"  {para['id']}: {para['text'][:60]}...")

    print(f"\nTotal paragraphs: {count}")

    # Test internal refs parsing
    print("\nTesting internal cross-reference parsing...")
    ref_count = 0
    ranges_with_groups = 0

    for ref in parse_catechism_internal_refs():
        ref_count += 1
        if ref["passage_group"]:
            ranges_with_groups += 1
        if ref_count <= 5:
            pg = ref['passage_group'][:8] + '...' if ref['passage_group'] else None
            print(f"  {ref['from_id']} -> {ref['to_id']} (group: {pg})")

    print(f"\nTotal internal refs: {ref_count}")
    print(f"Refs with passage_group: {ranges_with_groups}")