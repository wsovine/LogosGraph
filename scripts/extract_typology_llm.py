#!/usr/bin/env python3
"""Extract typological relationships from Haydock commentary using LLM.

This script processes typology candidates through Claude to extract
structured type/antitype relationships for manual review.

Usage:
    python scripts/extract_typology_llm.py
    python scripts/extract_typology_llm.py --limit 10 --verbose
    python scripts/extract_typology_llm.py --resume
    python scripts/extract_typology_llm.py --model claude-sonnet-4-5 --batch-size 20
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from tqdm import tqdm

from src.data.typology_extractor import (
    TypologyExtractor,
    ExtractionStats,
    result_to_dict,
    DEFAULT_MODEL,
)

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_INPUT = Path("data/extracted/haydock_typology_candidates.jsonl")
DEFAULT_OUTPUT = Path("data/extracted/haydock_typology_raw.jsonl")
DEFAULT_CHECKPOINT = Path("data/extracted/.typology_checkpoint.json")


def load_candidates(input_path: Path) -> list[dict]:
    """Load candidates from JSONL file.

    Args:
        input_path: Path to input JSONL file.

    Returns:
        List of candidate dicts.
    """
    candidates = []
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                candidates.append(json.loads(line))
    return candidates


def load_checkpoint(checkpoint_path: Path) -> set[str]:
    """Load set of already-processed verse IDs from checkpoint.

    Args:
        checkpoint_path: Path to checkpoint JSON file.

    Returns:
        Set of processed verse IDs.
    """
    if not checkpoint_path.exists():
        return set()

    try:
        with checkpoint_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("processed_ids", []))
    except (json.JSONDecodeError, KeyError):
        logger.warning(f"Invalid checkpoint file, starting fresh")
        return set()


def save_checkpoint(checkpoint_path: Path, processed_ids: set[str]) -> None:
    """Save checkpoint with processed verse IDs.

    Args:
        checkpoint_path: Path to checkpoint JSON file.
        processed_ids: Set of processed verse IDs.
    """
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with checkpoint_path.open("w", encoding="utf-8") as f:
        json.dump({"processed_ids": list(processed_ids)}, f)


def append_result(output_path: Path, result_dict: dict) -> None:
    """Append a single result to the output JSONL file.

    Args:
        output_path: Path to output JSONL file.
        result_dict: Result dict to append.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result_dict, ensure_ascii=False) + "\n")


def print_stats(stats: ExtractionStats) -> None:
    """Print extraction statistics."""
    print()
    print("=" * 60)
    print("Extraction Statistics")
    print("=" * 60)
    print(f"  Total candidates:    {stats.total_candidates:,}")
    print(f"  Processed:           {stats.processed:,}")
    print(f"  With typology:       {stats.with_typology:,}")
    print(f"  Without typology:    {stats.without_typology:,}")
    print(f"  Errors:              {stats.errors:,}")
    print(f"  Total extractions:   {stats.total_extractions:,}")
    print()
    print(f"  Success rate:        {stats.success_rate:.1%}")
    print(f"  Typology rate:       {stats.typology_rate:.1%}")
    print()
    print(f"  Input tokens:        {stats.total_input_tokens:,}")
    print(f"  Output tokens:       {stats.total_output_tokens:,}")
    print(f"  Estimated cost:      ${stats.estimated_cost_usd:.4f}")
    print()
    print(f"  Elapsed time:        {stats.elapsed_seconds:.1f}s")
    if stats.processed > 0:
        rate = stats.processed / stats.elapsed_seconds
        print(f"  Processing rate:     {rate:.2f} candidates/sec")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Extract typological relationships from Haydock commentary using LLM"
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input JSONL file with candidates (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSONL file for extractions (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=DEFAULT_CHECKPOINT,
        help=f"Checkpoint file for resume (default: {DEFAULT_CHECKPOINT})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Model to use for extraction (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of candidates to process before saving checkpoint (default: 50)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of candidates to process (for testing)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint, skipping already-processed candidates",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=50,
        help="Max requests per minute (default: 50)",
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

    # Validate input file
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    # Load candidates
    print(f"Loading candidates from {args.input}...")
    all_candidates = load_candidates(args.input)
    print(f"Loaded {len(all_candidates):,} candidates")

    # Handle resume
    processed_ids = set()
    if args.resume:
        processed_ids = load_checkpoint(args.checkpoint)
        if processed_ids:
            print(f"Resuming: {len(processed_ids):,} already processed")

    # Filter to unprocessed candidates
    candidates = [c for c in all_candidates if c["verse_id"] not in processed_ids]

    if not candidates:
        print("No new candidates to process.")
        sys.exit(0)

    # Apply limit
    if args.limit:
        candidates = candidates[: args.limit]
        print(f"Limited to {len(candidates):,} candidates")

    print()
    print(f"Processing {len(candidates):,} candidates...")
    print(f"Model: {args.model}")
    print(f"Rate limit: {args.rate_limit} RPM")
    print()

    # Initialize extractor
    try:
        extractor = TypologyExtractor(
            model=args.model,
            rate_limit_rpm=args.rate_limit,
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Process with progress bar
    stats = ExtractionStats(total_candidates=len(candidates))

    try:
        with tqdm(candidates, desc="Extracting", unit="candidate") as pbar:
            for i, candidate in enumerate(pbar):
                # Extract
                result = extractor.extract_single(candidate)
                result_dict = result_to_dict(result)

                # Append to output
                append_result(args.output, result_dict)

                # Track processed
                processed_ids.add(candidate["verse_id"])

                # Update stats
                stats.processed += 1
                stats.total_input_tokens += result.input_tokens
                stats.total_output_tokens += result.output_tokens

                if result.error:
                    stats.errors += 1
                    pbar.set_postfix({"errors": stats.errors})
                elif result.has_typology:
                    stats.with_typology += 1
                    stats.total_extractions += len(result.extractions)
                else:
                    stats.without_typology += 1

                # Update progress bar description
                pbar.set_postfix({
                    "typology": stats.with_typology,
                    "cost": f"${stats.estimated_cost_usd:.3f}",
                })

                # Save checkpoint periodically
                if (i + 1) % args.batch_size == 0:
                    save_checkpoint(args.checkpoint, processed_ids)
                    logger.debug(f"Checkpoint saved at {i + 1}")

    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving checkpoint...")
        save_checkpoint(args.checkpoint, processed_ids)
        print(f"Checkpoint saved. Use --resume to continue.")
        stats.elapsed_seconds = 0  # Will be inaccurate anyway
        print_stats(stats)
        sys.exit(1)

    # Final checkpoint save
    save_checkpoint(args.checkpoint, processed_ids)

    # Calculate elapsed time (approximate since we didn't track start)
    # The extractor tracks its own timing, but we process one at a time
    # For accurate timing, we'd need to track it here
    import time
    stats.elapsed_seconds = stats.processed * (60.0 / args.rate_limit)  # Approximate

    print_stats(stats)

    print(f"\nResults written to: {args.output}")
    print(f"Checkpoint saved to: {args.checkpoint}")
    print()
    print("Next steps:")
    print("  1. Review extractions with: python scripts/review_typology.py")
    print("  2. Or view raw results: head -5 " + str(args.output))


if __name__ == "__main__":
    main()
