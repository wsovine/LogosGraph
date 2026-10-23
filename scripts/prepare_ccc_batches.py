#!/usr/bin/env python3
"""Prepare the Catechism typology pass: batch files, Type catalog, gold set.

Reads every Catechism paragraph (with its Scripture CITES) and every Type
(with its current links) from Neo4j, and writes what the extractor subagents
read and what the checker validates against:

    data/extracted/ccc_pass/
        batches/batch-NN.md   paragraphs for one batch (plus read-only context)
        types_catalog.md      the Types extractors map onto (and .json for scripts)
        paragraphs.json       all paragraph texts + cited verse IDs
        verse_ids.json        every Verse ID in the graph
        gold.json             paragraphs the pass must surface (recall check)
        manifest.json         batch ranges, files, word counts

Usage:
    python scripts/prepare_ccc_batches.py
    python scripts/prepare_ccc_batches.py --dry-run
"""

import argparse
import json
import sys
import textwrap
from datetime import date
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.data.book_mapping import display_ref
from src.data.ccc_typology_pass import (
    BATCHES, CONTEXT_PARAGRAPHS, PASS_DIR, fetch_catalog, fetch_paragraphs, fetch_verse_ids,
)
from src.data.typology_schemas import VALID_CATEGORIES

WRAP = 110
NO_SPLIT = {"break_on_hyphens": False, "break_long_words": False}  # keep IDs and quotes intact
PARTS = {"01": "I", "02": "I", "03": "I", "04": "II", "05": "II", "06": "III", "07": "III", "08": "IV"}

# Paragraphs the pass must surface (dev/active/ccc-typology-pass/ccc-typology-pass-context.md)
GOLD = {
    58: "Melchizedek, a figure of Christ",
    64: "holy women of Israel; Mary the purest figure among them",
    559: "Daughter of Zion, a figure of the Church",
    593: "the Temple prefigures Christ's own mystery",
    696: "Elijah's fire on Carmel, a figure of the fire of the Holy Spirit",
    697: "the cloud and light, figures fulfilled by Christ in the Holy Spirit",
    710: "the remnant returning from exile, a prefiguration of the Church",
    720: "John's baptism prefiguring (NT → NT)",
    845: "Noah's ark prefigures the Church",
    1150: "anointing of kings and priests, laying on of hands, sacrifices, Passover → sacraments",
    1217: "baptismal-water prefigurations (creation, flood, Red Sea, Jordan)",
    1219: "Noah's ark, a prefiguring of salvation by Baptism",
    1225: "blood and water, types of Baptism and Eucharist (NT → NT)",
    1294: "chrism in Confirmation and ordination, the sign of consecration (synthesized with 1150)",
    1333: "Melchizedek's bread and wine, a prefiguring of the Church's offering",
    1335: "loaves and Cana prefigure the Eucharist (NT → NT)",
    1541: "priesthood of Aaron, Levites, seventy elders → ordained ministry",
    1548: "the priest of the old law, a figure of Christ",
    1605: "Gen 2:24, the unbreakable union of man and woman (Matrimony)",
    1611: "Ruth, Tobit, Song of Songs: an elevated sense of marriage (Matrimony)",
    1612: "the nuptial covenant with Israel prepared the way for the new covenant",
    2571: "Abraham's hospitality at Mamre foreshadows the Annunciation",
    2593: "Moses' prayer foreshadows Christ's intercession",
    2603: "Jesus' prayer prefigures Gethsemane (NT → NT)",
    2679: "Mary, a figure of the Church (NT → NT)",
}


def words(text: str) -> int:
    return len(text.split())


def wrap(text: str) -> list[str]:
    lines = []
    for para in text.strip().split("\n"):
        lines.extend(textwrap.wrap(para, WRAP, **NO_SPLIT) or [""])
    return lines


def render_paragraph(n: int, p: dict, context: bool) -> list[str]:
    lines = [f"## §{n}" + (" (CONTEXT: read for flow, extract nothing)" if context else "")]
    lines += wrap(p["text"])
    if p["cited"]:
        cited = " · ".join(f"{display_ref(v)} [{v}]" for v in p["cited"])
        lines += textwrap.wrap(f"Cited: {cited}", WRAP, subsequent_indent="  ", **NO_SPLIT)
    return lines + [""]


