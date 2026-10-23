"""Shared rules for the Catechism typology pass.

The pass reads every Catechism paragraph with Claude Code subagents (no API
calls). Prep writes the batch files the extractor agents read; the checker
validates their JSONL output (verbatim quotes, Type decisions, verse refs) so
an agent can self-check before finishing, and reconcile reuses the same rules.

See dev/active/ccc-typology-pass/ for the plan.
"""

import json
import os
import re
from pathlib import Path

from src.config import settings
from src.data.catechism_citation_parser import parse_scripture_citation
from src.data.typology_schemas import VALID_CATEGORIES, VALID_CONFIDENCES, VALID_TESTAMENTS
from src.db.connection import Neo4jConnection, get_connection

# CCC_PASS_DIR lets a dry run work on a scratch copy
PASS_DIR = Path(os.environ.get("CCC_PASS_DIR") or settings.DATA_DIR.parent / "extracted" / "ccc_pass")

# Contiguous ranges by Part of the Catechism (plan §4.2)
BATCHES: dict[str, tuple[int, int]] = {
    "01": (1, 390),
    "02": (391, 747),
    "03": (748, 1065),
    "04": (1066, 1380),
    "05": (1381, 1690),
    "06": (1691, 2130),
    "07": (2131, 2557),
    "08": (2558, 2865),
}
CONTEXT_PARAGRAPHS = 3  # read-only paragraphs shown before each batch

RELATIONS = {"explicit", "preparatory", "prophecy", "nt-figure", "teaches-only", "synthesized"}
DECISIONS = {"existing", "broaden", "merge", "new"}
MAX_QUOTE_CHARS = 300

_VERSE_ID = re.compile(r"^[0-9A-Z]{3}-\d+-\d+$")


def normalize(text: str) -> str:
    """Normalize for verbatim comparison: straight quotes, no emphasis marks, single spaces."""
    text = text.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "*": None}))
    return " ".join(text.split())


def batch_of(paragraph: int) -> str:
    """The batch whose primary range holds this paragraph."""
    for batch, (first, last) in BATCHES.items():
        if first <= paragraph <= last:
            return batch
    raise ValueError(f"CCC {paragraph} is outside every batch")


# ---------------------------------------------------------------------------
# Graph reads
# ---------------------------------------------------------------------------

def fetch_paragraphs(connection: Neo4jConnection | None = None) -> dict[int, dict]:
    """{paragraph: {text, cited[]}} for every Catechism paragraph, with its Scripture CITES."""
    connection = connection or get_connection()
    with connection.session() as s:
        rows = s.run(
            "MATCH (c:CatechismParagraph) "
            "RETURN c.paragraph AS n, c.text AS text, [(c)-[:CITES]->(v:Verse) | v.id] AS cited"
        )
        return {r["n"]: {"text": r["text"], "cited": sorted(r["cited"])} for r in rows}


def fetch_catalog(connection: Neo4jConnection | None = None) -> list[dict]:
    """Every Type with its current links and teaching paragraphs (what extractors map onto)."""
    connection = connection or get_connection()
    with connection.session() as s:
        rows = s.run(
            "MATCH (t:Type) "
            "RETURN t.id AS id, t.name AS name, t.testament AS testament, t.description AS description, "
            "[(t)-[o:PREFIGURES]->(a:Type) | {id: a.id, category: o.category}] AS out, "
            "[(b:Type)-[i:PREFIGURES]->(t) | {id: b.id, category: i.category}] AS inc, "
            "[(c:CatechismParagraph)-[:TEACHES]->(t) | c.paragraph] AS ccc "
            "ORDER BY t.testament DESC, t.name"
        )
        return [
            {**dict(r), "out": sorted(r["out"], key=lambda x: x["id"]),
             "inc": sorted(r["inc"], key=lambda x: x["id"]), "ccc": sorted(r["ccc"])}
            for r in rows
        ]


def fetch_verse_ids(connection: Neo4jConnection | None = None) -> set[str]:
    connection = connection or get_connection()
    with connection.session() as s:
        return {r["id"] for r in s.run("MATCH (v:Verse) RETURN v.id AS id")}


# ---------------------------------------------------------------------------
# Record checks
# ---------------------------------------------------------------------------

def resolve_verses(refs: list[str]) -> tuple[list[str], list[str]]:
    """Turn verse IDs or standard refs ("Ps 110:4") into verse IDs. Returns (ids, unparseable refs)."""
    ids, bad = [], []
    for ref in refs:
        if _VERSE_ID.match(ref):
            ids.append(ref)
            continue
        parsed = parse_scripture_citation(ref)
        if parsed:
            ids.extend(parsed)
        else:
            bad.append(ref)
    return ids, bad


def _check_quote(quote, paragraph: int, paragraphs: dict[int, dict], where: str) -> list[str]:
    if not isinstance(quote, str) or not quote.strip():
        return [f"{where}: missing quote"]
    if len(quote) > MAX_QUOTE_CHARS:
        return [f"{where}: quote is {len(quote)} chars (max {MAX_QUOTE_CHARS})"]
    if paragraph not in paragraphs:
        return [f"{where}: CCC {paragraph} does not exist"]
    if normalize(quote) not in normalize(paragraphs[paragraph]["text"]):
        return [f"{where}: quote is not verbatim in CCC {paragraph}: {quote[:60]}…"]
    return []


