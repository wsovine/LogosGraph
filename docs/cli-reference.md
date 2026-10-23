# CLI Reference

All scripts support `--help` for detailed options.

## Data Extraction

### extract_haydock_footers.py

Extract commentary footers from Haydock USFM files and filter for typology candidates.

```bash
python scripts/extract_haydock_footers.py [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output PATH` | `data/extracted/haydock_footers.jsonl` | Output file path |
| `--filter-typology` | off | Also output filtered typology candidates |
| `-v, --verbose` | off | Enable verbose logging |

**Examples:**

```bash
# Extract all footers
python scripts/extract_haydock_footers.py

# Extract footers and filter for typology keywords
python scripts/extract_haydock_footers.py --filter-typology

# Custom output location
python scripts/extract_haydock_footers.py -o my_footers.jsonl
```

**Output:**
- `haydock_footers.jsonl` - All 21,349 footers
- `haydock_typology_candidates.jsonl` - 872 typology candidates (with `--filter-typology`)

---

### extract_typology_llm.py

Process typology candidates through Claude to extract structured type/antitype relationships.

```bash
python scripts/extract_typology_llm.py [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-i, --input PATH` | `data/extracted/haydock_typology_candidates.jsonl` | Input candidates |
| `-o, --output PATH` | `data/extracted/haydock_typology_raw.jsonl` | Output extractions |
| `--checkpoint PATH` | `data/extracted/.typology_checkpoint.json` | Checkpoint file |
| `--model MODEL` | `claude-haiku-4-5` | Claude model to use |
| `--limit N` | none | Process only N candidates |
| `--resume` | off | Resume from checkpoint |
| `--rate-limit N` | 50 | Max requests per minute |
| `--batch-size N` | 50 | Checkpoint save interval |
| `-v, --verbose` | off | Enable verbose logging |

**Environment:**
- Requires `ANTHROPIC_API_KEY` environment variable

**Examples:**

```bash
# Test with 10 candidates
python scripts/extract_typology_llm.py --limit 10

# Full extraction (~30 min, ~$0.50-1.00)
python scripts/extract_typology_llm.py

# Resume after interruption
python scripts/extract_typology_llm.py --resume

# Use a different model
python scripts/extract_typology_llm.py --model claude-sonnet-4-5
```

**Output:**
- `haydock_typology_raw.jsonl` - Structured extractions with type/antitype pairs

---

## Review

### review_typology.py

Interactive terminal interface for reviewing LLM extractions before import.

```bash
python scripts/review_typology.py [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-i, --input PATH` | `data/extracted/haydock_typology_raw.jsonl` | Input extractions |
| `--approved PATH` | `data/reviewed/typology_approved.jsonl` | Approved output |
| `--rejected PATH` | `data/reviewed/typology_rejected.jsonl` | Rejected output |
| `--progress PATH` | `data/reviewed/.review_progress.json` | Progress file |
| `--stats` | off | Show statistics and exit |
| `--reset` | off | Reset progress and start over |
| `--ai-assist` | off | Enable AI assistant for review suggestions |

**Interactive Commands:**

| Key | Action |
|-----|--------|
| `y` / `Enter` | **Accept AI** - Accept AI suggestion (only with `--ai-assist`) |
| `a` | **Approve** - Select types, confirm category, save |
| `r` | **Reject** - Discard with optional reason |
| `m` | **Modify** - Edit extraction before approving |
| `s` | **Skip** - Review later |
| `v` | **View** - Show full commentary text |
| `q` | **Quit** - Save progress and exit |

**Approval Flow:**

1. Select OT Type (pick existing or create new)
2. Select NT Antitype (pick existing or create new)
3. Confirm category for PREFIGURES relationship
4. Add optional notes
5. Confirm

**AI-Assisted Flow (with `--ai-assist`):**

1. AI analyzes extraction and suggests approve/reject with reasoning
2. AI recommends type/antitype selections from existing types or suggests new ones
3. Press `y` or `Enter` to accept AI suggestion (auto-fills selections)
4. Or press `a/r/m/s` to override with manual decision
5. Final confirmation still required before saving

