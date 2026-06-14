#!/usr/bin/env python3
"""Adjudicate mined MEMBER_OF candidates with the theologian persona.

Each candidate from scripts/mine_member_candidates.py is judged against its
actual verse text by an LLM running the theologian persona
(.claude/agents/theologian.md). Verdicts are appended to JSONL for human
review -- this script never writes to the database.

Usage:
    python scripts/adjudicate_memberships.py
    python scripts/adjudicate_memberships.py --limit 10 --verbose
    python scripts/adjudicate_memberships.py --resume
    python scripts/adjudicate_memberships.py --model claude-opus-4-8
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from tqdm import tqdm

from src.config import settings
from src.review.member_adjudicator import DEFAULT_MODEL, MembershipAdjudicator

DEFAULT_INPUT = Path("data/extracted/member_candidates.jsonl")
DEFAULT_OUTPUT = Path("data/extracted/member_adjudicated.jsonl")
DEFAULT_CHECKPOINT = Path("data/extracted/.member_adjudication_checkpoint.json")


def candidate_key(candidate: dict) -> str:
    """Unique key for a (verse, type) candidate pair."""
    return f"{candidate['verse_id']}|{candidate['type_id']}"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_checkpoint(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        with path.open("r", encoding="utf-8") as f:
            return set(json.load(f).get("processed_keys", []))
    except (json.JSONDecodeError, KeyError):
        logging.warning("Invalid checkpoint file, starting fresh")
        return set()


def save_checkpoint(path: Path, processed: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump({"processed_keys": list(processed)}, f)


def main():
    parser = argparse.ArgumentParser(
        description="Adjudicate MEMBER_OF candidates with the theologian persona"
    )
    parser.add_argument(
        "-i", "--input", type=Path, default=DEFAULT_INPUT,
        help=f"Input JSONL of mined candidates (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Output JSONL of verdicts (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--checkpoint", type=Path, default=DEFAULT_CHECKPOINT,
        help=f"Checkpoint file for resume (default: {DEFAULT_CHECKPOINT})",
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL}; "
             "claude-opus-4-8 matches the interactive review assistant)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=25,
        help="Candidates between checkpoint saves (default: 25)",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit number of candidates to process (for testing)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from checkpoint, skipping already-processed candidates",
    )
    parser.add_argument(
        "--rate-limit", type=int, default=50,
        help="Max requests per minute (default: 50)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if not settings.ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not set (environment or .env)")
        sys.exit(1)
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        print("Run: python scripts/mine_member_candidates.py")
        sys.exit(1)

    all_candidates = load_jsonl(args.input)
    print(f"Loaded {len(all_candidates):,} candidates from {args.input}")

    processed = load_checkpoint(args.checkpoint) if args.resume else set()
    if processed:
        print(f"Resuming: {len(processed):,} already processed")

    candidates = [c for c in all_candidates if candidate_key(c) not in processed]
    if not candidates:
        print("No new candidates to process.")
        sys.exit(0)
    if args.limit:
        candidates = candidates[: args.limit]
        print(f"Limited to {len(candidates):,} candidates")

    print(f"\nAdjudicating {len(candidates):,} candidates with {args.model}...\n")

    adjudicator = MembershipAdjudicator(model=args.model)
    min_interval = 60.0 / args.rate_limit
    accepted = rejected = errors = 0
    input_tokens = output_tokens = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)

    try:
        with tqdm(candidates, desc="Adjudicating", unit="candidate") as pbar:
            for i, candidate in enumerate(pbar):
                started = time.monotonic()
                verdict = adjudicator.adjudicate(candidate)

                row = dict(candidate)
                row["adjudication"] = {
                    "action": verdict.action,
                    "confidence": verdict.confidence,
                    "reasoning": verdict.reasoning,
                    "model": args.model,
                    "error": verdict.error,
                }
                with args.output.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

                processed.add(candidate_key(candidate))
                input_tokens += verdict.input_tokens
                output_tokens += verdict.output_tokens
                if verdict.error:
                    errors += 1
                elif verdict.action == "accept":
                    accepted += 1
                else:
                    rejected += 1
                pbar.set_postfix({"accept": accepted, "reject": rejected,
                                  "errors": errors})

                if (i + 1) % args.batch_size == 0:
                    save_checkpoint(args.checkpoint, processed)

                # Rate limiting
                elapsed = time.monotonic() - started
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)

    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving checkpoint...")
        save_checkpoint(args.checkpoint, processed)
        print("Checkpoint saved. Use --resume to continue.")
        sys.exit(1)

    save_checkpoint(args.checkpoint, processed)

    total = accepted + rejected + errors
    print()
    print("=" * 60)
    print("Adjudication Summary")
    print("=" * 60)
    print(f"  Processed:      {total:,}")
    print(f"  Accepted:       {accepted:,}")
    print(f"  Rejected:       {rejected:,}")
    print(f"  Errors:         {errors:,}")
    print(f"  Input tokens:   {input_tokens:,}")
    print(f"  Output tokens:  {output_tokens:,}")
    print("=" * 60)
    print(f"\nVerdicts written to: {args.output}")
    print("\nNext step:")
    print("  python scripts/review_memberships.py")


if __name__ == "__main__":
    main()
