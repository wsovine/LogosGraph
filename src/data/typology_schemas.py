"""Validation schemas for typology data files.

Provides JSON schemas and validation functions for:
- Type nodes (ccc_types.json)
- PREFIGURES relationships (ccc_prefigures.json)
- MEMBER_OF relationships (ccc_verse_memberships.json)
- TEACHES relationships (ccc_teaches.json)
"""

import json
import logging
from pathlib import Path
from typing import Any

from src.config import settings

logger = logging.getLogger(__name__)

# Valid categories for Type nodes
VALID_CATEGORIES = {
    "Sacramental",
    "Christological",
    "Ecclesial",
    "Marian",
    "Eschatological",
    "Covenantal",
}

# Valid testaments
VALID_TESTAMENTS = {"OT", "NT"}

# Valid confidence levels
VALID_CONFIDENCES = {"high", "medium", "low"}


def validate_type(type_data: dict[str, Any]) -> list[str]:
    """Validate a single Type node.

    Args:
        type_data: Dictionary with Type node fields.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []

    # Required fields
    required = ["id", "name", "testament", "category", "source", "confidence", "reviewed"]
    for field in required:
        if field not in type_data:
            errors.append(f"Missing required field: {field}")

    # Field validations
    if "id" in type_data:
        if not isinstance(type_data["id"], str) or not type_data["id"]:
            errors.append("id must be a non-empty string")
        elif not type_data["id"].replace("-", "").replace("_", "").isalnum():
            errors.append(f"id should be a slug: {type_data['id']}")

    if "testament" in type_data:
        if type_data["testament"] not in VALID_TESTAMENTS:
            errors.append(f"Invalid testament: {type_data['testament']}. Must be one of {VALID_TESTAMENTS}")

    if "category" in type_data:
        if type_data["category"] not in VALID_CATEGORIES:
            errors.append(f"Invalid category: {type_data['category']}. Must be one of {VALID_CATEGORIES}")

    if "confidence" in type_data:
        if type_data["confidence"] not in VALID_CONFIDENCES:
            errors.append(f"Invalid confidence: {type_data['confidence']}. Must be one of {VALID_CONFIDENCES}")

    if "reviewed" in type_data:
        if not isinstance(type_data["reviewed"], bool):
            errors.append("reviewed must be a boolean")

    return errors


def validate_prefigures_relationship(rel_data: dict[str, Any], valid_type_ids: set[str]) -> list[str]:
    """Validate a single PREFIGURES relationship.

    Args:
        rel_data: Dictionary with relationship fields.
        valid_type_ids: Set of valid Type IDs to check references against.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []

    # Required fields
    required = ["from_type", "to_type", "source", "confidence"]
    for field in required:
        if field not in rel_data:
            errors.append(f"Missing required field: {field}")

    # Check type references
    if "from_type" in rel_data and rel_data["from_type"] not in valid_type_ids:
        errors.append(f"Unknown from_type: {rel_data['from_type']}")

    if "to_type" in rel_data and rel_data["to_type"] not in valid_type_ids:
        errors.append(f"Unknown to_type: {rel_data['to_type']}")

    # Check confidence
    if "confidence" in rel_data and rel_data["confidence"] not in VALID_CONFIDENCES:
        errors.append(f"Invalid confidence: {rel_data['confidence']}")

    # Check category if present (optional on relationship, required on Type)
    if "category" in rel_data and rel_data["category"] not in VALID_CATEGORIES:
        errors.append(f"Invalid category: {rel_data['category']}. Must be one of {VALID_CATEGORIES}")

    # Optional fields: notes, description (no validation needed, just strings)

    return errors


