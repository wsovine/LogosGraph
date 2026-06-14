#!/usr/bin/env python3
"""Mine MEMBER_OF candidate verses from the cross-reference layer.

For each Type, finds verses cross-referenced by multiple existing member
verses (corroboration >= threshold), excluding high-degree hub verses.
Writes candidates to JSONL for LLM adjudication and human review -- this
script never writes to the database.

Usage:
    python scripts/mine_member_candidates.py
    python scripts/mine_member_candidates.py --min-corroboration 3 --max-degree 100
    python scripts/mine_member_candidates.py -o data/extracted/member_candidates.jsonl
"""

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.data.member_candidate_miner import (
    DEFAULT_MAX_DEGREE,
    DEFAULT_MIN_CORROBORATION,
    DEFAULT_PER_TYPE_CAP,
    mine_candidates,
)
from src.db.connection import get_connection

DEFAULT_OUTPUT = Path("data/extracted/member_candidates.jsonl")


def main():
    parser = argparse.ArgumentParser(
        description="Mine MEMBER_OF candidates from cross-references"
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Output JSONL file (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--min-corroboration", type=int, default=DEFAULT_MIN_CORROBORATION,
        help="Minimum distinct member verses cross-referencing the candidate "
             f"(default: {DEFAULT_MIN_CORROBORATION})",
    )
    parser.add_argument(
        "--max-degree", type=int, default=DEFAULT_MAX_DEGREE,
        help="Exclude candidates with more cross-references than this "
             f"(hub filter, default: {DEFAULT_MAX_DEGREE})",
    )
    parser.add_argument(
        "--per-type-cap", type=int, default=DEFAULT_PER_TYPE_CAP,
        help=f"Max candidates kept per type (default: {DEFAULT_PER_TYPE_CAP}; 0 disables)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    connection = get_connection()
    connection.verify()

    candidates = mine_candidates(
        connection,
        min_corroboration=args.min_corroboration,
        max_degree=args.max_degree,
        per_type_cap=args.per_type_cap or None,
    )

    if not candidates:
        print("No candidates found.")
        sys.exit(0)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for row in candidates:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    by_type = Counter(c["type_name"] for c in candidates)
    print()
    print("=" * 60)
    print("Candidate Mining Summary")
    print("=" * 60)
    print(f"  Candidates:          {len(candidates):,}")
    print(f"  Types touched:       {len(by_type)}")
    print(f"  Min corroboration:   {args.min_corroboration}")
    print(f"  Max candidate degree:{args.max_degree}")
    print()
    print("  Top types by candidate count:")
    for name, n in by_type.most_common(10):
        print(f"    {n:4d}  {name}")
    print("=" * 60)
    print(f"\nCandidates written to: {args.output}")
    print("\nNext steps:")
    print("  1. Adjudicate with: python scripts/adjudicate_memberships.py")
    print("  2. Then review with: python scripts/review_memberships.py")

    connection.close()


if __name__ == "__main__":
    main()