**Environment:**
- `--ai-assist` requires `ANTHROPIC_API_KEY` environment variable
- Uses Claude 3.5 Haiku for cost-effective suggestions

**Examples:**

```bash
# Check review progress
python scripts/review_typology.py --stats

# Start or resume review
python scripts/review_typology.py

# Start over from beginning
python scripts/review_typology.py --reset

# Review with AI assistance
python scripts/review_typology.py --ai-assist
```

**Output:**
- `typology_approved.jsonl` - Approved extractions with normalized type IDs
- `typology_rejected.jsonl` - Rejected extractions with reasons
- `new_types.jsonl` - New types created during review

---

## Membership Enrichment

Pipeline for enriching the MEMBER_OF evidence layer from cross-references.
See [typology-workflow.md](typology-workflow.md#step-5-enrich-member_of-evidence-optional) for the full guide.

### mine_member_candidates.py

Mine MEMBER_OF candidates: verses cross-referenced by multiple existing
member verses of a Type. Read-only against the database.

```bash
# Mine with defaults (corroboration >= 2, hub degree <= 150, 40 per type)
python scripts/mine_member_candidates.py

# Stricter mining
python scripts/mine_member_candidates.py --min-corroboration 3 --max-degree 100
```

**Options:**
- `-o, --output` - Output JSONL (default: `data/extracted/member_candidates.jsonl`)
- `--min-corroboration` - Min member verses cross-referencing the candidate (default: 2)
- `--max-degree` - Hub filter: max total cross-references on candidate (default: 150)
- `--per-type-cap` - Max candidates per type, 0 disables (default: 40)

---

### adjudicate_memberships.py

Judge each mined candidate against its verse text using the theologian
persona (`.claude/agents/theologian.md`). Requires `ANTHROPIC_API_KEY`.

```bash
# Test with 5 candidates
python scripts/adjudicate_memberships.py --limit 5

# Full run with resume support
python scripts/adjudicate_memberships.py --resume

# Match the interactive review assistant's model
python scripts/adjudicate_memberships.py --model claude-opus-4-8
```

**Options:**
- `-i, --input` / `-o, --output` - JSONL paths (defaults under `data/extracted/`)
- `--model` - Model (default: `claude-sonnet-4-6`)
- `--limit` - Process only N candidates (testing)
- `--resume` - Skip already-processed candidates via checkpoint
- `--rate-limit` - Max requests/minute (default: 50)

---

### review_memberships.py

Interactive human review of theologian-accepted candidates.

```bash
# Check progress
python scripts/review_memberships.py --stats

# Review accepted candidates (y/n/s/q)
python scripts/review_memberships.py

# Also second-guess theologian rejections
python scripts/review_memberships.py --include-rejected
```

**Output:**
- `data/reviewed/member_of_approved.jsonl` - Approved memberships
- `data/reviewed/member_of_rejected.jsonl` - Rejected candidates

---

### import_memberships.py

Import approved memberships as MEMBER_OF edges with provenance
(`source: 'crossref-mined'`, `confidence`, `corroboration`, `reviewed`).
Idempotent; never modifies existing edges.

```bash
# Preview
python scripts/import_memberships.py --dry-run

# Import
python scripts/import_memberships.py
```

---

## Catechism Typology Pass

A systematic read of all 2,865 Catechism paragraphs for typology. The LLM steps (extraction, Type
consolidation, verification) run as **Claude Code subagents**, not API scripts. Their instructions live in
`.claude/agents/ccc-typology-extractor.md` and `.claude/agents/theologian.md` (local; `.claude/` is gitignored).
These scripts are the deterministic steps around them. Outputs go to `data/extracted/ccc_pass/`. See
[typology-workflow.md](typology-workflow.md#step-6-catechism-typology-pass).

### prepare_ccc_batches.py

Write the extractor inputs: 8 batch files (contiguous paragraph ranges by Part), the Type catalog, all
paragraph texts with their Scripture CITES, the Verse ID list, and the recall gold set. Requires Neo4j.

```bash
python scripts/prepare_ccc_batches.py --dry-run   # print batch sizes only
python scripts/prepare_ccc_batches.py
```

### check_ccc_raw.py

Validate one batch of extractor output (`raw/batch-NN.jsonl`): verbatim quotes, Type decisions with
alternatives considered, categories, resolvable verse refs, and a coverage row. No database needed.
Extractor agents run it on themselves before finishing.

```bash
python scripts/check_ccc_raw.py 04
```

### reconcile_ccc_typology.py

Merge all batches: re-check rows, sort them into review buckets (A source on an existing link, B new link,
C needs a Type decision, T teaches-only, X held), build the Type ledger, measure gold recall, and write
`reconcile-report.md`.

| Option | Description |
|--------|-------------|
| `--batches NN …` | Only these batches |
| `--check-decisions` | Validate `type_decisions.jsonl` against the ledger |
| `--apply-decisions` | Rewrite candidates to final Type ids → `candidates_final.jsonl` |

### build_ccc_verify_packets.py

Build blind packets for the verifier (claims + Catechism text + a recall sample, without the extractor's
reasoning), and check the verdict files.

```bash
python scripts/build_ccc_verify_packets.py --packets 6
python scripts/build_ccc_verify_packets.py --check
```

### review_ccc_typology.py

Interactive review (Type decisions first, then new links, then Catechism sources on existing links, then
teaches rows). Writes `data/reviewed/ccc_typology_approved.jsonl` / `_rejected.jsonl` and the Type changes
overlay `data/reviewed/type_changes.jsonl`. Resumable.

| Option | Description |
|--------|-------------|
| `--bucket {A,B,C,T}` | Review one bucket (skips Type decisions) |
| `--stats` | Show progress |
| `--auto-verifier` | Apply the verifier's verdicts to everything not yet reviewed (each record is labeled as such) |

Keys: `y` approve · `n` reject · `e` edit · `r` apply the verifier's fix · `v` full paragraph · `s` skip ·
`q` quit · `A` approve the rest of bucket A or T (verifier-accepted or label-only).

---

## Database

### import_all.py

Import all data into Neo4j database.

```bash
python scripts/import_all.py
```

**Requirements:**
- Neo4j running at `NEO4J_URI`
- Valid credentials in `.env`

**Imports:**
- Bible verses and books
- Cross-references (TSK + Haydock)
- Catechism paragraphs and citations
- Typology (if available)

---

### import_typology.py

Import Type nodes and PREFIGURES / MEMBER_OF / TEACHES edges from the CCC seed files and reviewed Haydock extractions.

```bash
python scripts/import_typology.py [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--types`, `--prefigures`, `--memberships`, `--teaches` | Run only these steps (default: all) |
| `--seed-only` | Only curated CCC seed data |
| `--reviewed-only` | Only reviewed Haydock data |
| `--reset` | Delete all Type nodes and typology edges first, then import everything |
| `-v, --verbose` | Enable verbose logging |

The import only adds or accumulates (MERGE), so a correction to an existing seed or reviewed row (e.g. a fixed verse ID) takes effect only with `--reset`. `--reset` also removes the crossref-mined MEMBER_OF edges, so follow it with `import_memberships.py`:

```bash
python scripts/import_typology.py --reset
python scripts/import_memberships.py
python scripts/validate_import.py
```

---

### validate_import.py

Validate database state after import.

```bash
python scripts/validate_import.py
```

**Checks:**
- Node counts (Verses, Books, CCC, Types)
- Relationship counts
- Data integrity

---

## Module Testing

Test individual modules directly:

```bash
# Test Haydock footer parser
python -m src.data.haydock_footer_parser

# Test LLM extractor (requires API key)
python -m src.data.typology_extractor

# Validate seed data schemas
python -m src.data.typology_schemas

# Unit tests (requires the dev extra: pip install -e ".[dev]")
python -m pytest tests/
```
