# Typology Workflow

This guide walks through the complete process of extracting, reviewing, and importing biblical typology data.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                            │
├─────────────────────────────────────────────────────────────────┤
│  CCC Paragraphs          Haydock Commentary                     │
│  (Manual curation)       (LLM extraction)                       │
│         │                       │                               │
│         ▼                       ▼                               │
│  data/seed/*.json        data/extracted/*.jsonl                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      HUMAN REVIEW                               │
├─────────────────────────────────────────────────────────────────┤
│  Interactive terminal reviewer                                  │
│  - Approve/Reject/Modify extractions                            │
│  - Map to existing types or create new ones                     │
│  - Assign categories to relationships                           │
│         │                                                       │
│         ▼                                                       │
│  data/reviewed/typology_approved.jsonl                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      NEO4J IMPORT                               │
├─────────────────────────────────────────────────────────────────┤
│  Type nodes, PREFIGURES edges, MEMBER_OF edges                  │
└─────────────────────────────────────────────────────────────────┘
```

## Step 1: Extract Haydock Footers

Extract all commentary footers and filter for typology-related content.

```bash
python scripts/extract_haydock_footers.py --filter-typology
```

**Output:**
- `data/extracted/haydock_footers.jsonl` (21,349 footers)
- `data/extracted/haydock_typology_candidates.jsonl` (872 candidates)

**Typology Keywords:**
The filter looks for these patterns:
- `type of`, `figure of`, `prefigure`, `foreshadow`
- `shadow of`, `image of`, `represent`, `typify`
- `antitype`, `fulfill`, `symbol`

## Step 2: Run LLM Extraction

Process candidates through Claude to extract structured type/antitype pairs.

### Setup

Ensure your API key is configured:

```bash
# In .env file
ANTHROPIC_API_KEY=sk-ant-...

# Or export directly
export ANTHROPIC_API_KEY=sk-ant-...
```

### Test Run

Start with a small batch to verify everything works:

```bash
python scripts/extract_typology_llm.py --limit 10
```

### Full Extraction

Process all 872 candidates:

```bash
python scripts/extract_typology_llm.py
```

**Estimated:**
- Time: ~30 minutes at 50 RPM
- Cost: ~$0.50-1.00 (Claude Haiku 4.5)

### Resume After Interruption

If the process is interrupted (Ctrl+C or error), resume:

```bash
python scripts/extract_typology_llm.py --resume
```

**Output:**
- `data/extracted/haydock_typology_raw.jsonl`

## Step 3: Review Extractions

Interactively review LLM extractions for quality control.

### Check Progress

```bash
python scripts/review_typology.py --stats
```

### Start Reviewing

```bash
python scripts/review_typology.py
```

### Review Interface

For each extraction, you'll see:
- Verse reference and commentary text
- LLM-extracted type and antitype
- Category and confidence
- LLM's reasoning

### Actions

| Key | Action | Description |
|-----|--------|-------------|
| `a` | Approve | Accept and map to types |
| `r` | Reject | Discard (false positive) |
| `m` | Modify | Edit before approving |
| `s` | Skip | Review later |
| `v` | View | See full commentary |
| `q` | Quit | Save and exit |

### Approval Flow

When you press `a`:

1. **Select OT Type**
   ```
   Existing OT types:
     1. Circumcision (circumcision)
     2. Cloud in the Desert (cloud-in-desert)
     ...
   [n] Create NEW type
   ```

2. **Select NT Antitype**
   ```
   Existing NT types:
     1. Baptism (baptism)
     2. Christ (christ)
     ...
   [n] Create NEW type
   ```

3. **Confirm Category**
   ```
   LLM suggested: Christological
   1. Christological
   2. Covenantal
   3. Ecclesial
   4. Eschatological
   5. Marian
   6. Sacramental
   ```

4. **Add Notes** (optional)

5. **Confirm**

### Creating New Types

If the LLM found a type not in the existing list:

```
CREATE NEW TYPE
  Name [Adam]:
  ID [adam]:
  Description (optional): The first man, created in God's image
  Created new type: adam
```

**Output:**
- `data/reviewed/typology_approved.jsonl` - Approved with normalized IDs
- `data/reviewed/typology_rejected.jsonl` - Rejected extractions
- `data/reviewed/new_types.jsonl` - New types created

## Step 4: Import to Neo4j

```bash
python scripts/import_typology.py
```

This will:
1. Create Type nodes (seed + new)
2. Create PREFIGURES relationships with categories
3. Create MEMBER_OF relationships (verse → type)
4. Create TEACHES relationships (CCC → type)

## Step 5: Enrich MEMBER_OF Evidence (optional)

The initial review yields relatively few member verses per Type (~3 on
average). The enrichment pipeline mines the cross-reference layer for
additional evidence verses, with two safety gates before anything reaches
the database:

```bash
# 1. Structural mining (read-only): candidates must be cross-referenced
#    by >= 2 existing member verses; hub verses excluded
python scripts/mine_member_candidates.py

# 2. Theologian adjudication: each candidate judged against its actual
#    verse text (catches Vulgate-vs-modern versification mismatches)
python scripts/adjudicate_memberships.py --resume

# 3. Human review of accepted candidates
python scripts/review_memberships.py

# 4. Import with provenance, then validate
python scripts/import_memberships.py
python scripts/validate_import.py
```

Mined edges carry `source: 'crossref-mined'` plus `confidence`,
`corroboration`, and `reviewed` properties; edges from the original curated
review have no properties. To query the curated evidence layer only:

```cypher
MATCH (v:Verse)-[r:MEMBER_OF]->(t:Type) WHERE r.source IS NULL ...
```

**Membership criterion** (what the adjudicator and reviewer enforce): a
verse is a member only if its text *directly witnesses* the concept --
narrates, institutes, prophesies, or explicitly invokes it. Thematic
similarity is not membership, and a verse about the antitype is not
evidence for the type.

## Step 6: Catechism Typology Pass

The CCC seed (Step 0) was a hand-picked set of 13 paragraphs. This pass reads **every** Catechism
paragraph. The LLM work runs as Claude Code subagents (Opus); the scripts around it are deterministic.

```bash
# 1. Prep: 8 batches, the Type catalog and the gold set → data/extracted/ccc_pass/
python scripts/prepare_ccc_batches.py

# 2. Extract: one ccc-typology-extractor agent per batch writes raw/batch-NN.jsonl
#    and self-checks with:
python scripts/check_ccc_raw.py NN

# 3. Reconcile: buckets, Type ledger, gold recall
python scripts/reconcile_ccc_typology.py

# 4. Consolidate Types: one theologian agent turns the ledger into type_decisions.jsonl
#    (existing / new / broaden / rename / merge, with every affected link checked), then:
python scripts/reconcile_ccc_typology.py --check-decisions
python scripts/reconcile_ccc_typology.py --apply-decisions

# 5. Verify: blind theologian verifiers, one per packet
python scripts/build_ccc_verify_packets.py --packets 6
python scripts/build_ccc_verify_packets.py --check

# 6. Review, then import with the rest of the typology layer
python scripts/review_ccc_typology.py
python scripts/import_typology.py --reset && python scripts/import_memberships.py
python scripts/validate_import.py
```

Rules the pass enforces:
- Every quote must be a verbatim substring of its paragraph (checked by script).
- Each candidate carries a relation label: `explicit`, `preparatory`, `synthesized` (imported after review),
  or `prophecy` / `nt-figure` (held; see `dev/BACKLOG.md`).
- Imported link notes are the Catechism's own words (`CCC 1541: "…"`), never AI text.
- Type changes are an overlay (`data/reviewed/type_changes.jsonl`). Renames keep the Type id, and merges
  become an alias map applied at parse time, so the source files stay untouched.

Result (2026-10-23): 220 Types, 309 PREFIGURES (88 with Catechism support), 312 TEACHES.

## Tips

### Recognizing True Typology

**Is typology:**
- "Noah's Ark prefigures the Church"
- "The crossing of the Red Sea is a type of Baptism"
- "Melchizedek foreshadows Christ's priesthood"

**Is NOT typology:**
- General symbolism without OT→NT connection
- Moral lessons or allegory
- Historical commentary without typological claim

### Category Guidelines

| Category | Look for... |
|----------|-------------|
| Sacramental | Water, washing, bread, wine, oil |
| Christological | Persons/events pointing to Jesus |
| Ecclesial | Community, ark, temple, city |
| Marian | Women, mother figures, ark |
| Eschatological | Heaven, judgment, promised land |
| Covenantal | Promises, oaths, agreements |

### Handling Edge Cases

**Multiple types in one commentary:**
The LLM may extract multiple type/antitype pairs. Review each separately.

**Unclear antitype:**
If the OT type is clear but NT fulfillment isn't explicit, you can:
- Reject if too speculative
- Create a generic antitype (e.g., `christ`)
- Add notes explaining the connection

**Duplicate types:**
If the LLM suggests a name like "The Flood" but `noahs-flood` already exists, select the existing type to avoid duplicates.