def render_batch(batch: str, paragraphs: dict[int, dict]) -> tuple[str, int, int]:
    first, last = BATCHES[batch]
    in_range = [n for n in sorted(paragraphs) if first <= n <= last]
    context = [n for n in sorted(paragraphs) if first - CONTEXT_PARAGRAPHS <= n < first]
    body = []
    for n in context:
        body += render_paragraph(n, paragraphs[n], context=True)
    for n in in_range:
        body += render_paragraph(n, paragraphs[n], context=False)
    header = [
        f"# Catechism batch {batch}: §{first}–§{last} (Part {PARTS[batch]})",
        "",
        f"Paragraphs in range: {len(in_range)} · Output: data/extracted/ccc_pass/raw/batch-{batch}.jsonl",
        "Cited verses are shown as 'Display ref [VERSE-ID]'; copy the bracketed ID when you use one.",
        "",
    ]
    text = "\n".join(header + body)
    return text, len(in_range), sum(words(paragraphs[n]["text"]) for n in in_range)


def render_catalog(catalog: list[dict]) -> str:
    lines = [
        f"# Type catalog ({len(catalog)} Types, {date.today().isoformat()})",
        "",
        f"Categories: {', '.join(sorted(VALID_CATEGORIES))}",
        "Each entry: `id` · name (testament): description. Then its current links and the Catechism",
        "paragraphs that already teach it. OT Types list what they prefigure (→); NT Types what prefigures them (←).",
        "",
    ]
    for testament in ("OT", "NT"):
        lines += [f"## {testament} Types", ""]
        for t in (t for t in catalog if t["testament"] == testament):
            lines += textwrap.wrap(
                f"- `{t['id']}` · {t['name']} ({testament}): {t['description'] or '(no description)'}",
                WRAP, subsequent_indent="    ", **NO_SPLIT)
            links = [f"→ {l['id']} ({l['category']})" for l in t["out"]] + \
                    [f"← {l['id']} ({l['category']})" for l in t["inc"]]
            if links:
                lines += textwrap.wrap("links: " + ", ".join(links), WRAP,
                                       initial_indent="    ", subsequent_indent="      ", **NO_SPLIT)
            if t["ccc"]:
                lines.append(f"    CCC: {', '.join(map(str, t['ccc']))}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Prepare Catechism typology pass batches")
    parser.add_argument("--dry-run", action="store_true", help="Print batch sizes and write nothing")
    args = parser.parse_args()

    paragraphs = fetch_paragraphs()
    numbers = sorted(paragraphs)
    covered = {n for first, last in BATCHES.values() for n in range(first, last + 1)}
    gaps = sorted(set(numbers) - covered)
    if gaps:
        sys.exit(f"Paragraphs outside every batch: {gaps[:10]}")
    print(f"Paragraphs: {len(paragraphs)} (§{numbers[0]}–§{numbers[-1]}), "
          f"{sum(words(p['text']) for p in paragraphs.values()):,} words, "
          f"{sum(1 for p in paragraphs.values() if p['cited'])} with Scripture CITES")

    rendered = {b: render_batch(b, paragraphs) for b in BATCHES}
    for b, (text, count, n_words) in rendered.items():
        first, last = BATCHES[b]
        print(f"  batch {b}: §{first}–§{last}  {count:>4} paragraphs  {n_words:>6,} words  "
              f"{text.count(chr(10)) + 1:>5} lines")
    if args.dry_run:
        return

    catalog = fetch_catalog()
    verse_ids = sorted(fetch_verse_ids())
    (PASS_DIR / "batches").mkdir(parents=True, exist_ok=True)
    (PASS_DIR / "raw").mkdir(exist_ok=True)

    for b, (text, _, _) in rendered.items():
        (PASS_DIR / "batches" / f"batch-{b}.md").write_text(text, encoding="utf-8")
    (PASS_DIR / "types_catalog.md").write_text(render_catalog(catalog), encoding="utf-8")
    (PASS_DIR / "types_catalog.json").write_text(json.dumps(catalog, indent=1), encoding="utf-8")
    (PASS_DIR / "paragraphs.json").write_text(
        json.dumps({str(n): p for n, p in paragraphs.items()}), encoding="utf-8")
    (PASS_DIR / "verse_ids.json").write_text(json.dumps(verse_ids), encoding="utf-8")
    (PASS_DIR / "gold.json").write_text(
        json.dumps({str(n): v for n, v in GOLD.items()}, indent=1), encoding="utf-8")
    (PASS_DIR / "manifest.json").write_text(json.dumps({
        "prepared": date.today().isoformat(),
        "paragraphs": len(paragraphs),
        "types": len(catalog),
        "batches": {b: {"first": BATCHES[b][0], "last": BATCHES[b][1], "paragraphs": c, "words": w,
                        "file": f"batches/batch-{b}.md", "output": f"raw/batch-{b}.jsonl"}
                    for b, (_, c, w) in rendered.items()},
    }, indent=1), encoding="utf-8")
    print(f"Wrote batches, catalog ({len(catalog)} Types), {len(verse_ids):,} verse IDs and "
          f"{len(GOLD)} gold paragraphs to {PASS_DIR}")


if __name__ == "__main__":
    main()
