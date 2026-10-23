#!/usr/bin/env python3
"""Interactive human review of the Catechism typology pass.

Walks the reviewer through, in order:
  1. Type decisions (new / broaden / rename / merge), with every existing link they affect
  2. New links (buckets C and B)
  3. Catechism sources added to existing links (bucket A)
  4. Teaches-only rows (bucket T)
  In buckets A and T, [A] approves the rest of the bucket where the verifier accepted or
  changed only the relation label.
Each card shows the claim, the verbatim quote, the extractor's rationale and the
independent verifier's verdict. A row's verse evidence is approved with the row.
Rows that need a rejected Type decision stay in the queue: remap them with [e] or reject them.
Nothing touches the database here.

Outputs (data/reviewed/):
  ccc_typology_approved.jsonl / ccc_typology_rejected.jsonl
  type_changes.jsonl / type_changes_rejected.jsonl   (approved Type decisions overlay)

Keys:  y approve  n reject  e edit  r apply the verifier's revision  v full paragraph
       s skip  q quit  A approve the rest of bucket A or T (verifier-accepted or label-only)

Usage:
    python scripts/review_ccc_typology.py
    python scripts/review_ccc_typology.py --bucket A
    python scripts/review_ccc_typology.py --stats
    python scripts/review_ccc_typology.py --auto-verifier   # apply the verifier's verdicts (user-authorized)
"""

import argparse
import json
import os
import shutil
import sys
import textwrap
from collections import Counter
from datetime import date
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.data.book_mapping import display_ref
from src.data.ccc_typology_pass import PASS_DIR, load_jsonl
from src.data.typology_schemas import VALID_CATEGORIES
from src.review.typology_reviewer import colorize

REVIEWED = Path("data/reviewed")
APPROVED = REVIEWED / "ccc_typology_approved.jsonl"
REJECTED = REVIEWED / "ccc_typology_rejected.jsonl"
TYPES_APPROVED = REVIEWED / "type_changes.jsonl"
TYPES_REJECTED = REVIEWED / "type_changes_rejected.jsonl"
BUCKET_ORDER = {"C": 0, "B": 0, "A": 1, "T": 2}
BULK_BUCKETS = {"A", "T"}  # adding a source / a TEACHES edge: low risk, bulk-approvable
STAGES = {
    "C": "NEW LINKS",
    "B": "NEW LINKS",
    "A": "CATECHISM SOURCES ON EXISTING LINKS",
    "T": "CATECHISM TEACHES (NO NEW PAIR)",
}
VERDICT_COLORS = {"accept": "green", "revise": "yellow", "reject": "red"}
WIDTH = min(shutil.get_terminal_size((100, 24)).columns, 110)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def wrap(text: str, indent: int = 2, color: str | None = None) -> None:
    """Print text wrapped to the terminal, indented, optionally colored."""
    pad = " " * indent
    for para in str(text).split("\n"):
        lines = textwrap.wrap(para, WIDTH - indent, break_on_hyphens=False) or [""]
        for line in lines:
            print(pad + (colorize(line, color) if color else line))


def rule(char: str = "─", color: str = "dim") -> None:
    print(colorize(char * WIDTH, color))


def section(title: str) -> None:
    print()
    print(colorize(title, "bold"))


def clear() -> None:
    if sys.stdout.isatty():
        os.system("clear" if os.name == "posix" else "cls")


def menu(options: list[tuple[str, str, str]]) -> None:
    """options: (key, label, color)."""
    print()
    rule()
    print("  " + "   ".join(f"[{colorize(k, c)}] {label}" for k, label, c in options))


def ask(keys: str) -> str:
    while True:
        choice = input(colorize("\n  Your choice: ", "bold")).strip()
        if choice in keys or (choice.lower() in keys and choice.lower() != "a"):
            return choice if choice in keys else choice.lower()


def load_or_empty(path: Path) -> list[dict]:
    return load_jsonl(path) if path.exists() else []


