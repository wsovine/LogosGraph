#!/usr/bin/env python3
"""Reconcile extractor output for the Catechism typology pass.

Deterministic, no LLM. Reads every data/extracted/ccc_pass/raw/batch-NN.jsonl,
re-runs the row checks, and sorts each row into a review bucket:

    A  adds a Catechism source to a link the graph already has
    B  new link between existing Types
    C  depends on a Type decision (broaden / merge / new) on either side
    T  teaches-only (CatechismParagraph -> Type)
    X  held: prophecy, NT -> NT, or failed checks (kept for audit)

Verse evidence (bucket M) is listed separately. It also writes the Type ledger that
the consolidation agent works from, and a gold-set recall check.

Outputs (data/extracted/ccc_pass/):
    candidates.jsonl     one row per candidate, with cand_id and bucket
    catalog_issues.json  existing graph data the extractors found the Catechism contradicts
    type_ledger.json     broaden/merge proposals per existing Type + grouped new Types
    reconcile-report.md  counts, warnings, recall

Usage:
    python scripts/reconcile_ccc_typology.py            # all batches present
    python scripts/reconcile_ccc_typology.py --batches 04
    python scripts/reconcile_ccc_typology.py --check-decisions   # after Type consolidation
    python scripts/reconcile_ccc_typology.py --apply-decisions   # → candidates_final.jsonl
"""

import argparse
import difflib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.data.ccc_typology_pass import BATCHES, PASS_DIR, check_record, load_jsonl, resolve_verses

HELD_RELATIONS = {"prophecy", "nt-figure"}


def name_key(name: str) -> str:
    """Grouping key for proposed Type names: lowercase, no articles or punctuation."""
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower().replace("'s", "")).split()
    return " ".join(w for w in words if w not in {"the", "a", "an", "of"})


def side_key(d: dict) -> str:
    """Stable identity for one side of a pair, before consolidation."""
    if not isinstance(d, dict):
        return "?"
    decision = d.get("decision")
    if decision == "new":
        return f"new:{name_key(d.get('name', ''))}"
    if decision == "merge":
        return (d.get("merge_ids") or ["?"])[0]
    return d.get("id") or "?"


COMMON_WORDS = {"holy", "israel", "lord", "gods", "mount", "people", "new", "old", "covenant"}


def _significant(key: str) -> set[str]:
    return {w for w in key.split() if len(w) > 3 and w not in COMMON_WORDS}


def _near(key: str, candidates: dict[str, str], limit: int = 4) -> list[str]:
    """Candidates whose name key shares a significant word with `key` or reads similarly, best first."""
    words = _significant(key)
    scored = []
    for cid, ckey in candidates.items():
        ratio = difflib.SequenceMatcher(None, key, ckey).ratio()
        if ratio >= 0.6 or words & _significant(ckey):
            scored.append((ratio, cid))
    return [cid for _, cid in sorted(scored, reverse=True)[:limit]]


def load_inputs(batches: list[str]):
    paragraphs = {int(n): p for n, p in json.loads((PASS_DIR / "paragraphs.json").read_text()).items()}
    catalog = json.loads((PASS_DIR / "types_catalog.json").read_text())
    types = {t["id"]: t for t in catalog}
    verse_ids = set(json.loads((PASS_DIR / "verse_ids.json").read_text()))
    gold = {int(n): v for n, v in json.loads((PASS_DIR / "gold.json").read_text()).items()}
    rows = []
    for b in batches:
        for rec in load_jsonl(PASS_DIR / "raw" / f"batch-{b}.jsonl"):
            rows.append((b, rec))
    return paragraphs, types, verse_ids, gold, rows


def bucket_for(rec: dict, errors: list[str], types: dict[str, dict]) -> tuple[str, str | None]:
    """(bucket, existing_category)."""
    if errors:
        return "X", None
    if rec["relation"] in HELD_RELATIONS:
        return "X", None
    sides = [rec["type"]] + ([rec["antitype"]] if rec["kind"] == "prefigures" else [])
    if any(s["decision"] != "existing" for s in sides):
        return "C", None
    if rec["kind"] == "teaches":
        return "T", None
    existing = {l["id"]: l["category"] for l in types[rec["type"]["id"]]["out"]}
    if rec["antitype"]["id"] in existing:
        return "A", existing[rec["antitype"]["id"]]
    return "B", None


