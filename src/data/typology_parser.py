"""Parse typology data files (seed JSON + reviewed JSONL).

Yields normalized dicts for the typology importer:
- Type nodes (from ccc_types.json + new_types.jsonl)
- PREFIGURES relationships (from ccc_prefigures.json + typology_approved.jsonl)
- MEMBER_OF relationships (from ccc_verse_memberships.json + typology_approved.jsonl)
- TEACHES relationships (from ccc_teaches.json)
- Catechism-pass rows (from ccc_typology_approved.jsonl) and the Type changes
  overlay (type_changes.jsonl: new Types, renames/broadenings, merges)

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
    """Yield seed + reviewed Type nodes, de-duplicating by id (seed wins).

    The Type changes overlay applies last: renamed/broadened Types get their new
    name and description, merged-away Types are dropped, and new Types are added.
    """
    changes = load_type_changes()
    seen: set[str] = set()
    for type_data in [*parse_seed_types(seed_path), *parse_reviewed_types(reviewed_path)]:
        if type_data["id"] in seen or type_data["id"] in changes["aliases"]:
            continue
        seen.add(type_data["id"])
        yield {**type_data, **changes["overrides"].get(type_data["id"], {})}
    for type_data in changes["new"]:
        if type_data["id"] not in seen:
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
                "source_verse": None if _is_chapter_level(rec["verse_id"]) else rec["verse_id"],
            }


def _is_chapter_level(verse_id: str) -> bool:
    """Haydock chapter prefaces are keyed to verse 0 (e.g. "REV-18-0") and have no Verse node."""
    return verse_id.endswith("-0")


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
    evidence (MEMBER_OF) for that type. Chapter-level prefaces attest no
    particular verse, so they yield no membership.
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
            if _is_chapter_level(rec["verse_id"]):
                continue
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


# ---------------------------------------------------------------------------
# Catechism typology pass (dev/active/ccc-typology-pass/)
# ---------------------------------------------------------------------------

def load_type_changes(file_path: Path | None = None) -> dict:
    """Read the approved Type decisions overlay.

    Returns {"new": [Type rows], "overrides": {id: {name, description}},
    "aliases": {absorbed_id: survivor_id}}. Renames and broadenings keep the id.
    """
    if file_path is None:
        file_path = REVIEWED_DIR / "type_changes.jsonl"
    changes: dict = {"new": [], "overrides": {}, "aliases": {}}
    if not file_path.exists():
        return changes
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            if d["action"] == "new":
                changes["new"].append(_normalize_type({
                    "id": d["new_id"], "name": d["name"], "testament": d["testament"],
                    "description": d.get("description"), "source": "ccc-review", "reviewed": True,
                }))
            elif d["action"] in ("broaden", "rename", "merge"):
                override = {"name": d["name"]}
                if d.get("description"):
                    override["description"] = d["description"]
                changes["overrides"][d["target_id"]] = override
                for absorbed in d.get("absorbs") or []:
                    changes["aliases"][absorbed] = d["target_id"]
    return changes


def apply_type_aliases(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    """Re-point rows at merge survivors (merged-away Type ids -> surviving id)."""
    aliases = load_type_changes()["aliases"]
    if not aliases:
        return rows
    return [{**r, **{k: aliases.get(r[k], r[k]) for k in keys if r.get(k)}} for r in rows]


def _ccc_approved(file_path: Path | None) -> list[dict]:
    if file_path is None:
        file_path = REVIEWED_DIR / "ccc_typology_approved.jsonl"
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _ccc_quotes(rec: dict) -> list[tuple[int, str]]:
    """(paragraph, quote) pairs: one for a plain row, one per paragraph for a synthesized row."""
    if rec.get("quotes"):
        return [(q["ccc"], q["quote"]) for q in rec["quotes"]]
    return [(rec["ccc"], rec["quote"])]


def parse_ccc_approved_prefigures(file_path: Path | None = None) -> Generator[dict, None, None]:
    """Yield PREFIGURES rows from the reviewed Catechism pass.

    Each attesting paragraph becomes a source ("CCC-1541"). The note is the
    Catechism's own words, never AI text. A link the graph already had keeps its
    category (bucket A rows carry it as existing_category).
    """
    for rec in _ccc_approved(file_path):
        if rec["kind"] != "prefigures":
            continue
        quotes = _ccc_quotes(rec)
        note = " … ".join(f"CCC {n}: “{q}”" for n, q in quotes)
        for n, _ in quotes:
            yield {
                "from": rec["type_id"],
                "to": rec["antitype_id"],
                "source": f"CCC-{n}",
                "confidence": rec.get("confidence"),
                "category": rec.get("existing_category") or rec.get("category"),
                "notes": note,
                "source_verse": None,
            }


def parse_ccc_approved_teaches(file_path: Path | None = None) -> Generator[dict, None, None]:
    """Yield {ccc_id, type_ids[]} TEACHES rows from the reviewed Catechism pass.

    A plain pair: the paragraph teaches both Types. A synthesized pair: the row's
    own paragraph carries the antitype, and the other quoted paragraphs the type.
    """
    for rec in _ccc_approved(file_path):
        if rec["kind"] == "teaches":
            yield {"ccc_id": f"CCC-{rec['ccc']}", "type_ids": [rec["type_id"]]}
        elif rec.get("quotes"):
            for n, _ in _ccc_quotes(rec):
                side = rec["antitype_id"] if n == rec["ccc"] else rec["type_id"]
                yield {"ccc_id": f"CCC-{n}", "type_ids": [side]}
        else:
            yield {"ccc_id": f"CCC-{rec['ccc']}", "type_ids": [rec["type_id"], rec["antitype_id"]]}


def parse_ccc_approved_memberships(file_path: Path | None = None) -> Generator[dict, None, None]:
    """Yield {verse_id, type_id, ccc} for verse evidence approved with Catechism-pass rows."""
    for rec in _ccc_approved(file_path):
        sides = {"type_verses": rec["type_id"], "antitype_verses": rec.get("antitype_id"),
                 "verses": rec["type_id"]}
        for side, verse_ids in (rec.get("verse_ids") or {}).items():
            for verse_id in verse_ids:
                if sides.get(side):
                    yield {"verse_id": verse_id, "type_id": sides[side], "ccc": f"CCC-{rec['ccc']}"}


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