def validate_verse_membership(membership: dict[str, Any], valid_type_ids: set[str]) -> list[str]:
    """Validate a single MEMBER_OF relationship set.

    Args:
        membership: Dictionary with type_id and verse_ids.
        valid_type_ids: Set of valid Type IDs to check references against.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []

    # Required fields
    if "type_id" not in membership:
        errors.append("Missing required field: type_id")
    elif membership["type_id"] not in valid_type_ids:
        errors.append(f"Unknown type_id: {membership['type_id']}")

    if "verse_ids" not in membership:
        errors.append("Missing required field: verse_ids")
    elif not isinstance(membership["verse_ids"], list):
        errors.append("verse_ids must be a list")
    elif len(membership["verse_ids"]) == 0:
        errors.append("verse_ids cannot be empty")
    else:
        # Validate verse ID format (BOOK-CHAPTER-VERSE)
        for verse_id in membership["verse_ids"]:
            if not _is_valid_verse_id(verse_id):
                errors.append(f"Invalid verse ID format: {verse_id}")

    return errors


def validate_teaches_relationship(teaches: dict[str, Any], valid_type_ids: set[str]) -> list[str]:
    """Validate a single TEACHES relationship set.

    Args:
        teaches: Dictionary with ccc_id and type_ids.
        valid_type_ids: Set of valid Type IDs to check references against.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []

    # Required fields
    if "ccc_id" not in teaches:
        errors.append("Missing required field: ccc_id")
    elif not teaches["ccc_id"].startswith("CCC-"):
        errors.append(f"Invalid CCC ID format: {teaches['ccc_id']}")

    if "type_ids" not in teaches:
        errors.append("Missing required field: type_ids")
    elif not isinstance(teaches["type_ids"], list):
        errors.append("type_ids must be a list")
    elif len(teaches["type_ids"]) == 0:
        errors.append("type_ids cannot be empty")
    else:
        for type_id in teaches["type_ids"]:
            if type_id not in valid_type_ids:
                errors.append(f"Unknown type_id: {type_id}")

    return errors


def _is_valid_verse_id(verse_id: str) -> bool:
    """Check if verse ID follows BOOK-CHAPTER-VERSE format.

    Args:
        verse_id: String like "GEN-1-1" or "1CO-10-4".

    Returns:
        True if format is valid.
    """
    parts = verse_id.split("-")
    if len(parts) < 3:
        return False

    # Book can be like "GEN", "1CO", "2TH" etc.
    # Chapter and verse should be numeric
    try:
        # Join all but last two parts as book (handles 1CO, 2TH, etc.)
        book = "-".join(parts[:-2]) if len(parts) > 3 else parts[0]
        chapter = int(parts[-2])
        verse = int(parts[-1])
        return len(book) >= 2 and chapter > 0 and verse > 0
    except (ValueError, IndexError):
        return False


def validate_types_file(file_path: Path | None = None) -> tuple[bool, list[str], set[str]]:
    """Validate the types JSON file.

    Args:
        file_path: Path to ccc_types.json. Defaults to data/seed/ccc_types.json.

    Returns:
        Tuple of (is_valid, error_messages, valid_type_ids).
    """
    if file_path is None:
        file_path = settings.DATA_DIR.parent / "seed" / "ccc_types.json"

    errors = []
    valid_type_ids = set()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return False, [f"Failed to load file: {e}"], set()

    if "types" not in data:
        return False, ["Missing 'types' array in file"], set()

    for i, type_data in enumerate(data["types"]):
        type_errors = validate_type(type_data)
        if type_errors:
            errors.extend([f"Type[{i}] ({type_data.get('id', 'unknown')}): {e}" for e in type_errors])
        else:
            valid_type_ids.add(type_data["id"])

    return len(errors) == 0, errors, valid_type_ids


def validate_prefigures_file(
    file_path: Path | None = None, valid_type_ids: set[str] | None = None
) -> tuple[bool, list[str]]:
    """Validate the PREFIGURES relationships JSON file.

    Args:
        file_path: Path to ccc_prefigures.json. Defaults to data/seed/ccc_prefigures.json.
        valid_type_ids: Set of valid Type IDs. If None, loads from types file.

    Returns:
        Tuple of (is_valid, error_messages).
    """
    if file_path is None:
        file_path = settings.DATA_DIR.parent / "seed" / "ccc_prefigures.json"

    if valid_type_ids is None:
        _, _, valid_type_ids = validate_types_file()

    errors = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return False, [f"Failed to load file: {e}"]

    if "relationships" not in data:
        return False, ["Missing 'relationships' array in file"]

    for i, rel_data in enumerate(data["relationships"]):
        rel_errors = validate_prefigures_relationship(rel_data, valid_type_ids)
        if rel_errors:
            desc = f"{rel_data.get('from_type', '?')}->{rel_data.get('to_type', '?')}"
            errors.extend([f"Relationship[{i}] ({desc}): {e}" for e in rel_errors])

    return len(errors) == 0, errors