def build_ledger(candidates: list[dict], types: dict[str, dict]) -> dict:
    changes = defaultdict(list)  # existing Type id -> broaden/merge proposals
    new_groups = defaultdict(lambda: {"names": Counter(), "testaments": Counter(), "descriptions": [],
                                      "key_verses": [], "depends": []})
    for c in candidates:
        if c["bucket"] != "C":
            continue
        for side in ("type", "antitype"):
            d = c.get(side)
            if not isinstance(d, dict) or d["decision"] == "existing":
                continue
            entry = {"cand_id": c["cand_id"], "ccc": c["ccc"], "side": side, "relation": c["relation"],
                     "reasoning": d.get("reasoning"), "alternatives_considered": d.get("alternatives_considered")}
            if d["decision"] == "broaden":
                changes[d["id"]].append({**entry, "decision": "broaden", "new_name": d["new_name"],
                                         "new_description": d["new_description"]})
            elif d["decision"] == "merge":
                for tid in d["merge_ids"]:
                    changes[tid].append({**entry, "decision": "merge", "merge_ids": d["merge_ids"]})
            else:
                g = new_groups[name_key(d["name"])]
                g["names"][d["name"]] += 1
                g["testaments"][d["testament"]] += 1
                g["descriptions"].append(d["description"])
                if d.get("key_verse"):
                    g["key_verses"].append(d["key_verse"])
                g["depends"].append(entry)

    catalog_keys = {tid: name_key(t["name"]) for tid, t in types.items()}
    group_keys = list(new_groups)
    ledger_new = []
    for key, g in sorted(new_groups.items()):
        name = g["names"].most_common(1)[0][0]
        near_catalog = _near(key, catalog_keys)
        near_new = _near(key, {k: k for k in group_keys if k != key})
        ledger_new.append({
            "group": key, "name": name, "name_variants": dict(g["names"]),
            "testament": g["testaments"].most_common(1)[0][0], "testament_votes": dict(g["testaments"]),
            "descriptions": g["descriptions"], "key_verses": sorted(set(g["key_verses"])),
            "near_catalog": near_catalog, "near_new_groups": near_new, "depends": g["depends"],
        })
    ledger_existing = [
        {"id": tid, "name": types[tid]["name"], "testament": types[tid]["testament"],
         "description": types[tid]["description"], "out": types[tid]["out"], "inc": types[tid]["inc"],
         "proposals": props}
        for tid, props in sorted(changes.items())
    ]
    return {"existing_type_changes": ledger_existing, "new_types": ledger_new}


# ---------------------------------------------------------------------------
# Type decisions (from the consolidation agent)
# ---------------------------------------------------------------------------

