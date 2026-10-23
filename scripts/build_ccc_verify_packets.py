#!/usr/bin/env python3
"""Build blind verification packets for the Catechism typology pass, and check verdicts.

Each packet gives a verifier (the theologian persona) the claims to judge, in plain words,
plus the Catechism text. It deliberately omits the extractor's rationale and
confidence, so the verdict is independent. Each packet also carries a recall sample:
paragraphs with typology vocabulary that produced no candidate.

Reads candidates_final.jsonl (after Type consolidation) and type_decisions.jsonl.
Held rows (prophecy, NT -> NT) are not verified in this phase.

Outputs (data/extracted/ccc_pass/verify/):
    packet-NN.md        claims + Type decisions + texts + recall sample
    verdicts-NN.jsonl   written by the verifier agent

Usage:
    python scripts/build_ccc_verify_packets.py --packets 6
    python scripts/build_ccc_verify_packets.py --check          # every claim has one valid verdict
"""

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.data.ccc_typology_pass import PASS_DIR, load_jsonl
from reconcile_ccc_typology import name_key

VERIFY_DIR = PASS_DIR / "verify"
WRAP = 110
NO_SPLIT = {"break_on_hyphens": False, "break_long_words": False}
RECALL_PER_PACKET = 8
TYPOLOGY_WORDS = re.compile(
    r"prefigur|foreshadow|\bfigures?\b|\btypes?\b|typolog|image of|prepar(?:ed|es|ing) the way|"
    r"fulfil|announc", re.I)
VERBS = {
    "explicit": "prefigures",
    "preparatory": "prepares the way for (or is fulfilled in)",
    "synthesized": "prefigures (taking these paragraphs together)",
}
VERDICTS = {"accept", "reject", "revise"}


def wrap(text: str, indent: str = "") -> list[str]:
    out = []
    for para in text.strip().split("\n"):
        out += textwrap.wrap(para, WRAP, initial_indent=indent, subsequent_indent=indent, **NO_SPLIT) or [""]
    return out


def link_text(a) -> str:
    """An affected link, given as a string or as {link, basis, reads_true, why}."""
    if isinstance(a, str):
        return a
    return f"{a.get('link')} (basis: {a.get('basis')}; consolidator: {a.get('why')})"


def type_label(tid: str, types: dict, decisions: dict) -> str:
    """Display name for a final Type id: an approved-pending new or renamed Type shows its proposed name."""
    for d in decisions.values():
        if d.get("action") == "new" and d.get("new_id") == tid:
            return f"{d['name']} [proposed new {d['testament']} Type: {d['description']}]"
        if d.get("action") in ("broaden", "rename", "merge") and d.get("target_id") == tid:
            return f"{d['name']} [existing `{tid}`, proposed {d['action']}; was “{types[tid]['name']}”]"
    t = types.get(tid, {})
    return f"{t.get('name', tid)} ({t.get('testament', '?')})"


def claim_text(row: dict, types: dict, decisions: dict) -> str:
    if row["kind"] == "teaches":
        return f"The Catechism teaches about **{type_label(row['type_id'], types, decisions)}**."
    verb = VERBS.get(row["relation"], row["relation"])
    return (f"In the Catechism, **{type_label(row['type_id'], types, decisions)}** {verb} "
            f"**{type_label(row['antitype_id'], types, decisions)}**. Category: {row.get('category')}.")


