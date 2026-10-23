#!/usr/bin/env python3
"""Check an extractor's output for the Catechism typology pass.

Validates every row of data/extracted/ccc_pass/raw/batch-NN.jsonl against the
pass rules: verbatim quotes, valid Type decisions (with alternatives
considered), known categories, resolvable verse refs, and one coverage row
that accounts for every paragraph in the batch. Works from the files written
by prepare_ccc_batches.py, so it needs no database.

Exit code 1 if any row has errors (warnings don't fail).

Usage:
    python scripts/check_ccc_raw.py 04
    python scripts/check_ccc_raw.py 04 --quiet
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.data.ccc_typology_pass import BATCHES, PASS_DIR, check_record


def main():
    parser = argparse.ArgumentParser(description="Check one batch of Catechism pass output")
    parser.add_argument("batch", choices=sorted(BATCHES), help="Batch number, e.g. 04")
    parser.add_argument("--quiet", action="store_true", help="Print errors and the summary only")
    args = parser.parse_args()

    raw = PASS_DIR / "raw" / f"batch-{args.batch}.jsonl"
    if not raw.exists():
        sys.exit(f"No output yet: {raw}")
    paragraphs = {int(n): p for n, p in json.loads((PASS_DIR / "paragraphs.json").read_text()).items()}
    types = {t["id"]: t for t in json.loads((PASS_DIR / "types_catalog.json").read_text())}
    verse_ids = set(json.loads((PASS_DIR / "verse_ids.json").read_text()))
    first, last = BATCHES[args.batch]

    errors, warnings, rows = [], [], []
    for i, line in enumerate(raw.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {i}: invalid JSON ({e})")
            continue
        rows.append(rec)
        errs, warns = check_record(rec, paragraphs, types, verse_ids)
        if rec.get("kind") != "coverage" and isinstance(rec.get("ccc"), int) and not first <= rec["ccc"] <= last:
            errs.append(f"CCC {rec['ccc']} is outside batch {args.batch} (§{first}–§{last})")
        errors += [f"line {i}: {e}" for e in errs]
        warnings += [f"line {i}: {w}" for w in warns]

    coverage = [r for r in rows if r.get("kind") == "coverage"]
    expected = sum(1 for n in paragraphs if first <= n <= last)
    if len(coverage) != 1:
        errors.append(f"expected exactly 1 coverage row, found {len(coverage)}")
    elif (coverage[0].get("first"), coverage[0].get("last"), coverage[0].get("read")) != (first, last, expected):
        errors.append(f"coverage row must be first={first}, last={last}, read={expected}: {coverage[0]}")

    findings = [r for r in rows if r.get("kind") not in ("coverage", "catalog-issue")]
    issues = [r for r in rows if r.get("kind") == "catalog-issue"]
    print(f"batch {args.batch}: {len(findings)} rows from "
          f"{len({r.get('ccc') for r in findings})} paragraphs")
    if not args.quiet:
        print("  kinds:     ", dict(Counter(r.get("kind") for r in findings)))
        print("  relations: ", dict(Counter(r.get("relation") for r in findings)))
        decisions = Counter(r[side].get("decision") for r in findings for side in ("type", "antitype")
                            if isinstance(r.get(side), dict))
        print("  Type decisions:", dict(decisions))
        print("  catalog issues:", len(issues))
    for w in warnings:
        print(f"  warning: {w}")
    for e in errors:
        print(f"  ERROR: {e}")
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
