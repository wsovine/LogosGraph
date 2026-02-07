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
```
