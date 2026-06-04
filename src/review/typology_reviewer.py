"""Interactive reviewer for LLM-extracted typological relationships.

Provides a terminal-based interface for reviewing, approving, rejecting,
or modifying typology extractions before import into the knowledge graph.
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from typing import TYPE_CHECKING

from src.config import settings
from src.data.typology_schemas import VALID_CATEGORIES, VALID_CONFIDENCES

if TYPE_CHECKING:
    from src.review.ai_assistant import ReviewSuggestion, TheologyAssistant

logger = logging.getLogger(__name__)


def load_verse_texts(cpdv_path: Path | None = None) -> dict[str, str]:
    """Load verse texts from CPDV.json for display during review.

    Args:
        cpdv_path: Path to CPDV.json. Defaults to data/raw/CPDV.json.

    Returns:
        Dictionary mapping verse_id to verse text.
    """
    if cpdv_path is None:
        cpdv_path = settings.DATA_DIR / "CPDV.json"

    if not cpdv_path.exists():
        logger.warning(f"CPDV file not found: {cpdv_path}")
        return {}

    try:
        from src.data.cpdv_parser import parse_cpdv

        verses = {}
        for verse in parse_cpdv(cpdv_path):
            verses[verse["id"]] = verse["text"]
        return verses
    except Exception as e:
        logger.warning(f"Failed to load verse texts: {e}")
        return {}

# Path to seed types
SEED_TYPES_PATH = settings.DATA_DIR.parent / "seed" / "ccc_types.json"

# ANSI color codes for terminal output
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "red": "\033[31m",
}


def colorize(text: str, color: str) -> str:
    """Add ANSI color to text if terminal supports it."""
    if not sys.stdout.isatty():
        return text
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def load_existing_types(path: Path | None = None) -> dict[str, dict]:
    """Load existing Type definitions from seed data.

    Returns:
        Dict mapping type ID to type data.
    """
    if path is None:
        path = SEED_TYPES_PATH

    if not path.exists():
        logger.warning(f"Seed types file not found: {path}")
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return {t["id"]: t for t in data.get("types", [])}


def slugify(name: str) -> str:
    """Convert a name to a slug ID.

    Args:
        name: Human-readable name like "Adam's Creation"

    Returns:
        Slug like "adams-creation"
    """
    # Lowercase
    slug = name.lower()
    # Replace apostrophes and special chars with nothing
    slug = re.sub(r"[''`]", "", slug)
    # Replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)
    return slug


@dataclass
class ReviewDecision:
    """A single review decision for an extraction."""

    verse_id: str
    extraction_index: int
    action: str  # "approve", "reject", "modify", "skip"
    modified_data: dict[str, Any] | None = None
    reviewer_notes: str | None = None


@dataclass
class ReviewSession:
    """Tracks state of a review session."""

    input_file: Path
    approved_file: Path
    rejected_file: Path
    progress_file: Path
    new_types_file: Path | None = None

    items: list[dict] = field(default_factory=list)
    current_index: int = 0
    decisions: list[ReviewDecision] = field(default_factory=list)

    # Existing types from seed data
    existing_types: dict[str, dict] = field(default_factory=dict)
    # New types created during this session
    new_types: dict[str, dict] = field(default_factory=dict)
    # Verse texts for display
    verse_texts: dict[str, str] = field(default_factory=dict)

    # Statistics
    total_extractions: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    modified_count: int = 0
    skipped_count: int = 0
    new_types_count: int = 0

    def load_items(self) -> None:
        """Load extraction items from input file."""
        self.items = []
        with self.input_file.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    # Only include items that have typology
                    if item.get("has_typology") and item.get("extractions"):
                        self.items.append(item)

        # Count total extractions
        self.total_extractions = sum(
            len(item.get("extractions", [])) for item in self.items
        )

        # Load existing types from seed data
        self.existing_types = load_existing_types()

        # Load previously created new types
        self.load_new_types()

        # Load verse texts for display
        self.verse_texts = load_verse_texts()

    def get_all_types(self) -> dict[str, dict]:
        """Get all types (existing + new)."""
        all_types = dict(self.existing_types)
        all_types.update(self.new_types)
        return all_types

    def get_types_by_testament(self, testament: str) -> list[tuple[str, str]]:
        """Get types filtered by testament.

        Returns:
            List of (id, name) tuples sorted by name.
        """
        all_types = self.get_all_types()
        types = [
            (tid, t["name"])
            for tid, t in all_types.items()
            if t.get("testament") == testament
        ]
        return sorted(types, key=lambda x: x[1])

    def add_new_type(self, type_data: dict) -> str:
        """Add a new type to the session.

        Args:
            type_data: Type data with id, name, testament, category, etc.

        Returns:
            The type ID.
        """
        type_id = type_data["id"]
        self.new_types[type_id] = type_data
        self.new_types_count += 1
        return type_id

    def load_new_types(self) -> None:
        """Load previously created new types from file."""
        if self.new_types_file is None:
            self.new_types_file = self.approved_file.parent / "new_types.jsonl"

        if not self.new_types_file.exists():
            return

        try:
            with self.new_types_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        type_data = json.loads(line)
                        self.new_types[type_data["id"]] = type_data
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error loading new types file: {e}")

    def save_new_types(self) -> None:
        """Save new types created during review to a file."""
        if not self.new_types:
            return

        if self.new_types_file is None:
            self.new_types_file = self.approved_file.parent / "new_types.jsonl"

        self.new_types_file.parent.mkdir(parents=True, exist_ok=True)
        with self.new_types_file.open("w", encoding="utf-8") as f:
            for type_data in self.new_types.values():
                f.write(json.dumps(type_data, ensure_ascii=False) + "\n")

    def load_progress(self) -> None:
        """Load progress from previous session."""
        if not self.progress_file.exists():
            return

        try:
            with self.progress_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                self.current_index = data.get("current_index", 0)
                self.approved_count = data.get("approved_count", 0)
                self.rejected_count = data.get("rejected_count", 0)
                self.modified_count = data.get("modified_count", 0)
                self.skipped_count = data.get("skipped_count", 0)
        except (json.JSONDecodeError, KeyError):
            logger.warning("Invalid progress file, starting fresh")

    def save_progress(self) -> None:
        """Save current progress."""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with self.progress_file.open("w", encoding="utf-8") as f:
            json.dump({
                "current_index": self.current_index,
                "approved_count": self.approved_count,
                "rejected_count": self.rejected_count,
                "modified_count": self.modified_count,
                "skipped_count": self.skipped_count,
            }, f)

    def append_approved(
        self,
        item: dict,
        extraction: dict,
        type_id: str,
        antitype_id: str,
        notes: str | None = None,
    ) -> None:
        """Append an approved extraction to the approved file.

        Args:
            item: Original item with verse info.
            extraction: The extraction data (may be modified).
            type_id: ID of the OT type (existing or new).
            antitype_id: ID of the NT antitype (existing or new).
            notes: Optional reviewer notes.
        """
        record = {
            "verse_id": item["verse_id"],
            "book": item["book"],
            "chapter": item["chapter"],
            "verse": item["verse"],
            "original_text": item["original_text"],
            # Normalized type/antitype IDs for import
            "type_id": type_id,
            "antitype_id": antitype_id,
            # Category goes on the PREFIGURES relationship
            "category": extraction.get("category"),
            "confidence": extraction.get("confidence", "medium"),
            # Original extraction for reference
            "extraction": extraction,
            "reviewer_notes": notes,
            "source": "haydock",
        }
        self.approved_file.parent.mkdir(parents=True, exist_ok=True)
        with self.approved_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def append_rejected(self, item: dict, extraction: dict, notes: str | None = None) -> None:
        """Append a rejected extraction to the rejected file."""
        record = {
            "verse_id": item["verse_id"],
            "book": item["book"],
            "chapter": item["chapter"],
            "verse": item["verse"],
            "extraction": extraction,
            "rejection_reason": notes,
        }
        self.rejected_file.parent.mkdir(parents=True, exist_ok=True)
        with self.rejected_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


class TypologyReviewer:
    """Interactive terminal reviewer for typology extractions."""

    def __init__(
        self,
        session: ReviewSession,
        ai_assistant: "TheologyAssistant | None" = None,
    ):
        """Initialize reviewer with a session.

        Args:
            session: The review session to use.
            ai_assistant: Optional AI assistant for suggestions.
        """
        self.session = session
        self.ai_assistant = ai_assistant
        self._current_suggestion: "ReviewSuggestion | None" = None

    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        os.system("clear" if os.name == "posix" else "cls")

    def print_header(self) -> None:
        """Print the review session header."""
        s = self.session
        reviewed = s.approved_count + s.rejected_count + s.modified_count + s.skipped_count

        print(colorize("=" * 70, "dim"))
        print(colorize("TYPOLOGY REVIEW", "bold"))
        print(colorize("=" * 70, "dim"))
        print()
        print(f"Item {s.current_index + 1} of {len(s.items)} items")
        print(f"Progress: {reviewed}/{s.total_extractions} extractions reviewed")
        print(
            f"  {colorize(f'Approved: {s.approved_count}', 'green')}  "
            f"{colorize(f'Rejected: {s.rejected_count}', 'red')}  "
            f"{colorize(f'Modified: {s.modified_count}', 'yellow')}  "
            f"{colorize(f'Skipped: {s.skipped_count}', 'dim')}"
        )
        print()

    def print_item(self, item: dict, extraction_index: int = 0) -> None:
        """Print an extraction item for review."""
        extraction = item["extractions"][extraction_index]

        # Verse info
        print(colorize(f"VERSE: {item['verse_id']}", "cyan"))
        verse_text = self.session.verse_texts.get(item["verse_id"])
        if verse_text:
            # Truncate long verses
            if len(verse_text) > 200:
                verse_text = verse_text[:200] + "..."
            print(colorize(f'"{verse_text}"', "dim"))
        print(colorize("-" * 50, "dim"))
        print()

        # Original commentary (truncated if very long)
        text = item["original_text"]
        if len(text) > 500:
            text = text[:500] + "..."
        print(colorize("COMMENTARY:", "bold"))
        print(text)
        print()

        # Extraction
        print(colorize("EXTRACTED TYPOLOGY:", "bold"))
        print(colorize("-" * 30, "dim"))
        print(f"  Type (OT):     {colorize(extraction['type_name'], 'yellow')}")
        if extraction.get("type_description"):
            print(f"                 {colorize(extraction['type_description'], 'dim')}")
        print(f"  Antitype (NT): {colorize(extraction['antitype_name'], 'green')}")
        if extraction.get("antitype_description"):
            print(f"                 {colorize(extraction['antitype_description'], 'dim')}")
        print(f"  Category:      {extraction['category']}")
        print(f"  Confidence:    {extraction['confidence']}")
        if extraction.get("reasoning"):
            print()
            print(colorize("  Reasoning:", "dim"))
            print(f"  {extraction['reasoning']}")
        print()

        # Notes from LLM
        if item.get("notes"):
            print(colorize("LLM Notes:", "dim"))
            print(f"  {item['notes']}")
            print()

    def print_menu(self, has_suggestion: bool = False) -> None:
        """Print the action menu.

        Args:
            has_suggestion: Whether an AI suggestion is available.
        """
        print(colorize("ACTIONS:", "bold"))
        if has_suggestion:
            print(f"  [{colorize('y', 'cyan')}] Accept AI - Accept AI suggestion")
            print(f"  [{colorize('Enter', 'cyan')}]          - (same as 'y')")
        print(f"  [{colorize('a', 'green')}] Approve   - Accept this extraction as-is")
        print(f"  [{colorize('r', 'red')}] Reject    - Discard this extraction")
        print(f"  [{colorize('m', 'yellow')}] Modify    - Edit before approving")
        print(f"  [{colorize('s', 'dim')}] Skip      - Skip for now (review later)")
        print(f"  [{colorize('v', 'cyan')}] View full - Show full commentary text")
        print(f"  [{colorize('q', 'magenta')}] Quit      - Save and exit")
        print()

    def print_ai_suggestion(self, suggestion: "ReviewSuggestion") -> None:
        """Print the AI suggestion prominently.

        Args:
            suggestion: The AI's review suggestion.
        """
        print(colorize("=" * 70, "cyan"))
        print(colorize("AI ASSISTANT RECOMMENDATION", "cyan"))
        print(colorize("=" * 70, "cyan"))
        print()

        # Action with color
        if suggestion.action == "approve":
            action_str = colorize("APPROVE", "green")
        else:
            action_str = colorize("REJECT", "red")

        print(f"  Action: {action_str}")
        print(f"  Confidence: {colorize(f'{suggestion.confidence:.0%}', 'bold')}")
        print()

        # Reasoning
        print(colorize("  Reasoning:", "bold"))
        # Wrap reasoning text
        reasoning = suggestion.reasoning
        if len(reasoning) > 100:
            words = reasoning.split()
            lines = []
            current_line = "  "
            for word in words:
                if len(current_line) + len(word) + 1 > 70:
                    lines.append(current_line)
                    current_line = "  " + word
                else:
                    current_line += " " + word if current_line != "  " else word
            if current_line.strip():
                lines.append(current_line)
            print("\n".join(lines))
        else:
            print(f"  {reasoning}")
        print()

        # If approving, show suggested types
        if suggestion.action == "approve":
            print(colorize("  Suggested mappings:", "bold"))

            # Type
            if suggestion.type_id:
                type_info = self.session.get_all_types().get(suggestion.type_id, {})
                type_name = type_info.get("name", suggestion.type_id)
                print(f"    Type (OT):     {colorize(type_name, 'yellow')} ({suggestion.type_id})")
            elif suggestion.type_name:
                print(f"    Type (OT):     {colorize(suggestion.type_name, 'yellow')} {colorize('(NEW)', 'cyan')}")

            # Antitype
            if suggestion.antitype_id:
                antitype_info = self.session.get_all_types().get(suggestion.antitype_id, {})
                antitype_name = antitype_info.get("name", suggestion.antitype_id)
                print(f"    Antitype (NT): {colorize(antitype_name, 'green')} ({suggestion.antitype_id})")
            elif suggestion.antitype_name:
                print(f"    Antitype (NT): {colorize(suggestion.antitype_name, 'green')} {colorize('(NEW)', 'cyan')}")

            # Category
            if suggestion.category:
                print(f"    Category:      {colorize(suggestion.category, 'magenta')}")

        print()
        print(colorize("=" * 70, "cyan"))
        print()

    def get_input(self, prompt: str) -> str:
        """Get user input with prompt."""
        try:
            return input(colorize(prompt, "bold")).strip().lower()
        except EOFError:
            return "q"

    def modify_extraction(self, extraction: dict) -> dict:
        """Interactive modification of an extraction."""
        modified = extraction.copy()

        print()
        print(colorize("MODIFY EXTRACTION (press Enter to keep current value)", "yellow"))
        print()

        # Type name
        current = extraction["type_name"]
        new_value = input(f"  Type name [{current}]: ").strip()
        if new_value:
            modified["type_name"] = new_value

        # Antitype name
        current = extraction["antitype_name"]
        new_value = input(f"  Antitype name [{current}]: ").strip()
        if new_value:
            modified["antitype_name"] = new_value

        # Category
        current = extraction["category"]
        print(f"  Categories: {', '.join(sorted(VALID_CATEGORIES))}")
        new_value = input(f"  Category [{current}]: ").strip()
        if new_value:
            # Find matching category (case-insensitive)
            for cat in VALID_CATEGORIES:
                if cat.lower().startswith(new_value.lower()):
                    modified["category"] = cat
                    break

        # Confidence
        current = extraction["confidence"]
        print(f"  Confidence levels: {', '.join(sorted(VALID_CONFIDENCES))}")
        new_value = input(f"  Confidence [{current}]: ").strip()
        if new_value and new_value in VALID_CONFIDENCES:
            modified["confidence"] = new_value

        return modified

    def print_types_list(self, testament: str) -> None:
        """Print numbered list of types for a testament."""
        types = self.session.get_types_by_testament(testament)
        if not types:
            print(colorize(f"  No {testament} types defined yet.", "dim"))
            return

        for i, (tid, name) in enumerate(types, 1):
            print(f"  {i:2}. {name} ({colorize(tid, 'dim')})")

    def select_type(self, testament: str, suggested_name: str) -> tuple[str, bool]:
        """Interactive type selection.

        Args:
            testament: "OT" or "NT"
            suggested_name: The LLM-suggested name for this type.

        Returns:
            Tuple of (type_id, is_new_type)
        """
        types = self.session.get_types_by_testament(testament)
        label = "TYPE (OT)" if testament == "OT" else "ANTITYPE (NT)"

        print()
        print(colorize(f"SELECT {label}", "bold"))
        print(colorize(f"LLM suggested: {suggested_name}", "cyan"))
        print()
        print(f"Existing {testament} types:")
        self.print_types_list(testament)
        print()
        print(f"  [{colorize('n', 'yellow')}] Create NEW type")
        print()

        while True:
            choice = input(f"Enter number or 'n' for new: ").strip().lower()

            if choice == "n":
                # Create new type
                return self.create_new_type(testament, suggested_name)

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(types):
                    type_id = types[idx][0]
                    return type_id, False
                else:
                    print(colorize("Invalid number. Try again.", "red"))
            except ValueError:
                print(colorize("Enter a number or 'n'.", "red"))

    def create_new_type(self, testament: str, suggested_name: str) -> tuple[str, bool]:
        """Create a new type during review.

        Returns:
            Tuple of (type_id, True)
        """
        print()
        print(colorize("CREATE NEW TYPE", "yellow"))
        print()

        # Name
        name = input(f"  Name [{suggested_name}]: ").strip()
        if not name:
            name = suggested_name

        # Generate ID
        suggested_id = slugify(name)
        type_id = input(f"  ID [{suggested_id}]: ").strip()
        if not type_id:
            type_id = suggested_id

        # Check for collision
        all_types = self.session.get_all_types()
        if type_id in all_types:
            print(colorize(f"  Type ID '{type_id}' already exists!", "red"))
            use_existing = input("  Use existing type? [Y/n]: ").strip().lower()
            if use_existing != "n":
                return type_id, False
            # Let them try again
            return self.create_new_type(testament, suggested_name)

        # Description (optional)
        description = input("  Description (optional): ").strip()

        # Create type data (no category - that goes on PREFIGURES relationship)
        type_data = {
            "id": type_id,
            "name": name,
            "testament": testament,
            "description": description or None,
            "source": "haydock-review",
            "confidence": "medium",
            "reviewed": True,
        }

        self.session.add_new_type(type_data)
        print(colorize(f"  Created new type: {type_id}", "green"))

        return type_id, True

    def select_category(self, current: str) -> str:
        """Select or confirm the category for the relationship.

        Args:
            current: The current/suggested category.

        Returns:
            Selected category.
        """
        print()
        print(colorize("CATEGORY (for PREFIGURES relationship)", "bold"))
        print(f"LLM suggested: {colorize(current, 'cyan')}")
        print()

        categories = sorted(VALID_CATEGORIES)
        for i, cat in enumerate(categories, 1):
            marker = " *" if cat == current else ""
            print(f"  {i}. {cat}{marker}")
        print()

        choice = input(f"Enter number or press Enter to keep [{current}]: ").strip()

        if not choice:
            return current

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(categories):
                return categories[idx]
        except ValueError:
            pass

        print(colorize(f"Keeping: {current}", "dim"))
        return current

    def accept_ai_suggestion(
        self,
        item: dict,
        extraction: dict,
        suggestion: "ReviewSuggestion",
    ) -> bool:
        """Accept an AI suggestion, handling both approval and rejection.

        Args:
            item: The original item.
            extraction: The extraction data.
            suggestion: The AI's suggestion.

        Returns:
            True if the action was successful, False if cancelled.
        """
        if suggestion.action == "reject":
            # Handle rejection
            print()
            print(colorize("AI suggests REJECTING this extraction.", "red"))
            print(f"Reason: {suggestion.reasoning}")
            print()
            confirm = input("Accept AI rejection? [Y/n]: ").strip().lower()
            if confirm == "n":
                print("Cancelled.")
                input("Press Enter to continue...")
                return False

            self.session.append_rejected(item, extraction, f"AI: {suggestion.reasoning}")
            self.session.rejected_count += 1
            print(colorize("Rejected!", "red"))
            input("Press Enter to continue...")
            return True

        # Handle approval
        print()
        print(colorize("Accepting AI suggestion for APPROVAL:", "green"))

        # Determine type_id
        type_id = suggestion.type_id
        type_is_new = False
        if not type_id and suggestion.type_name:
            # Create new type
            type_id = slugify(suggestion.type_name)
            if type_id not in self.session.get_all_types():
                type_data = {
                    "id": type_id,
                    "name": suggestion.type_name,
                    "testament": "OT",
                    "description": None,
                    "source": "haydock-review-ai",
                    "confidence": "medium",
                    "reviewed": True,
                }
                self.session.add_new_type(type_data)
                type_is_new = True
                print(f"  Created new OT type: {colorize(suggestion.type_name, 'yellow')} ({type_id})")

        # Determine antitype_id
        antitype_id = suggestion.antitype_id
        antitype_is_new = False
        if not antitype_id and suggestion.antitype_name:
            # Create new antitype
            antitype_id = slugify(suggestion.antitype_name)
            if antitype_id not in self.session.get_all_types():
                antitype_data = {
                    "id": antitype_id,
                    "name": suggestion.antitype_name,
                    "testament": "NT",
                    "description": None,
                    "source": "haydock-review-ai",
                    "confidence": "medium",
                    "reviewed": True,
                }
                self.session.add_new_type(antitype_data)
                antitype_is_new = True
                print(f"  Created new NT type: {colorize(suggestion.antitype_name, 'green')} ({antitype_id})")

        # Use suggested category or fall back to extraction
        category = suggestion.category or extraction.get("category", "Christological")

        # Update extraction with confirmed category
        updated_extraction = dict(extraction)
        updated_extraction["category"] = category

        # Show summary
        print()
        print(colorize("SUMMARY:", "bold"))
        type_info = self.session.get_all_types().get(type_id, {})
        antitype_info = self.session.get_all_types().get(antitype_id, {})
        print(f"  Type:     {colorize(type_info.get('name', type_id), 'yellow')}" + (" (NEW)" if type_is_new else ""))
        print(f"  Antitype: {colorize(antitype_info.get('name', antitype_id), 'green')}" + (" (NEW)" if antitype_is_new else ""))
        print(f"  Category: {colorize(category, 'magenta')}")
        print(f"  Verse:    {item['verse_id']}")

        confirm = input("\nConfirm approval? [Y/n]: ").strip().lower()
        if confirm == "n":
            print("Cancelled.")
            input("Press Enter to continue...")
            return False

        # Save
        self.session.append_approved(
            item, updated_extraction, type_id, antitype_id, f"AI-assisted: {suggestion.reasoning}"
        )
        self.session.approved_count += 1

        print(colorize("Approved!", "green"))
        input("Press Enter to continue...")
        return True

    def approve_extraction(self, item: dict, extraction: dict, is_modified: bool = False) -> None:
        """Handle the approval workflow including type selection.

        Args:
            item: The original item.
            extraction: The extraction (possibly modified).
            is_modified: Whether the extraction was modified.
        """
        # Select OT type
        type_id, type_is_new = self.select_type("OT", extraction["type_name"])

        # Select NT antitype
        antitype_id, antitype_is_new = self.select_type("NT", extraction["antitype_name"])

        # Select/confirm category
        category = self.select_category(extraction.get("category", "Christological"))

        # Update extraction with confirmed category
        extraction = dict(extraction)  # Copy
        extraction["category"] = category

        # Reviewer notes
        notes = input("\nReviewer notes (optional): ").strip() or None

        # Confirm
        print()
        print(colorize("SUMMARY:", "bold"))
        print(f"  Type:     {colorize(type_id, 'yellow')}" + (" (NEW)" if type_is_new else ""))
        print(f"  Antitype: {colorize(antitype_id, 'green')}" + (" (NEW)" if antitype_is_new else ""))
        print(f"  Category: {colorize(category, 'magenta')}")
        print(f"  Verse:    {item['verse_id']}")

        confirm = input("\nConfirm approval? [Y/n]: ").strip().lower()
        if confirm == "n":
            print("Cancelled.")
            input("Press Enter to continue...")
            return

        # Save
        self.session.append_approved(item, extraction, type_id, antitype_id, notes)
        if is_modified:
            self.session.modified_count += 1
        else:
            self.session.approved_count += 1

        print(colorize("Approved!", "green"))
        input("Press Enter to continue...")

    def review_item(self, item: dict) -> bool:
        """Review a single item. Returns False if user wants to quit."""
        extractions = item.get("extractions", [])

        for i, extraction in enumerate(extractions):
            # Get AI suggestion if assistant is available
            suggestion: "ReviewSuggestion | None" = None
            if self.ai_assistant:
                print(colorize("Getting AI suggestion...", "dim"))
                self.ai_assistant.update_types(self.session.get_all_types())
                suggestion = self.ai_assistant.get_suggestion(item, extraction)
                self._current_suggestion = suggestion

            while True:
                self.clear_screen()
                self.print_header()

                if len(extractions) > 1:
                    print(colorize(f"Extraction {i + 1} of {len(extractions)}", "magenta"))
                    print()

                self.print_item(item, i)

                # Show AI suggestion if available
                if suggestion:
                    self.print_ai_suggestion(suggestion)

                self.print_menu(has_suggestion=suggestion is not None)

                action = self.get_input("Action: ")

                # Handle 'y' or Enter to accept AI suggestion
                if action in ("y", "") and suggestion:
                    if self.accept_ai_suggestion(item, extraction, suggestion):
                        break
                    # If cancelled, loop continues

                elif action == "a":
                    # Approve - now includes type selection
                    self.approve_extraction(item, extraction, is_modified=False)
                    break

                elif action == "r":
                    # Reject
                    reason = input("Rejection reason (optional): ").strip() or None
                    self.session.append_rejected(item, extraction, reason)
                    self.session.rejected_count += 1
                    break

                elif action == "m":
                    # Modify
                    modified = self.modify_extraction(extraction)
                    print()
                    print(colorize("Modified extraction:", "yellow"))
                    print(f"  Type: {modified['type_name']} → {modified['antitype_name']}")
                    print(f"  Category: {modified['category']}, Confidence: {modified['confidence']}")
                    confirm = input("Proceed with approval? [Y/n]: ").strip().lower()
                    if confirm != "n":
                        self.approve_extraction(item, modified, is_modified=True)
                        break

                elif action == "s":
                    # Skip
                    self.session.skipped_count += 1
                    break

                elif action == "v":
                    # View full text
                    self.clear_screen()
                    print(colorize("FULL COMMENTARY TEXT:", "bold"))
                    print(colorize("=" * 70, "dim"))
                    print(item["original_text"])
                    print(colorize("=" * 70, "dim"))
                    input("\nPress Enter to continue...")

                elif action == "q":
                    return False

                elif action == "" and not suggestion:
                    # Empty input without AI suggestion - ignore
                    print(colorize("Invalid action. Try again.", "red"))
                    input("Press Enter...")

                else:
                    print(colorize("Invalid action. Try again.", "red"))
                    input("Press Enter...")

        return True

    def run(self) -> None:
        """Run the interactive review session."""
        print("Loading extractions...")
        self.session.load_items()
        self.session.load_progress()

        if not self.session.items:
            print("No items with typology extractions found.")
            return

        print(f"Found {len(self.session.items)} items with {self.session.total_extractions} extractions")
        print(f"Loaded {len(self.session.existing_types)} existing types from seed data")
        if self.session.new_types:
            print(f"Loaded {len(self.session.new_types)} new types from previous sessions")
        if self.session.verse_texts:
            print(f"Loaded {len(self.session.verse_texts)} verse texts for display")

        if self.session.current_index > 0:
            print(f"Resuming from item {self.session.current_index + 1}")

        input("Press Enter to start reviewing...")

        try:
            while self.session.current_index < len(self.session.items):
                item = self.session.items[self.session.current_index]

                if not self.review_item(item):
                    # User quit
                    break

                self.session.current_index += 1
                self.session.save_progress()

            else:
                # Completed all items
                self.clear_screen()
                print(colorize("REVIEW COMPLETE!", "green"))
                print()

        finally:
            self.session.save_progress()
            self.session.save_new_types()
            self.print_summary()

    def print_summary(self) -> None:
        """Print final review summary."""
        s = self.session
        print()
        print(colorize("=" * 50, "dim"))
        print(colorize("REVIEW SESSION SUMMARY", "bold"))
        print(colorize("=" * 50, "dim"))
        print(f"  Items processed: {s.current_index}/{len(s.items)}")
        print(f"  {colorize(f'Approved: {s.approved_count}', 'green')}")
        print(f"  {colorize(f'Rejected: {s.rejected_count}', 'red')}")
        print(f"  {colorize(f'Modified: {s.modified_count}', 'yellow')}")
        print(f"  {colorize(f'Skipped:  {s.skipped_count}', 'dim')}")
        if s.new_types_count > 0:
            print(f"  {colorize(f'New types created: {s.new_types_count}', 'cyan')}")
        print()
        print(f"Approved extractions: {s.approved_file}")
        print(f"Rejected extractions: {s.rejected_file}")
        if s.new_types_count > 0 and s.new_types_file:
            print(f"New types: {s.new_types_file}")
        print(f"Progress saved to: {s.progress_file}")
        print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Default paths
    input_file = Path("data/extracted/haydock_typology_raw.jsonl")
    approved_file = Path("data/reviewed/typology_approved.jsonl")
    rejected_file = Path("data/reviewed/typology_rejected.jsonl")
    progress_file = Path("data/reviewed/.review_progress.json")

    if not input_file.exists():
        print(f"Input file not found: {input_file}")
        print("Run extract_typology_llm.py first to generate extractions.")
        sys.exit(1)

    session = ReviewSession(
        input_file=input_file,
        approved_file=approved_file,
        rejected_file=rejected_file,
        progress_file=progress_file,
    )

    reviewer = TypologyReviewer(session)
    reviewer.run()