def build(n_packets: int) -> None:
    rows = [r for r in load_jsonl(PASS_DIR / "candidates_final.jsonl") if r["bucket"] != "X"]
    decisions = {d["decision_id"]: d for d in load_jsonl(PASS_DIR / "type_decisions.jsonl")}
    types = {t["id"]: t for t in json.loads((PASS_DIR / "types_catalog.json").read_text())}
    paragraphs = {int(n): p for n, p in json.loads((PASS_DIR / "paragraphs.json").read_text()).items()}
    all_rows = load_jsonl(PASS_DIR / "candidates.jsonl")
    with_rows = {r["ccc"] for r in all_rows} | {q["ccc"] for r in all_rows for q in r.get("quotes") or []}
    recall_pool = [n for n in sorted(paragraphs)
                   if n not in with_rows and TYPOLOGY_WORDS.search(paragraphs[n]["text"])]

    rows.sort(key=lambda r: r["ccc"])
    size = -(-len(rows) // n_packets)
    chunks = [rows[i:i + size] for i in range(0, len(rows), size)]
    decision_ids = [d for d, v in decisions.items() if v["action"] not in ("use_existing",)]
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)

    # Each Type decision goes to the packet holding the first row that depends on it. A decision whose
    # rows are all held or folded (e.g. a broaden whose rows became duplicates) goes to the packet
    # covering its first dependent paragraph, or else to the last packet.
    final_rows = load_jsonl(PASS_DIR / "candidates_final.jsonl")
    assigned = {}
    for d in decision_ids:
        live = next((k for k, c in enumerate(chunks, 1) if any(d in r["pending_decisions"] for r in c)), None)
        if live is None:
            deps = [r["ccc"] for r in final_rows if d in r.get("pending_decisions", [])] or \
                   [r["ccc"] for r in final_rows for side in ("type", "antitype")
                    if isinstance(r.get(side), dict) and r[side].get("decision") == "new"
                    and name_key(r[side].get("name", "")) in (decisions[d].get("covers") or {}).get("new_groups", [])]
            live = next((k for k, c in enumerate(chunks, 1) if deps and c[0]["ccc"] <= min(deps) <= c[-1]["ccc"]),
                        len(chunks))
        assigned[d] = live

    for k, chunk in enumerate(chunks, 1):
        first, last = chunk[0]["ccc"], chunk[-1]["ccc"]
        recall = [n for n in recall_pool if first <= n <= last][:RECALL_PER_PACKET]
        mine = [d for d in decision_ids if assigned[d] == k]
        texts = sorted({r["ccc"] for r in chunk} | {q["ccc"] for r in chunk for q in r.get("quotes") or []}
                       | {r["ccc"] + o for r in chunk for o in (-1, 1) if r["ccc"] + o in paragraphs}
                       | set(recall))
        lines = [f"# Verification packet {k:02d}: §{first}–§{last}", "",
                 f"Claims: {len(chunk)} · Type decisions: {len(mine)} · Recall sample: {len(recall)} paragraphs",
                 f"Write verdicts to `data/extracted/ccc_pass/verify/verdicts-{k:02d}.jsonl`.", "",
                 "## Claims", ""]
        for r in chunk:
            quotes = [(r["ccc"], r["quote"])] if r.get("quote") else [(q["ccc"], q["quote"]) for q in r["quotes"]]
            lines += [f"### {r['cand_id']}", f"- §{r['ccc']} · relation: {r['relation']}",
                      *wrap(f"- Claim: {claim_text(r, types, decisions)}")]
            lines += [ln for n, q in quotes for ln in wrap(f"- Quote (§{n}): “{q}”")]
            if r["pending_decisions"]:
                lines.append(f"- Depends on Type decision(s): {', '.join(r['pending_decisions'])}")
            lines.append("")
        if mine:
            lines += ["## Type decisions", ""]
            for d in mine:
                v = decisions[d]
                lines += [f"### {d} ({v['action']})",
                          *wrap(f"- Result: {v.get('name') or v.get('target_id')}"
                                + (f" — {v['description']}" if v.get("description") else "")),
                          *(wrap(f"- Target: `{v['target_id']}` (now “{types[v['target_id']]['name']}”)")
                            if v.get("target_id") in types else []),
                          *(wrap(f"- Absorbs: {', '.join(v['absorbs'])}") if v.get("absorbs") else []),
                          *([ln for a in v.get("affected_links") or [] for ln in wrap(f"- Must still read true: {link_text(a)}")]),
                          *wrap(f"- Consolidator's rationale: {v.get('rationale', '')}"), ""]
        if recall:
            lines += ["## Recall sample (no candidate was extracted from these)", "",
                      ", ".join(f"§{n}" for n in recall), ""]
        lines += ["## Catechism texts", ""]
        for n in texts:
            lines += [f"#### §{n}", *wrap(paragraphs[n]["text"]), ""]
        (VERIFY_DIR / f"packet-{k:02d}.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"packet-{k:02d}: §{first}–§{last}  {len(chunk)} claims  {len(mine)} decisions  "
              f"{len(recall)} recall  {len(lines)} lines")


def check() -> int:
    rows = {r["cand_id"] for r in load_jsonl(PASS_DIR / "candidates_final.jsonl") if r["bucket"] != "X"}
    decisions = {d["decision_id"] for d in load_jsonl(PASS_DIR / "type_decisions.jsonl")
                 if d["action"] != "use_existing"}
    seen, errors = {}, []
    for path in sorted(VERIFY_DIR.glob("verdicts-*.jsonl")):
        for v in load_jsonl(path):
            key = v.get("cand_id") or v.get("decision_id") or v.get("recall_ccc")
            if v.get("recall_ccc"):
                continue
            if key in seen:
                errors.append(f"{path.name}: duplicate verdict for {key}")
            seen[key] = v
            if v.get("verdict") not in VERDICTS or not v.get("reason"):
                errors.append(f"{path.name}: {key} needs verdict in {sorted(VERDICTS)} and a reason")
    errors += [f"no verdict: {k}" for k in sorted((rows | decisions) - set(seen))]
    errors += [f"verdict for unknown id: {k}" for k in sorted(set(seen) - rows - decisions)]
    for e in errors:
        print(f"ERROR: {e}")
    print(f"{len(seen)} verdicts for {len(rows)} claims + {len(decisions)} Type decisions · {len(errors)} errors")
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description="Build or check Catechism pass verification packets")
    parser.add_argument("--packets", type=int, default=6, help="Number of packets (default 6)")
    parser.add_argument("--check", action="store_true", help="Check verdict files and exit")
    args = parser.parse_args()
    if args.check:
        sys.exit(check())
    build(args.packets)


if __name__ == "__main__":
    main()