def validate_memberships_file(
    file_path: Path | None = None, valid_type_ids: set[str] | None = None
) -> tuple[bool, list[str]]:
    """Validate the verse memberships JSON file.

    Args:
        file_path: Path to ccc_verse_memberships.json.
        valid_type_ids: Set of valid Type IDs. If None, loads from types file.

    Returns:
        Tuple of (is_valid, error_messages).
    """
    if file_path is None:
        file_path = settings.DATA_DIR.parent / "seed" / "ccc_verse_memberships.json"

    if valid_type_ids is None:
        _, _, valid_type_ids = validate_types_file()

    errors = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return False, [f"Failed to load file: {e}"]

    if "memberships" not in data:
        return False, ["Missing 'memberships' array in file"]

    for i, membership in enumerate(data["memberships"]):
        mem_errors = validate_verse_membership(membership, valid_type_ids)
        if mem_errors:
            errors.extend([f"Membership[{i}] ({membership.get('type_id', '?')}): {e}" for e in mem_errors])

    return len(errors) == 0, errors


def validate_teaches_file(
    file_path: Path | None = None, valid_type_ids: set[str] | None = None
) -> tuple[bool, list[str]]:
    """Validate the CCC TEACHES relationships JSON file.

    Args:
        file_path: Path to ccc_teaches.json.
        valid_type_ids: Set of valid Type IDs. If None, loads from types file.

    Returns:
        Tuple of (is_valid, error_messages).
    """
    if file_path is None:
        file_path = settings.DATA_DIR.parent / "seed" / "ccc_teaches.json"

    if valid_type_ids is None:
        _, _, valid_type_ids = validate_types_file()

    errors = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return False, [f"Failed to load file: {e}"]

    if "teaches" not in data:
        return False, ["Missing 'teaches' array in file"]

    for i, teaches in enumerate(data["teaches"]):
        teaches_errors = validate_teaches_relationship(teaches, valid_type_ids)
        if teaches_errors:
            errors.extend([f"Teaches[{i}] ({teaches.get('ccc_id', '?')}): {e}" for e in teaches_errors])

    return len(errors) == 0, errors


def validate_all_seed_files() -> tuple[bool, dict[str, list[str]]]:
    """Validate all seed data files.

    Returns:
        Tuple of (all_valid, errors_by_file).
    """
    all_errors = {}

    # Validate types first (needed for other validations)
    types_valid, types_errors, valid_type_ids = validate_types_file()
    if types_errors:
        all_errors["ccc_types.json"] = types_errors

    # Validate other files
    prefigures_valid, prefigures_errors = validate_prefigures_file(valid_type_ids=valid_type_ids)
    if prefigures_errors:
        all_errors["ccc_prefigures.json"] = prefigures_errors

    memberships_valid, memberships_errors = validate_memberships_file(valid_type_ids=valid_type_ids)
    if memberships_errors:
        all_errors["ccc_verse_memberships.json"] = memberships_errors

    teaches_valid, teaches_errors = validate_teaches_file(valid_type_ids=valid_type_ids)
    if teaches_errors:
        all_errors["ccc_teaches.json"] = teaches_errors

    all_valid = len(all_errors) == 0
    return all_valid, all_errors


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Validating typology seed files...")
    print("=" * 50)

    all_valid, all_errors = validate_all_seed_files()

    if all_valid:
        print("All files valid!")

        # Print statistics
        types_path = settings.DATA_DIR.parent / "seed" / "ccc_types.json"
        prefigures_path = settings.DATA_DIR.parent / "seed" / "ccc_prefigures.json"
        memberships_path = settings.DATA_DIR.parent / "seed" / "ccc_verse_memberships.json"
        teaches_path = settings.DATA_DIR.parent / "seed" / "ccc_teaches.json"

        with open(types_path) as f:
            types_data = json.load(f)
        with open(prefigures_path) as f:
            prefigures_data = json.load(f)
        with open(memberships_path) as f:
            memberships_data = json.load(f)
        with open(teaches_path) as f:
            teaches_data = json.load(f)

        print(f"\nStatistics:")
        print(f"  Types: {len(types_data['types'])}")
        print(f"    OT: {sum(1 for t in types_data['types'] if t['testament'] == 'OT')}")
        print(f"    NT: {sum(1 for t in types_data['types'] if t['testament'] == 'NT')}")
        print(f"  PREFIGURES relationships: {len(prefigures_data['relationships'])}")
        print(f"  MEMBER_OF mappings: {len(memberships_data['memberships'])}")
        total_verses = sum(len(m['verse_ids']) for m in memberships_data['memberships'])
        print(f"    Total verse references: {total_verses}")
        print(f"  TEACHES mappings: {len(teaches_data['teaches'])}")

    else:
        print("Validation errors found:\n")
        for filename, errors in all_errors.items():
            print(f"{filename}:")
            for error in errors:
                print(f"  - {error}")
            print()