def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


class Review:
    def __init__(self):
        self.rows = load_jsonl(PASS_DIR / "candidates_final.jsonl")
        self.decisions = {d["decision_id"]: d for d in load_or_empty(PASS_DIR / "type_decisions.jsonl")}
        self.types = {t["id"]: t for t in json.loads((PASS_DIR / "types_catalog.json").read_text())}
        self.paragraphs = {int(n): p for n, p in json.loads((PASS_DIR / "paragraphs.json").read_text()).items()}
        self.verdicts = {}
        for path in sorted((PASS_DIR / "verify").glob("verdicts-*.jsonl")):
            for v in load_jsonl(path):
                key = v.get("cand_id") or v.get("decision_id")
                if key:
                    self.verdicts[key] = v
        self.approved_types = {d["decision_id"]: d for d in load_or_empty(TYPES_APPROVED)}
        self.rejected_types = {d["decision_id"] for d in load_or_empty(TYPES_REJECTED)}
        self.done = {r["cand_id"] for r in load_or_empty(APPROVED)} | {r["cand_id"] for r in load_or_empty(REJECTED)}
        self.session = Counter()

    # -- naming ------------------------------------------------------------
    def new_type(self, tid: str | None) -> dict | None:
        return next((d for d in self.decisions.values() if d.get("action") == "new" and d.get("new_id") == tid), None)

    def name(self, tid: str | None) -> str:
        d = self.new_type(tid)
        if d:
            return f"{d['name']} ({d['testament']})"
        t = self.types.get(tid)
        return f"{t['name']} ({t['testament']})" if t else str(tid)

    def known_ids(self) -> set[str]:
        return set(self.types) | {d["new_id"] for d in self.approved_types.values() if d.get("action") == "new"}

    # -- shared card parts ---------------------------------------------------
    def header(self, stage: str, i: int, n: int) -> None:
        clear()
        rule("═")
        print(colorize("  CATECHISM TYPOLOGY REVIEW", "bold") + colorize(f"  ·  {stage}", "cyan"))
        rule("═")
        s = self.session
        print(f"  Item {i} of {n}    "
              f"{colorize(f'Approved: {s['approved']}', 'green')}  "
              f"{colorize(f'Rejected: {s['rejected']}', 'red')}  "
              f"{colorize(f'Edited: {s['edited']}', 'yellow')}  "
              f"{colorize(f'Skipped: {s['skipped']}', 'dim')}")

    def show_verdict(self, key: str) -> None:
        v = self.verdicts.get(key)
        section("VERIFIER")
        if not v:
            wrap("(no verdict)", color="dim")
            return
        print("  " + colorize(v["verdict"].upper(), VERDICT_COLORS.get(v["verdict"], "bold")))
        wrap(v.get("reason", ""), indent=4)
        changes = {k: v[k] for k in ("relation", "type_id", "antitype_id", "category") if v.get(k)}
        if changes:
            wrap("Suggests: " + ", ".join(f"{k} → {val}" for k, val in changes.items()), indent=4, color="yellow")
        if v.get("suggested"):
            wrap(f"Suggests: {v['suggested']}", indent=4, color="yellow")
        if v.get("pastoral_flag"):
            wrap(f"⚑ {v['pastoral_flag']}", indent=4, color="magenta")

    def show_paragraph(self, n: int) -> None:
        section(f"CATECHISM §{n} (full text)")
        wrap(self.paragraphs[n]["text"], indent=4)

    # -- Type decisions ----------------------------------------------------
    def review_types(self) -> bool:
        queue = [d for d in self.decisions.values()
                 if d["action"] not in ("use_existing", "reject") and not d.get("held_only")
                 and d["decision_id"] not in self.approved_types and d["decision_id"] not in self.rejected_types]
        for i, d in enumerate(queue, 1):
            deps = [r for r in self.rows if d["decision_id"] in r.get("pending_decisions", [])]
            self.header("TYPE DECISIONS", i, len(queue))
            print()
            action = d["action"].upper()
            print("  " + colorize(f"{action}", "magenta") + colorize(f"   {d['decision_id']}", "dim"))

            section("PROPOSED TYPE")
            testament = f" ({d['testament']})" if d.get("testament") else ""
            print("  " + colorize(f"{d.get('name')}{testament}", "yellow" if d.get("testament") != "NT" else "green"))
            if d.get("description"):
                wrap(d["description"], indent=4, color="dim")

            if d.get("target_id") in self.types:
                t = self.types[d["target_id"]]
                section("CURRENTLY")
                print(f"  {t['name']}" + colorize(f"   `{t['id']}`", "dim"))
                wrap(t["description"] or "(no description)", indent=4, color="dim")
            if d.get("absorbs"):
                section("ABSORBS")
                wrap(", ".join(d["absorbs"]), indent=4)

            if d.get("affected_links"):
                section("EXISTING LINKS THAT MUST STILL READ TRUE")
                for a in d["affected_links"]:
                    link = a if isinstance(a, str) else a.get("link")
                    print("  • " + colorize(link, "cyan"))
                    if not isinstance(a, str) and a.get("why"):
                        wrap(a["why"], indent=6, color="dim")

            section("WHY")
            wrap(d.get("rationale", ""), indent=4)
            self.show_verdict(d["decision_id"])

            section(f"ROWS THAT DEPEND ON IT ({len(deps)})")
            for r in deps[:8]:
                print("  • " + colorize(f"§{r['ccc']}", "cyan") + "  " + self.claim_text(r))
            if len(deps) > 8:
                print(colorize(f"    … and {len(deps) - 8} more", "dim"))

            menu([("y", "Approve", "green"), ("n", "Reject", "red"), ("e", "Edit name/description", "yellow"),
                  ("s", "Skip", "dim"), ("q", "Quit", "magenta")])
            choice = ask("ynesq")
            if choice == "q":
                return False
            if choice == "s":
                self.session["skipped"] += 1
                continue
            if choice == "e":
                for field in ("name", "description"):
                    new = input(f"  {field} [{d.get(field)}]: ").strip()
                    if new:
                        d = {**d, field: new}
                self.session["edited"] += 1
                choice = "y"
            stamp = {"reviewed": date.today().isoformat()}
            if choice == "y":
                append_row(TYPES_APPROVED, {**d, **stamp})
                self.approved_types[d["decision_id"]] = d
                self.session["approved"] += 1
            else:
                append_row(TYPES_REJECTED, {**d, **stamp})
                self.rejected_types.add(d["decision_id"])
                self.session["rejected"] += 1
        return True

    # -- rows --------------------------------------------------------------
    def claim_text(self, r: dict) -> str:
        if r["kind"] == "teaches":
            return f"teaches about {colorize(self.name(r['type_id']), 'yellow')}"
        return f"{colorize(self.name(r['type_id']), 'yellow')}  →  {colorize(self.name(r['antitype_id']), 'green')}"

    def card(self, r: dict, i: int, n: int) -> None:
        self.header(STAGES[r["bucket"]], i, n)
        print()
        meta = [f"§{r['ccc']}", r["relation"], f"{r.get('confidence')} confidence"]
        if r.get("category"):
            meta.append(r["category"])
        print("  " + colorize("  ·  ".join(meta), "cyan") + colorize(f"     {r['cand_id']}", "dim"))

        section("LINK" if r["kind"] != "teaches" else "TEACHES ABOUT")
        if r["kind"] == "teaches":
            print("  " + colorize(self.name(r["type_id"]), "yellow"))
        else:
            print("  " + colorize(self.name(r["type_id"]), "yellow"))
            print("    " + colorize("prefigures", "dim") if r["relation"] == "explicit"
                  else "    " + colorize("prepares the way for / is fulfilled in", "dim"))
            print("  " + colorize(self.name(r["antitype_id"]), "green"))
        for tid in (r.get("type_id"), r.get("antitype_id")):
            d = self.new_type(tid)
            if d:
                wrap(f"New Type: {d['description']}", indent=4, color="dim")
        if r.get("existing_category") and r.get("existing_category") != r.get("category"):
            wrap(f"The existing link's category ({r['existing_category']}) is kept.", indent=4, color="dim")

        section("THE CATECHISM SAYS")
        quotes = [(r["ccc"], r["quote"])] if r.get("quote") else [(q["ccc"], q["quote"]) for q in r["quotes"]]
        for n_, q in quotes:
            wrap(f"“{q}”", indent=4)
            print(colorize(f"      — §{n_}", "dim"))

        section("EXTRACTOR")
        wrap(r.get("rationale", ""), indent=4, color="dim")
        self.show_verdict(r["cand_id"])

        verses = [v for vs in r.get("verse_ids", {}).values() for v in vs]
        if verses:
            section("VERSE EVIDENCE")
            wrap(", ".join(display_ref(v) for v in verses[:10]) + (" …" if len(verses) > 10 else ""), indent=4)

    def edit(self, r: dict) -> dict:
        r = dict(r)
        known = self.known_ids()
        for field in ("type_id", "antitype_id", "category", "relation"):
            if field == "antitype_id" and r["kind"] == "teaches":
                continue
            new = input(f"  {field} [{r.get(field)}]: ").strip()
            if not new:
                continue
            if field.endswith("_id") and new not in known:
                print(colorize(f"  unknown Type id {new!r}; kept {r.get(field)}", "red"))
            elif field == "category" and new not in VALID_CATEGORIES:
                print(colorize(f"  category must be one of {sorted(VALID_CATEGORIES)}", "red"))
            else:
                r[field] = new
        if r.get("verse_ids") and input("  Drop the verse evidence? [y/N] ").strip().lower() == "y":
            r["verse_ids"] = {}
        r["edited"] = True
        return r

    def record(self, r: dict, approved: bool, how: str) -> None:
        out = {k: r[k] for k in ("cand_id", "ccc", "kind", "relation", "type_id", "antitype_id", "category",
                                 "confidence", "verse_ids", "batch") if k in r}
        out.update({"quote": r.get("quote"), "quotes": r.get("quotes"),
                    "verifier": self.verdicts.get(r["cand_id"]), "existing_category": r.get("existing_category"),
                    "review": {"decision": "approved" if approved else "rejected", "how": how,
                               "edited": r.get("edited", False), "date": date.today().isoformat()}})
        append_row(APPROVED if approved else REJECTED, out)
        self.done.add(r["cand_id"])
        self.session["approved" if approved else "rejected"] += 1
        if r.get("edited"):
            self.session["edited"] += 1

    def bulk_safe(self, r: dict) -> bool:
        """Verifier accepted it, or revised only the relation label (which isn't imported onto the link)."""
        v = self.verdicts.get(r["cand_id"], {})
        if v.get("verdict") == "accept":
            return True
        changes = [k for k in ("relation", "type_id", "antitype_id", "category") if v.get(k)]
        return v.get("verdict") == "revise" and changes == ["relation"]

    def blocked(self, r: dict) -> str | None:
        """'rejected' if a Type decision it needs was rejected; 'pending' if one isn't approved yet."""
        needs = r.get("pending_decisions", [])
        if any(d in self.rejected_types for d in needs):
            return "rejected"
        if any(d not in self.approved_types for d in needs):
            return "pending"
        return None

    def review_rows(self, only_bucket: str | None) -> None:
        queue = sorted((r for r in self.rows if r["bucket"] in BUCKET_ORDER and r["cand_id"] not in self.done
                        and (only_bucket is None or r["bucket"] == only_bucket)),
                       key=lambda r: (BUCKET_ORDER[r["bucket"]], r["ccc"]))
        waiting = [r for r in queue if self.blocked(r) == "pending"]
        queue = [r for r in queue if self.blocked(r) != "pending"]
        if waiting:
            print(colorize(f"\n  {len(waiting)} rows wait on Type decisions you haven't reviewed yet.", "yellow"))
            input(colorize("  Press Enter to continue…", "dim"))
        for i, r in enumerate(queue, 1):
            if r["cand_id"] in self.done:
                continue
            self.card(r, i, len(queue))
            blocked = self.blocked(r) == "rejected"
            revise = self.verdicts.get(r["cand_id"], {}).get("verdict") == "revise"
            bulk = r["bucket"] in BULK_BUCKETS and not blocked
            if blocked:
                print()
                wrap("⚠ A Type decision this row needs was rejected: remap it with [e], or reject it.",
                     color="red")
            options = ([] if blocked else [("y", "Approve", "green")]) + [("n", "Reject", "red")]
            if revise and not blocked:
                options.append(("r", "Apply verifier's fix", "yellow"))
            options += [("e", "Edit", "yellow"), ("v", "Full paragraph", "cyan"), ("s", "Skip", "dim")]
            if bulk:
                rest = sum(1 for x in queue[i - 1:] if x["bucket"] == r["bucket"]
                           and x["cand_id"] not in self.done and self.bulk_safe(x))
                options.append(("A", f"Approve the rest of this bucket ({rest} verifier-OK)", "green"))
            options.append(("q", "Quit", "magenta"))
            menu(options)
            keys = "".join(k for k, _, _ in options)
            while True:
                choice = ask(keys)
                if choice == "v":
                    self.show_paragraph(r["ccc"])
                    continue
                break
            if choice == "q":
                break
            if choice == "s":
                self.session["skipped"] += 1
                continue
            if choice == "A":
                rest = [x for x in queue[i - 1:] if x["bucket"] == r["bucket"] and x["cand_id"] not in self.done
                        and self.bulk_safe(x)]
                for x in rest:
                    v = self.verdicts[x["cand_id"]]
                    label = {"relation": v["relation"]} if v["verdict"] == "revise" else {}
                    self.record({**x, **label}, True, f"bulk: bucket {x['bucket']}, verifier {v['verdict']}")
                print(colorize(f"\n  Approved {len(rest)} bucket-{r['bucket']} rows; the others stay in the queue.",
                               "green"))
                input(colorize("  Press Enter to continue…", "dim"))
                continue
            if choice == "e":
                self.record(self.edit(r), True, "edited")
            elif choice == "r":
                v = self.verdicts[r["cand_id"]]
                changes = {k: v[k] for k in ("relation", "type_id", "antitype_id", "category") if v.get(k)}
                unknown = [val for k, val in changes.items() if k.endswith("_id") and val not in self.known_ids()]
                if unknown:
                    print(colorize(f"\n  The fix names a Type that doesn't exist yet ({', '.join(unknown)}). "
                                   "Use [e] to remap the row, or skip it.", "red"))
                    input(colorize("  Press Enter to continue…", "dim"))
                    continue
                self.record({**r, **changes, "edited": True}, True, "verifier revision")
            else:
                self.record(r, choice == "y", "manual")


