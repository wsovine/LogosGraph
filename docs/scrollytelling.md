# Scrollytelling Sites

LogosGraph publishes three scroll-driven sites built from the graph. Each lives in its own GitHub repo and is
included here as a git submodule under `scrollytelling/`. Each is served by GitHub Pages from its `main` branch.

| Site | What it shows | Live | Repo (submodule) |
|------|---------------|------|------------------|
| **Old and New Testament arcs** | Arcs between Old and New Testament books, from the Haydock cross-references, with the most-referenced verses per book | [bible-crossrefs-visualization](https://wsovine.github.io/bible-crossrefs-visualization/) | [wsovine/bible-crossrefs-visualization](https://github.com/wsovine/bible-crossrefs-visualization) (`scrollytelling/old_and_new_testament_arcs`) |
| **Bible timeline** | The 73 books in chronological order, placed by when their events happen (or when they were written), with a painting per book | [bible-timeline](https://wsovine.github.io/bible-timeline/) | [wsovine/bible-timeline](https://github.com/wsovine/bible-timeline) (`scrollytelling/bible_timeline`) |
| **Shadow & Fulfillment** | Biblical typology: a guided story through Old Testament figures and their New Testament fulfillments, then an explorer of every figure | [bible-typology](https://wsovine.github.io/bible-typology/) | [wsovine/bible-typology](https://github.com/wsovine/bible-typology) (`scrollytelling/bible_typology`) |

## Shared conventions

- **No build step.** Plain HTML, CSS and ES modules. Libraries load from a CDN: D3 and Scrollama on the arcs and
  typology sites; the timeline uses neither.
- **Data is generated, not hand-edited** (the timeline is the exception; see below). Export scripts in each site's
  `export/` folder import this repo's `src.db.connection` and query Neo4j, so run them with LogosGraph's Neo4j up.
  If Neo4j isn't on the default port, set `NEO4J_URI` (e.g. `NEO4J_URI=bolt://localhost:17687`).
- **Analytics.** All three sites report to the same Google Analytics (GA4) property, `G-330XSHELBN`. The typology
  site loads it only on `wsovine.github.io`, so local previews and tests don't count as visits.
- **Publishing.** A push to a site repo's `main` goes live within a few minutes. GitHub Pages lets browsers cache
  files for about 10 minutes.

## Updating a site

```bash
cd scrollytelling/<site>
# ...regenerate data and/or edit, then commit in the site repo
git push origin main                       # goes live

cd ../..
git add scrollytelling/<site>              # record the new site commit in LogosGraph
git commit -m "chore: bump the <site> submodule"
git push origin main
```

After cloning LogosGraph, run `git submodule update --init` to fetch the sites.

## Old and New Testament arcs

```bash
cd scrollytelling/old_and_new_testament_arcs
python export/export_books.py        # -> data/books.json   (book order, verse positions, dates)
python export/export_crossrefs.py    # -> data/crossrefs-ot-to-nt.json, data/crossrefs-nt-to-ot.json (Haydock)
python export/export_top_verses.py   # -> data/top-verses.json
python3 -m http.server 8000          # preview at http://127.0.0.1:8000/
```

The site's own [README](https://github.com/wsovine/bible-crossrefs-visualization#readme) describes its structure.

## Bible timeline

The timeline's `data/books.json` is **maintained by hand**. It started as the output of the arcs site's
`export_books.py` (book positions plus the `dateWritten*` / `dateEvents*` fields from the `Book` nodes). Each book's
`backgroundImage` was then added by hand. Don't overwrite it with a fresh export: re-run `export_books.py` and copy
only the fields that changed. The paintings live in `images/`, and their credits are in `data/artwork_metadata.json`.
(The file was originally a symlink to the arcs data. GitHub Pages can't serve symlinks, so it is a real file now.)

Preview with `python3 -m http.server 8000` from `scrollytelling/bible_timeline`.

## Shadow & Fulfillment (typology)

Built from the typology layer (`Type` nodes, `PREFIGURES`, `MEMBER_OF`, `TEACHES`; see
[Graph Schema](graph-schema.md) and [Typology Workflow](typology-workflow.md)).

```bash
cd scrollytelling/bible_typology
python export/export_typology.py     # -> data/typology.json (figures and links)
python export/render_story.py        # -> data/story.json + export/story-draft.md (validates the script)
python export/export_evidence.py     # -> data/evidence.json (explorer verses, notes, Catechism excerpts)
python3 export/stamp.py              # -> index.html (content-hash URLs; run before every commit)
python3 serve.py                     # preview at http://127.0.0.1:8765/ (no browser caching)
```

- **The story script** is `export/story.toml`. `render_story.py` refuses to write `story.json` if any verse,
  Catechism paragraph, link or quote in it doesn't check out against the graph and its sources.
- **Clarification notes** (Catechism teaching shown beside historical commentary) are in `export/context_notes.toml`.
- **Chapter paintings** are public-domain works from Wikimedia Commons, made with `export/prepare_art.py` and
  credited in `[chapter.art]` entries in `story.toml`. The compiler enforces the image budget.
- **Version stamps.** `stamp.py` gives every module, stylesheet and data file a content-hash URL, so a deploy never
  mixes old and new files. A local pre-commit hook can run `python3 export/stamp.py --check`; hooks aren't
  versioned, so each clone needs its own.
- Typology changes made in this repo (renames, merges, new links) flow to the site by re-importing (see the
  [CLI Reference](cli-reference.md)) and re-running the four commands above.

The site's [README](https://github.com/wsovine/bible-typology#readme) has the full data pipeline, the art workflow
and design notes.
