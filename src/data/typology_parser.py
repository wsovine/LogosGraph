"""Parse typology data files (seed JSON + reviewed JSONL).

Yields normalized dicts for the typology importer:
- Type nodes (from ccc_types.json + new_types.jsonl)
- PREFIGURES relationships (from ccc_prefigures.json + typology_approved.jsonl)
- MEMBER_OF relationships (from ccc_verse_memberships.json + typology_approved.jsonl)
- TEACHES relationships (from ccc_teaches.json)

Parsers yield dicts; the importer batches them (mirrors src/data/cpdv_parser.py).
"""

import json
import logging
from pathlib import Path
from typing import Generator

from src.config import settings

logger = logging.getLogger(__name__)

# Data roots (DATA_DIR is data/raw, so .parent is data/)
SEED_DIR = settings.DATA_DIR.parent / "seed"
REVIEWED_DIR = settings.DATA_DIR.parent / "reviewed"


# ---------------------------------------------------------------------------
# Type nodes
# ---------------------------------------------------------------------------

def parse_seed_types(file_path: Path | None = None) -> Generator[dict, None, None]:
    """Yield Type nodes from the curated CCC seed file (have a category)."""
    if file_path is None:
        file_path = SEED_DIR / "ccc_types.json"

    logger.info(f"Parsing seed types from {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for type_data in data.get("types", []):
        yield _normalize_type(type_data)


def parse_reviewed_types(file_path: Path | None = None) -> Generator[dict, None, None]:
    """Yield Type nodes created during review (new_types.jsonl, no category)."""
    if file_path is None:
        file_path = REVIEWED_DIR / "new_types.jsonl"

    logger.info(f"Parsing reviewed types from {file_path}")
    if not file_path.exists():
        logger.warning(f"Reviewed types file not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield _normalize_type(json.loads(line))


def parse_all_types(
    seed_path: Path | None = None, reviewed_path: Path | None = None
) -> Generator[dict, None, None]:
    """Yield seed + reviewed Type nodes, de-duplicating by id (seed wins)."""
    seen: set[str] = set()
    for type_data in parse_seed_types(seed_path):
        seen.add(type_data["id"])
        yield type_data
    for type_data in parse_reviewed_types(reviewed_path):
        if type_data["id"] in seen:
            continue
        seen.add(type_data["id"])
        yield type_data


def _normalize_type(type_data: dict) -> dict:
    """Normalize a Type record to the importer's property set (category optional)."""
    return {
        "id": type_data["id"],
        "name": type_data.get("name"),
        "testament": type_data.get("testament"),
        "category": type_data.get("category"),  # None for reviewed types
        "description": type_data.get("description"),
        "source": type_data.get("source"),
        "confidence": type_data.get("confidence"),
        "reviewed": type_data.get("reviewed", False),
    }


# ---------------------------------------------------------------------------
# PREFIGURES relationships (Type -> Type)
# ---------------------------------------------------------------------------

def parse_seed_prefigures(file_path: Path | None = None) -> Generator[dict, None, None]:
    """Yield PREFIGURES relationships from the curated CCC seed file."""
    if file_path is None:
        file_path = SEED_DIR / "ccc_prefigures.json"

    logger.info(f"Parsing seed PREFIGURES from {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for rel in data.get("relationships", []):
        yield {
            "from": rel["from_type"],
            "to": rel["to_type"],
            "source": rel.get("source"),
            "confidence": rel.get("confidence"),
            "category": rel.get("category"),  # usually absent in seed
            "notes": rel.get("notes"),
            "source_verse": None,
        }


def parse_approved_prefigures(file_path: Path | None = None) -> Generator[dict, None, None]:
    """Yield PREFIGURES relationships from the reviewed Haydock extractions."""
    if file_path is None:
        file_path = REVIEWED_DIR / "typology_approved.jsonl"

    logger.info(f"Parsing approved PREFIGURES from {file_path}")
    if not file_path.exists():
        logger.warning(f"Approved extractions file not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            yield {
                "from": rec["type_id"],
                "to": rec["antitype_id"],
                "source": rec.get("source", "haydock"),
                "confidence": rec.get("confidence"),
                "category": rec.get("category"),
                "notes": rec.get("reviewer_notes"),
                "source_verse": rec.get("verse_id"),
            }


# ---------------------------------------------------------------------------
# MEMBER_OF relationships (Verse -> Type)
# ---------------------------------------------------------------------------

def parse_seed_memberships(file_path: Path | None = None) -> Generator[dict, None, None]:
    """Yield {type_id, verse_ids[]} memberships from the curated CCC seed file."""
    if file_path is None:
        file_path = SEED_DIR / "ccc_verse_memberships.json"

    logger.info(f"Parsing seed MEMBER_OF from {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for membership in data.get("memberships", []):
        yield {
            "type_id": membership["type_id"],
            "verse_ids": membership.get("verse_ids", []),
        }


def parse_approved_memberships(file_path: Path | None = None) -> Generator[dict, None, None]:
    """Yield {type_id, verse_ids:[verse_id]} from each reviewed extraction.

    The verse whose Haydock commentary attests the OT figure becomes scriptural
    evidence (MEMBER_OF) for that type.
    """
    if file_path is None:
        file_path = REVIEWED_DIR / "typology_approved.jsonl"

    logger.info(f"Parsing approved MEMBER_OF from {file_path}")
    if not file_path.exists():
        logger.warning(f"Approved extractions file not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            yield {"type_id": rec["type_id"], "verse_ids": [rec["verse_id"]]}


# ---------------------------------------------------------------------------
# TEACHES relationships (CatechismParagraph -> Type)
# ---------------------------------------------------------------------------

def parse_teaches(file_path: Path | None = None) -> Generator[dict, None, None]:
    """Yield {ccc_id, type_ids[]} from the curated CCC seed file."""
    if file_path is None:
        file_path = SEED_DIR / "ccc_teaches.json"

    logger.info(f"Parsing TEACHES from {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for teaches in data.get("teaches", []):
        yield {
            "ccc_id": teaches["ccc_id"],
            "type_ids": teaches.get("type_ids", []),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    types = list(parse_all_types())
    prefigures = list(parse_seed_prefigures()) + list(parse_approved_prefigures())
    memberships = list(parse_seed_memberships()) + list(parse_approved_memberships())
    teaches = list(parse_teaches())

    print(f"Types (seed + reviewed, deduped): {len(types)}")
    print(f"  OT: {sum(1 for t in types if t['testament'] == 'OT')}")
    print(f"  NT: {sum(1 for t in types if t['testament'] == 'NT')}")
    print(f"PREFIGURES rows (seed + approved): {len(prefigures)}")
    print(f"MEMBER_OF rows (seed + approved): {len(memberships)}")
    print(f"  total verse refs: {sum(len(m['verse_ids']) for m in memberships)}")
    print(f"TEACHES rows: {len(teaches)}")