def auto_verifier(review: Review) -> list[str]:
    """Apply the independent verifier's verdicts without manual review (user-authorized).

    accept -> approve; reject -> reject; revise -> approve with the verifier's correction.
    Anything that can't be applied faithfully (a correction naming a Type that doesn't exist, or a
    row whose Type decision was rejected while its own verdict wasn't) is left for manual review.
    Every record says it was applied automatically, so the Methods copy can say so.
    """
    how = f"auto: verifier {{}} (user-authorized {date.today().isoformat()})"
    left = []
    stamp = {"reviewed": date.today().isoformat(), "review_how": "auto: verifier verdict (user-authorized)"}
    for d in review.decisions.values():
        did = d["decision_id"]
        if d["action"] in ("use_existing", "reject") or did in review.approved_types or did in review.rejected_types:
            continue
        verdict = review.verdicts.get(did, {}).get("verdict")
        if verdict in ("accept", "revise"):
            append_row(TYPES_APPROVED, {**d, **stamp})
            review.approved_types[did] = d
        elif verdict == "reject":
            append_row(TYPES_REJECTED, {**d, **stamp})
            review.rejected_types.add(did)
        else:
            left.append(f"{did}: no verdict")
    for r in sorted(review.rows, key=lambda r: (BUCKET_ORDER.get(r["bucket"], 9), r["ccc"])):
        if r["bucket"] not in BUCKET_ORDER or r["cand_id"] in review.done:
            continue
        v = review.verdicts.get(r["cand_id"], {})
        verdict = v.get("verdict")
        if verdict == "reject":
            review.record(r, False, how.format("reject"))
            continue
        if review.blocked(r):
            left.append(f"{r['cand_id']}: depends on a {review.blocked(r)} Type decision")
            continue
        if verdict == "accept":
            review.record(r, True, how.format("accept"))
        elif verdict == "revise":
            changes = {k: v[k] for k in ("relation", "type_id", "antitype_id", "category") if v.get(k)}
            unknown = [val for k, val in changes.items() if k.endswith("_id") and val not in review.known_ids()]
            if unknown:
                left.append(f"{r['cand_id']}: the verifier's fix needs a Type that doesn't exist ({', '.join(unknown)})")
                continue
            review.record({**r, **changes, "edited": True}, True, how.format("revision"))
        else:
            left.append(f"{r['cand_id']}: no verdict")
    return left