def _check_decision(side: str, d, types: dict[str, dict]) -> list[str]:
    if not isinstance(d, dict):
        return [f"{side}: missing Type decision"]
    errors = []
    decision = d.get("decision")
    if decision not in DECISIONS:
        return [f"{side}: decision must be one of {sorted(DECISIONS)}"]
    if not isinstance(d.get("alternatives_considered"), list):
        errors.append(f"{side}: alternatives_considered must be a list")
    else:
        for alt in d["alternatives_considered"]:
            if not isinstance(alt, dict) or alt.get("id") not in types or not alt.get("why_not"):
                errors.append(f"{side}: each alternative needs a catalog id and why_not ({alt})")
    if not d.get("reasoning"):
        errors.append(f"{side}: missing reasoning")
    if decision in ("existing", "broaden") and d.get("id") not in types:
        errors.append(f"{side}: unknown Type id {d.get('id')!r}")
    if decision == "broaden" and not (d.get("new_name") and d.get("new_description")):
        errors.append(f"{side}: broaden needs new_name and new_description")
    if decision == "merge":
        ids = d.get("merge_ids") or []
        if len(ids) < 2 or any(i not in types for i in ids):
            errors.append(f"{side}: merge needs 2+ existing merge_ids (survivor first)")
    if decision == "new":
        if not (d.get("name") and d.get("description")):
            errors.append(f"{side}: new Type needs name and description")
        if d.get("testament") not in VALID_TESTAMENTS:
            errors.append(f"{side}: new Type testament must be OT or NT")
    return errors


def decision_testament(d: dict, types: dict[str, dict]) -> str | None:
    if d.get("decision") == "new":
        return d.get("testament")
    tid = d.get("merge_ids", [None])[0] if d.get("decision") == "merge" else d.get("id")
    return types.get(tid, {}).get("testament")


def check_record(
    rec: dict, paragraphs: dict[int, dict], types: dict[str, dict], verse_ids: set[str]
) -> tuple[list[str], list[str]]:
    """Validate one extractor row. Returns (errors, warnings)."""
    kind = rec.get("kind")
    if kind == "coverage":
        missing = [k for k in ("batch", "first", "last", "read", "with_findings") if k not in rec]
        return ([f"coverage: missing {missing}"] if missing else []), []
    if kind == "catalog-issue":
        errors = [] if isinstance(rec.get("ccc"), int) and rec.get("issue") else ["catalog-issue: needs ccc and issue"]
        unknown = [i for i in rec.get("ids") or [] if i not in types]
        return errors + ([f"catalog-issue: unknown Type ids {unknown}"] if unknown else []), []

    errors, warnings = [], []
    n = rec.get("ccc")
    if not isinstance(n, int):
        return ["missing integer ccc"], []
    where = f"CCC {n}"
    relation = rec.get("relation")
    if relation not in RELATIONS:
        errors.append(f"{where}: relation must be one of {sorted(RELATIONS)}")

    if kind == "prefigures":
        if relation == "teaches-only":
            errors.append(f"{where}: a teaches-only row must have kind 'teaches'")
        if rec.get("category") not in VALID_CATEGORIES:
            errors.append(f"{where}: category must be one of {sorted(VALID_CATEGORIES)}")
        errors += _check_decision(f"{where} type", rec.get("type"), types)
        errors += _check_decision(f"{where} antitype", rec.get("antitype"), types)
        sides = ("type_verses", "antitype_verses")
        if relation not in ("nt-figure",) and not errors:
            if decision_testament(rec["type"], types) != "OT" or decision_testament(rec["antitype"], types) != "NT":
                warnings.append(f"{where}: not OT → NT ({relation})")
    elif kind == "teaches":
        if relation != "teaches-only":
            errors.append(f"{where}: kind 'teaches' must have relation 'teaches-only'")
        errors += _check_decision(f"{where} type", rec.get("type"), types)
        sides = ("verses",)
    else:
        return [f"{where}: kind must be prefigures, teaches, catalog-issue or coverage"], []

    if rec.get("confidence") not in VALID_CONFIDENCES:
        errors.append(f"{where}: confidence must be high, medium or low")

    if relation == "synthesized":
        quotes = rec.get("quotes") or []
        if len(quotes) < 2:
            errors.append(f"{where}: synthesized rows need quotes from 2+ paragraphs")
        for q in quotes:
            errors += _check_quote(q.get("quote"), q.get("ccc"), paragraphs, f"{where} (quoting {q.get('ccc')})")
    else:
        errors += _check_quote(rec.get("quote"), n, paragraphs, where)

    for side in sides:
        ids, bad = resolve_verses(rec.get(side) or [])
        if bad:
            errors.append(f"{where}: unparseable {side} {bad} (use a verse ID or e.g. 'Gen 14:18', '2 Kgs 5:14')")
        unknown = [v for v in ids if v not in verse_ids]
        if unknown:
            errors.append(f"{where}: {side} not in the graph: {unknown[:5]}")
    return errors, warnings


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