ACTIONS = {"use_existing", "new", "broaden", "rename", "merge", "reject"}
_KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def check_decisions(ledger: dict, decisions: list[dict], types: dict[str, dict]) -> list[str]:
    """Every ledger entry covered exactly once; ids and fields valid."""
    errors = []
    new_ids = {d.get("new_id") for d in decisions if d.get("action") == "new"}
    known = set(types) | new_ids
    covered_groups, covered_ids = Counter(), Counter()
    for d in decisions:
        did, action = d.get("decision_id", "?"), d.get("action")
        if action not in ACTIONS:
            errors.append(f"{did}: action must be one of {sorted(ACTIONS)}")
            continue
        covers = d.get("covers") or {}
        covered_groups.update(covers.get("new_groups") or [])
        covered_ids.update(covers.get("existing_ids") or [])
        if action == "new":
            nid = d.get("new_id") or ""
            if not _KEBAB.match(nid) or nid in types:
                errors.append(f"{did}: new_id {nid!r} must be kebab-case and not an existing id")
            if not (d.get("name") and d.get("description")) or d.get("testament") not in ("OT", "NT"):
                errors.append(f"{did}: new needs name, description and testament")
        if action in ("use_existing", "broaden", "rename", "merge") and d.get("target_id") not in known:
            errors.append(f"{did}: unknown target_id {d.get('target_id')!r}")
        if action in ("broaden", "rename", "merge") and not d.get("name"):
            errors.append(f"{did}: {action} needs the resulting name")
        if action == "merge":
            absorbed = d.get("absorbs") or []
            if not absorbed or any(a not in types for a in absorbed):
                errors.append(f"{did}: merge needs existing ids in absorbs")
        if action in ("broaden", "rename", "merge") and not d.get("affected_links") and \
                (types.get(d.get("target_id"), {}).get("out") or types.get(d.get("target_id"), {}).get("inc")):
            errors.append(f"{did}: list the target's current links in affected_links (the link test)")
        if action == "reject" and d.get("target_id") and d["target_id"] not in known:
            errors.append(f"{did}: reject remaps to unknown target_id {d['target_id']!r}")
    groups = {g["group"] for g in ledger["new_types"]}
    ids = {e["id"] for e in ledger["existing_type_changes"]}
    errors += [f"new-Type group not covered: {g}" for g in sorted(groups - set(covered_groups))]
    errors += [f"existing Type not covered: {i}" for i in sorted(ids - set(covered_ids))]
    errors += [f"covered more than once: {k}" for k, n in (covered_groups + covered_ids).items() if n > 1]
    errors += [f"covers an unknown ledger entry: {k}" for k in sorted(set(covered_groups) - groups)]
    errors += [f"covers an unknown ledger entry: {k}" for k in sorted(set(covered_ids) - ids)]
    return errors


def apply_decisions(candidates: list[dict], decisions: list[dict], types: dict[str, dict]) -> list[dict]:
    """Rewrite each candidate to final Type ids and re-bucket. Rows that depend on a
    Type decision list it in `pending_decisions` (the user approves those first)."""
    by_group = {g: d for d in decisions for g in (d.get("covers") or {}).get("new_groups") or []}
    by_existing = {i: d for d in decisions for i in (d.get("covers") or {}).get("existing_ids") or []}
    absorbed = {a: d for d in decisions if d.get("action") == "merge" for a in d.get("absorbs") or []}

    def resolve(side: dict) -> tuple[str | None, list[str]]:
        if not isinstance(side, dict):
            return None, []
        if side["decision"] == "new":
            d = by_group.get(name_key(side["name"]))
            if d is None or (d["action"] == "reject" and not d.get("target_id")):
                return None, []
            tid = d.get("new_id") if d["action"] == "new" else d.get("target_id")
            return tid, ([d["decision_id"]] if d["action"] != "use_existing" and d["action"] != "reject" else [])
        tid = (side.get("merge_ids") or [None])[0] if side["decision"] == "merge" else side.get("id")
        pending = []
        d = by_existing.get(tid)
        if d and d["action"] in ("broaden", "rename", "merge"):
            pending.append(d["decision_id"])
            tid = d.get("target_id") or tid
        if tid in absorbed:
            pending.append(absorbed[tid]["decision_id"])
            tid = absorbed[tid]["target_id"]
        return tid, pending

    final, first_seen = [], {}
    for c in candidates:
        type_id, p1 = resolve(c.get("type"))
        anti_id, p2 = resolve(c.get("antitype")) if c.get("kind") == "prefigures" else (None, [])
        pending = sorted(set(p1 + p2))
        row = {**c, "type_id": type_id, "antitype_id": anti_id, "pending_decisions": pending}
        pair = (c["ccc"], c.get("kind"), type_id, anti_id)
        if c["bucket"] != "X" and type_id and pair in first_seen:
            row["bucket"] = "X"
            row["check_errors"] = c["check_errors"] + [f"duplicate of {first_seen[pair]} after Type consolidation"]
        elif c["bucket"] == "X":
            pass
        elif type_id is None or (c.get("kind") == "prefigures" and anti_id is None):
            row["bucket"] = "X"
            row["check_errors"] = c["check_errors"] + ["a Type it depends on was rejected in consolidation"]
        elif pending:
            row["bucket"] = "C"
        elif c.get("kind") == "teaches":
            row["bucket"] = "T"
        else:
            out = {l["id"]: l["category"] for l in types.get(type_id, {}).get("out", [])}
            row["bucket"] = "A" if anti_id in out else "B"
            row["existing_category"] = out.get(anti_id)
        if row["bucket"] != "X":
            first_seen.setdefault(pair, c["cand_id"])
        final.append(row)
    return final


