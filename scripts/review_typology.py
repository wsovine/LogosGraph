#!/usr/bin/env python3
"""Interactive review of LLM-extracted typological relationships.

This script provides a terminal-based interface for reviewing extractions
before importing them into the knowledge graph.

Usage:
    python scripts/review_typology.py
    python scripts/review_typology.py --input data/extracted/haydock_typology_raw.jsonl
    python scripts/review_typology.py --stats
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.review.typology_reviewer import ReviewSession, TypologyReviewer

# Default paths
DEFAULT_INPUT = Path("data/extracted/haydock_typology_raw.jsonl")
DEFAULT_APPROVED = Path("data/reviewed/typology_approved.jsonl")
DEFAULT_REJECTED = Path("data/reviewed/typology_rejected.jsonl")
DEFAULT_PROGRESS = Path("data/reviewed/.review_progress.json")


def show_stats(input_path: Path, approved_path: Path, rejected_path: Path) -> None:
    """Show statistics about extractions and review progress."""
    print("=" * 50)
    print("TYPOLOGY REVIEW STATISTICS")
    print("=" * 50)
    print()

    # Count raw extractions
    total_items = 0
    items_with_typology = 0
    total_extractions = 0

    if input_path.exists():
        with input_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    total_items += 1
                    if item.get("has_typology") and item.get("extractions"):
                        items_with_typology += 1
                        total_extractions += len(item["extractions"])

    print(f"Raw extractions ({input_path}):")
    print(f"  Total items processed:     {total_items}")
    print(f"  Items with typology:       {items_with_typology}")
    print(f"  Total extractions to review: {total_extractions}")
    print()

    # Count approved
    approved_count = 0
    if approved_path.exists():
        with approved_path.open("r", encoding="utf-8") as f:
            approved_count = sum(1 for line in f if line.strip())

    # Count rejected
    rejected_count = 0
    if rejected_path.exists():
        with rejected_path.open("r", encoding="utf-8") as f:
            rejected_count = sum(1 for line in f if line.strip())

    reviewed = approved_count + rejected_count
    remaining = total_extractions - reviewed

    print(f"Review progress:")
    print(f"  Approved:  {approved_count}")
    print(f"  Rejected:  {rejected_count}")
    print(f"  Reviewed:  {reviewed}/{total_extractions}")
    print(f"  Remaining: {remaining}")

    if total_extractions > 0:
        pct = (reviewed / total_extractions) * 100
        print(f"  Progress:  {pct:.1f}%")

    print()

    # Show sample approved if any
    if approved_count > 0 and approved_path.exists():
        print("Recent approved extractions:")
        with approved_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-3:]:  # Last 3
                item = json.loads(line)
                ext = item["extraction"]
                print(f"  - {item['verse_id']}: {ext['type_name']} → {ext['antitype_name']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Interactive review of LLM-extracted typological relationships"
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input JSONL file with raw extractions (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--approved",
        type=Path,
        default=DEFAULT_APPROVED,
        help=f"Output file for approved extractions (default: {DEFAULT_APPROVED})",
    )
    parser.add_argument(
        "--rejected",
        type=Path,
        default=DEFAULT_REJECTED,
        help=f"Output file for rejected extractions (default: {DEFAULT_REJECTED})",
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=DEFAULT_PROGRESS,
        help=f"Progress file for resume support (default: {DEFAULT_PROGRESS})",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics and exit without starting review",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset progress and start review from beginning",
    )
    parser.add_argument(
        "--ai-assist",
        action="store_true",
        help="Enable AI assistant for review suggestions (uses Claude Haiku)",
    )

    args = parser.parse_args()

    # Show stats only
    if args.stats:
        show_stats(args.input, args.approved, args.rejected)
        return

    # Validate input file
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        print()
        print("Run the extraction first:")
        print("  python scripts/extract_typology_llm.py")
        sys.exit(1)

    # Reset progress if requested
    if args.reset:
        if args.progress.exists():
            args.progress.unlink()
            print("Progress reset.")
        if args.approved.exists():
            confirm = input(f"Also delete {args.approved}? [y/N]: ").strip().lower()
            if confirm == "y":
                args.approved.unlink()
        if args.rejected.exists():
            confirm = input(f"Also delete {args.rejected}? [y/N]: ").strip().lower()
            if confirm == "y":
                args.rejected.unlink()
        print()

    # Create session
    session = ReviewSession(
        input_file=args.input,
        approved_file=args.approved,
        rejected_file=args.rejected,
        progress_file=args.progress,
    )

    # Initialize AI assistant if requested
    ai_assistant = None
    if args.ai_assist:
        try:
            from src.review.ai_assistant import TheologyAssistant
        except ImportError as e:
            print(f"Error: --ai-assist requires the 'anthropic' package: {e}")
            print("Install with: uv sync")
            sys.exit(1)

        print("Initializing AI assistant...")
        # Need to load items first to get existing types
        session.load_items()
        all_types = session.get_all_types()
        ai_assistant = TheologyAssistant(all_types)
        print(f"AI assistant ready (using {ai_assistant.model})")
        print(f"  {len(ai_assistant.ot_types)} OT types, {len(ai_assistant.nt_types)} NT types loaded")
        print()

    # Run reviewer
    reviewer = TypologyReviewer(session, ai_assistant=ai_assistant)
    reviewer.run()


if __name__ == "__main__":
    main()
