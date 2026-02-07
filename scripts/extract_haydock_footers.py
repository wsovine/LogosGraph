#!/usr/bin/env python3
"""Extract Haydock commentary footers to JSONL format.

This script extracts all footer comments from Haydock USFM files and
optionally filters for typology-related content.

Usage:
    python scripts/extract_haydock_footers.py
    python scripts/extract_haydock_footers.py --filter-typology
    python scripts/extract_haydock_footers.py -v --output data/extracted/custom.jsonl
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from tqdm import tqdm

from src.data.haydock_footer_parser import parse_haydock_footers

logger = logging.getLogger(__name__)

# Keywords that suggest typological content in commentary
# These are common phrases used to describe OT/NT type relationships
TYPOLOGY_KEYWORDS = [
    r"\btype of\b",
    r"\bfigure of\b",
    r"\bprefigure",
    r"\bforeshadow",
    r"\bshadow of\b",
    r"\bimage of\b",
    r"\brepresent",
    r"\btypif",  # matches typify, typified, typifies, typical
    r"\bantitype",
    r"\bfulfill",  # matches fulfill, fulfilled, fulfillment
    r"\bsymbol",
]

# Compile patterns for efficient matching
_TYPOLOGY_PATTERNS = [re.compile(kw, re.IGNORECASE) for kw in TYPOLOGY_KEYWORDS]


def has_typology_keywords(text: str) -> list[str]:
    """Check if text contains typology-related keywords.

    Args:
        text: Commentary text to check

    Returns:
        List of matched keyword patterns (empty if none found)
    """
    matches = []
    for pattern in _TYPOLOGY_PATTERNS:
        if pattern.search(text):
            matches.append(pattern.pattern)
    return matches


def write_jsonl(filepath: Path, records: list[dict]) -> int:
    """Write records to a JSONL file.

    Args:
        filepath: Output file path
        records: List of dicts to write

    Returns:
        Number of records written
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(records)


def main():
    parser = argparse.ArgumentParser(
        description="Extract Haydock commentary footers to JSONL format"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/extracted/haydock_footers.jsonl"),
        help="Output file path (default: data/extracted/haydock_footers.jsonl)",
    )
    parser.add_argument(
        "--filter-typology",
        action="store_true",
        help="Also output filtered typology candidates to separate file",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )

    print("Extracting Haydock commentary footers...")
    print()

    # Collect all footers with progress bar
    all_footers = []
    typology_candidates = []
    books_seen = set()

    # First pass to count (for progress bar)
    # We know from testing there are ~21,349 footers
    footer_generator = parse_haydock_footers()

    for footer in tqdm(footer_generator, desc="Parsing footers", unit="footer"):
        all_footers.append(footer)
        books_seen.add(footer["book"])

        # Check for typology keywords if filtering enabled
        if args.filter_typology:
            matches = has_typology_keywords(footer["text"])
            if matches:
                # Add matched keywords to the record
                candidate = footer.copy()
                candidate["matched_keywords"] = matches
                typology_candidates.append(candidate)

    # Write full footers
    print()
    count = write_jsonl(args.output, all_footers)
    print(f"Wrote {count:,} footers to {args.output}")

    # Write typology candidates if filtering enabled
    if args.filter_typology:
        candidates_path = args.output.parent / "haydock_typology_candidates.jsonl"
        candidate_count = write_jsonl(candidates_path, typology_candidates)
        print(f"Wrote {candidate_count:,} typology candidates to {candidates_path}")

    # Print statistics
    print()
    print("Statistics:")
    print(f"  Total footers: {len(all_footers):,}")
    print(f"  Books processed: {len(books_seen)}")

    if args.filter_typology:
        print(f"  Typology candidates: {len(typology_candidates):,}")
        pct = (len(typology_candidates) / len(all_footers) * 100) if all_footers else 0
        print(f"  Filter rate: {pct:.1f}%")

        # Show keyword distribution
        if typology_candidates:
            keyword_counts = {}
            for candidate in typology_candidates:
                for kw in candidate["matched_keywords"]:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

            print()
            print("Keyword matches:")
            for kw, count in sorted(
                keyword_counts.items(), key=lambda x: -x[1]
            ):
                print(f"    {kw}: {count:,}")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