def main():
    parser = argparse.ArgumentParser(description="Reconcile Catechism typology pass output")
    parser.add_argument("--batches", nargs="+", choices=sorted(BATCHES),
                        help="Batches to include (default: every batch with output)")
    parser.add_argument("--check-decisions", action="store_true",
                        help="Validate type_decisions.jsonl against type_ledger.json and exit")
    parser.add_argument("--apply-decisions", action="store_true",
                        help="Rewrite candidates.jsonl to final Type ids → candidates_final.jsonl")
    args = parser.parse_args()

    if args.check_decisions or args.apply_decisions:
        types = {t["id"]: t for t in json.loads((PASS_DIR / "types_catalog.json").read_text())}
        ledger = json.loads((PASS_DIR / "type_ledger.json").read_text())
        decisions = load_jsonl(PASS_DIR / "type_decisions.jsonl")
        errors = check_decisions(ledger, decisions, types)
        for e in errors:
            print(f"ERROR: {e}")
        print(f"{len(decisions)} decisions · {dict(Counter(d.get('action') for d in decisions))} · {len(errors)} errors")
        if errors or args.check_decisions:
            sys.exit(1 if errors else 0)
        final = apply_decisions(load_jsonl(PASS_DIR / "candidates.jsonl"), decisions, types)
        with (PASS_DIR / "candidates_final.jsonl").open("w", encoding="utf-8") as f:
            for row in final:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"candidates_final.jsonl: {len(final)} rows · buckets {dict(Counter(r['bucket'] for r in final))}")
        return

    batches = args.batches or sorted(b for b in BATCHES if (PASS_DIR / "raw" / f"batch-{b}.jsonl").exists())
    if not batches:
        sys.exit("No extractor output found")

    paragraphs, types, verse_ids, gold, rows = load_inputs(batches)
    candidates, coverage, issues, seen = [], [], [], set()
    warnings_all = []
    for batch, rec in rows:
        if rec.get("kind") == "coverage":
            coverage.append(rec)
            continue
        if rec.get("kind") == "catalog-issue":
            issues.append({**rec, "batch": batch})
            continue
        errors, warnings = check_record(rec, paragraphs, types, verse_ids)
        type_key, anti_key = side_key(rec.get("type")), side_key(rec.get("antitype"))
        cand_id = f"c{rec.get('ccc')}:{type_key}>{anti_key}" if rec.get("kind") == "prefigures" \
            else f"c{rec.get('ccc')}:teaches:{type_key}"
        if cand_id in seen:
            warnings_all.append(f"{cand_id}: duplicate row dropped")
            continue
        seen.add(cand_id)
        bucket, existing_category = bucket_for(rec, errors, types)
        if existing_category and rec.get("category") != existing_category:
            warnings.append(f"category {rec.get('category')} differs from the existing link's "
                            f"{existing_category}; the existing category is kept")
        verses = {}
        for side in ("type_verses", "antitype_verses", "verses"):
            ids, _ = resolve_verses(rec.get(side) or [])
            if ids:
                verses[side] = [v for v in ids if v in verse_ids]
        candidates.append({**rec, "cand_id": cand_id, "batch": batch, "bucket": bucket,
                           "existing_category": existing_category, "check_errors": errors,
                           "warnings": warnings, "verse_ids": verses})
        warnings_all += [f"{cand_id}: {w}" for w in warnings]

    candidates.sort(key=lambda c: (c["ccc"], c["cand_id"]))
    with (PASS_DIR / "candidates.jsonl").open("w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    (PASS_DIR / "catalog_issues.json").write_text(json.dumps(issues, indent=1, ensure_ascii=False))
    ledger = build_ledger(candidates, types)
    (PASS_DIR / "type_ledger.json").write_text(json.dumps(ledger, indent=1, ensure_ascii=False))

    # Verse evidence (bucket M): verses on reviewable rows
    m_rows = sum(len(v) for c in candidates if c["bucket"] != "X" for v in c["verse_ids"].values())

    # Gold recall, over gold paragraphs inside the batches read
    in_scope = {n: v for n, v in gold.items() if any(BATCHES[b][0] <= n <= BATCHES[b][1] for b in batches)}
    found = defaultdict(list)
    for c in candidates:
        cited = {c["ccc"]} | {q.get("ccc") for q in c.get("quotes") or []}
        for n in cited & set(in_scope):
            found[n].append(f"{c['cand_id']} [{c['bucket']}/{c['relation']}]")
    missed = sorted(set(in_scope) - set(found))

    buckets = Counter(c["bucket"] for c in candidates)
    lines = [
        "# Catechism pass: reconcile report", "",
        f"Batches: {', '.join(batches)} · rows: {len(candidates)} · paragraphs with rows: "
        f"{len({c['ccc'] for c in candidates})}", "",
        "## Buckets", "",
        *[f"- **{b}**: {buckets.get(b, 0)}" for b in "ABCTX"],
        f"- **M** (verse evidence on reviewable rows): {m_rows} verse links", "",
        "## Relations", "",
        *[f"- {r}: {n}" for r, n in Counter(c["relation"] for c in candidates).most_common()], "",
        "## Type ledger", "",
        f"- Existing Types with broaden/merge proposals: {len(ledger['existing_type_changes'])}",
        *[f"  - `{e['id']}` ({e['name']}): " + "; ".join(
            f"{p['decision']} → {p.get('new_name') or p.get('merge_ids')} (§{p['ccc']})" for p in e["proposals"])
          for e in ledger["existing_type_changes"]],
        f"- Proposed new Types: {len(ledger['new_types'])}",
        *[f"  - {g['name']} ({g['testament']}) ← {len(g['depends'])} row(s)"
          + (f"; near catalog: {', '.join(g['near_catalog'])}" if g["near_catalog"] else "")
          + (f"; near new: {', '.join(g['near_new_groups'])}" if g["near_new_groups"] else "")
          for g in ledger["new_types"]], "",
        f"## Gold recall: {len(in_scope) - len(missed)}/{len(in_scope)}", "",
        *[f"- §{n} {in_scope[n]}: " + ("; ".join(found[n]) if n in found else "**MISSED**") for n in sorted(in_scope)],
        "",
        "## Coverage", "",
        *[f"- batch {c.get('batch')}: §{c.get('first')}–§{c.get('last')}, read {c.get('read')}, "
          f"with findings {c.get('with_findings')}" for c in coverage], "",
        "## Catalog issues (existing graph data the Catechism contradicts)", "",
        *[f"- §{i['ccc']} {i.get('ids')}: {i['issue']}" for i in issues], "",
        "## Failed checks (bucket X)", "",
        *[f"- {c['cand_id']}: {'; '.join(c['check_errors'])}" for c in candidates if c["check_errors"]], "",
        "## Warnings", "",
        *[f"- {w}" for w in warnings_all],
    ]
    (PASS_DIR / "reconcile-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(candidates)} candidates · buckets {dict(buckets)} · M {m_rows} · "
          f"gold {len(in_scope) - len(missed)}/{len(in_scope)} · "
          f"Type changes {len(ledger['existing_type_changes'])} existing, {len(ledger['new_types'])} new")
    print(f"Report: {PASS_DIR / 'reconcile-report.md'}")


if __name__ == "__main__":
    main()