def stats() -> None:
    rows = load_jsonl(PASS_DIR / "candidates_final.jsonl")
    approved, rejected = load_or_empty(APPROVED), load_or_empty(REJECTED)
    done = {r["cand_id"] for r in approved + rejected}
    print()
    rule("═")
    print(colorize("  CATECHISM PASS REVIEW: PROGRESS", "bold"))
    rule("═")
    print(f"  Type decisions:  {colorize(str(len(load_or_empty(TYPES_APPROVED))) + ' approved', 'green')}  "
          f"{colorize(str(len(load_or_empty(TYPES_REJECTED))) + ' rejected', 'red')}")
    for b, label in (("C", "New links (new Types)"), ("B", "New links"), ("A", "Sources on existing links"),
                     ("T", "Teaches")):
        total = [r for r in rows if r["bucket"] == b]
        n = sum(r["cand_id"] in done for r in total)
        color = "green" if total and n == len(total) else "yellow" if n else "dim"
        print(f"  {label:28} {colorize(f'{n}/{len(total)} reviewed', color)}")
    print(f"  Approved rows: {colorize(str(len(approved)), 'green')}   Rejected rows: {colorize(str(len(rejected)), 'red')}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Review the Catechism typology pass")
    parser.add_argument("--bucket", choices=sorted(BUCKET_ORDER), help="Review only this bucket (skips Type decisions)")
    parser.add_argument("--stats", action="store_true", help="Show progress and exit")
    parser.add_argument("--auto-verifier", action="store_true",
                        help="Apply the verifier's verdicts to everything not yet reviewed (user-authorized)")
    args = parser.parse_args()
    if args.stats:
        stats()
        return
    if args.auto_verifier:
        left = auto_verifier(Review())
        for item in left:
            print(colorize(f"  left for manual review: {item}", "yellow"))
        stats()
        return
    review = Review()
    # --bucket goes straight to that bucket's rows; a full run reviews Type decisions first
    if args.bucket or review.review_types():
        review.review_rows(args.bucket)
    stats()


if __name__ == "__main__":
    main()
