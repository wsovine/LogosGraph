#!/usr/bin/env python3
"""Interactive human review of adjudicated MEMBER_OF candidates.

Walks through theologian-accepted candidates (and optionally rejected ones),
showing the verse text and the theologian's reasoning. Approved memberships
go to data/reviewed/ for import; nothing touches the database here.

Keys:  y = approve   n = reject   s = skip (decide later)   q = quit

Usage:
    python scripts/review_memberships.py
    python scripts/review_memberships.py --include-rejected
    python scripts/review_memberships.py --stats
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

DEFAULT_INPUT = Path("data/extracted/member_adjudicated.jsonl")
DEFAULT_APPROVED = Path("data/reviewed/member_of_approved.jsonl")
DEFAULT_REJECTED = Path("data/reviewed/member_of_rejected.jsonl")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def candidate_key(row: dict) -> str:
    return f"{row['verse_id']}|{row['type_id']}"


def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def show_stats(input_path: Path, approved_path: Path, rejected_path: Path) -> None:
    rows = load_jsonl(input_path)
    accepted = sum(1 for r in rows if r.get("adjudication", {}).get("action") == "accept")
    approved = len(load_jsonl(approved_path))
    rejected = len(load_jsonl(rejected_path))
    print("=" * 50)
    print("MEMBERSHIP REVIEW STATISTICS")
    print("=" * 50)
    print(f"  Adjudicated candidates:   {len(rows)}")
    print(f"  Theologian-accepted:      {accepted}")
    print(f"  Human-approved:           {approved}")
    print(f"  Human-rejected:           {rejected}")
    print(f"  Remaining (of accepted):  {max(0, accepted - approved - rejected)}")


def main():
    parser = argparse.ArgumentParser(
        description="Review adjudicated MEMBER_OF candidates"
    )
    parser.add_argument(
        "-i", "--input", type=Path, default=DEFAULT_INPUT,
        help=f"Adjudicated candidates JSONL (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--approved", type=Path, default=DEFAULT_APPROVED,
        help=f"Approved output JSONL (default: {DEFAULT_APPROVED})",
    )
    parser.add_argument(
        "--rejected", type=Path, default=DEFAULT_REJECTED,
        help=f"Rejected output JSONL (default: {DEFAULT_REJECTED})",
    )
    parser.add_argument(
        "--include-rejected", action="store_true",
        help="Also review candidates the theologian rejected",
    )
    parser.add_argument(
        "--stats", action="store_true", help="Show progress statistics and exit",
    )
    args = parser.parse_args()

    if args.stats:
        show_stats(args.input, args.approved, args.rejected)
        return

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        print("Run: python scripts/adjudicate_memberships.py")
        sys.exit(1)

    rows = load_jsonl(args.input)
    done = {candidate_key(r) for r in load_jsonl(args.approved)}
    done |= {candidate_key(r) for r in load_jsonl(args.rejected)}

    queue = [
        r for r in rows
        if candidate_key(r) not in done
        and (args.include_rejected
             or r.get("adjudication", {}).get("action") == "accept")
    ]

    if not queue:
        print("Nothing left to review.")
        show_stats(args.input, args.approved, args.rejected)
        return

    print(f"{len(queue)} candidates to review.  [y]es / [n]o / [s]kip / [q]uit\n")

    approved_n = rejected_n = 0
    for i, row in enumerate(queue, 1):
        adj = row.get("adjudication", {})
        print("-" * 70)
        print(f"[{i}/{len(queue)}]  {row['verse_id']}  ->  {row['type_name']} "
              f"({row.get('type_testament', '?')})")
        print(f"  Corroboration: {row.get('corroboration')} member verses; "
              f"degree {row.get('candidate_degree')}")
        print(f"  Text: {(row.get('verse_text') or '').strip()}")
        print(f"  Theologian: {adj.get('action', '?').upper()} "
              f"({adj.get('confidence', '?')}) -- {adj.get('reasoning', '')}")

        while True:
            choice = input("  Approve? [y/n/s/q] ").strip().lower()
            if choice in ("y", "n", "s", "q"):
                break
        if choice == "q":
            break
        if choice == "s":
            continue
        if choice == "y":
            append_row(args.approved, row)
            approved_n += 1
        else:
            append_row(args.rejected, row)
            rejected_n += 1

    print()
    print(f"Session: approved {approved_n}, rejected {rejected_n}")
    print(f"Approved file: {args.approved}")
    print("\nNext step:")
    print("  python scripts/import_memberships.py")


if __name__ == "__main__":
    main()
