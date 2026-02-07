# Architecture

## Project Structure

```
logosgraph/
├── scripts/                    # CLI entry points
│   ├── extract_haydock_footers.py
│   ├── extract_typology_llm.py
│   ├── review_typology.py
│   ├── import_all.py
│   └── validate_import.py
│
├── src/
│   ├── config.py               # Environment settings
│   │
│   ├── data/                   # Data parsing and extraction
│   │   ├── book_mapping.py     # Verse ID utilities
│   │   ├── haydock_parser.py   # Haydock cross-ref parser
│   │   ├── haydock_footer_parser.py  # Footer extraction
│   │   ├── typology_extractor.py     # LLM extraction
│   │   ├── typology_schemas.py       # Validation schemas
│   │   ├── catechism_parser.py       # CCC parser
│   │   └── catechism_citation_parser.py
│   │
│   ├── db/                     # Database layer
│   │   └── schema.py           # Neo4j constraints and indexes
│   │
│   ├── import_pipeline/        # Data import functions
│   │   ├── runner.py           # Import orchestration
│   │   ├── verse_importer.py
│   │   ├── crossref_importer.py
│   │   ├── catechism_importer.py
│   │   └── typology_importer.py  # (Phase 4)
│   │
│   └── review/                 # Review workflow
│       └── typology_reviewer.py
│
├── data/
│   ├── raw/                    # Source files
│   │   └── haydock/            # Haydock USFM files
│   │
│   ├── seed/                   # Curated seed data
│   │   ├── ccc_types.json
│   │   ├── ccc_prefigures.json
│   │   ├── ccc_verse_memberships.json
│   │   └── ccc_teaches.json
│   │
│   ├── extracted/              # Extraction output
│   │   ├── haydock_footers.jsonl
│   │   ├── haydock_typology_candidates.jsonl
│   │   └── haydock_typology_raw.jsonl
│   │
│   └── reviewed/               # Review output
│       ├── typology_approved.jsonl
│       ├── typology_rejected.jsonl
│       └── new_types.jsonl
│
├── docs/                       # User documentation
├── dev/                        # Development docs
└── notebooks/                  # Jupyter notebooks
```

## Design Decisions

### Type Nodes vs Relationships

**Decision:** Use separate Type nodes connected by PREFIGURES relationships.

**Alternative considered:** Direct verse-to-verse TYPIFIES edges.

**Rationale:**
- Types are first-class concepts (Noah's Flood, Baptism)
- Multiple verses can support the same type (MEMBER_OF)
- CCC teaches about types, not individual verses (TEACHES)
- Cleaner queries for "what prefigures Baptism?"

### Category on Relationships

**Decision:** Category lives on PREFIGURES relationship, not Type node.

**Rationale:**
- Same type can participate in different categorical relationships
- Example: Noah's Ark is Sacramental (→ Baptism) AND Ecclesial (→ Church)
- More flexible for complex typological connections

### Hybrid Type Vocabulary

**Decision:** Reviewer can select existing types OR create new ones.

**Alternatives considered:**
1. Closed vocabulary (LLM maps to fixed list)
2. Open vocabulary (normalize duplicates later)

**Rationale:**
- Closed vocabulary might miss novel types
- Open vocabulary creates duplicate management burden
- Hybrid gives human control while leveraging existing types

### JSONL for Extraction Output

**Decision:** Use JSON Lines (.jsonl) for extraction and review files.

**Rationale:**
- Append-friendly (no need to rewrite entire file)
- Streaming-compatible (process line by line)
- Easy checkpoint/resume
- Human-readable

### Seed Data in JSON

**Decision:** Use JSON for curated seed data.

**Rationale:**
- Schema validation friendly
- Version control friendly (readable diffs)
- Small enough to load entirely
- Clear structure with arrays

## Graph Schema

### Nodes

```cypher
(:Verse {id, book, chapter, verse, text})
(:Book:Writing {id, name, testament, ...dates...})
(:CatechismParagraph {id, paragraph, text, section, ...})
(:Type {id, name, testament, description, source, confidence, reviewed})
```

### Relationships

```cypher
(:Verse)-[:NEXT]->(:Verse)
(:Verse)-[:CROSS_REFS {source}]->(:Verse)
(:CatechismParagraph)-[:CITES]->(:Verse)
(:Type)-[:PREFIGURES {category, confidence, source, verse_id}]->(:Type)
(:Verse)-[:MEMBER_OF]->(:Type)
(:CatechismParagraph)-[:TEACHES]->(:Type)
```

### Indexes and Constraints

```cypher
CREATE CONSTRAINT verse_id IF NOT EXISTS FOR (v:Verse) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT book_id IF NOT EXISTS FOR (b:Book) REQUIRE b.id IS UNIQUE;
CREATE CONSTRAINT ccc_id IF NOT EXISTS FOR (c:CatechismParagraph) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT type_id IF NOT EXISTS FOR (t:Type) REQUIRE t.id IS UNIQUE;
```

## Data Flow

### Extraction Pipeline

```
Haydock USFM → Footer Parser → JSONL
                    ↓
            Keyword Filter → Candidates JSONL
                    ↓
            LLM Extractor → Raw Extractions JSONL
                    ↓
            Human Review → Approved/Rejected JSONL
                    ↓
            Import → Neo4j
```

### Import Pipeline

```
Seed Data (JSON) ─────────────┐
                              ├──→ Type Nodes
Approved Extractions (JSONL) ─┘
         │
         ├──→ PREFIGURES edges (with category)
         ├──→ MEMBER_OF edges (verse → type)
         └──→ TEACHES edges (CCC → type)
```

## Error Handling

### LLM Extraction

- Rate limiting with configurable RPM
- Automatic retry on transient API errors
- JSON validation of responses
- Checkpoint save after each batch
- Resume from checkpoint on restart

### Review Session

- Progress saved after each decision
- Graceful Ctrl+C handling
- Resume from last position

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | For LLM | - | Claude API key |
| `NEO4J_URI` | For import | `bolt://localhost:7687` | Database URI |
| `NEO4J_USER` | For import | `neo4j` | Database user |
| `NEO4J_PASSWORD` | For import | `logosgraph` | Database password |
| `BATCH_SIZE` | No | `5000` | Import batch size |

### File Paths

Configured in `src/config.py`:

```python
DATA_DIR = PROJECT_ROOT / "data" / "raw"
HAYDOCK_DIR = DATA_DIR / "haydock"
```

Default extraction/review paths in scripts:
- `data/extracted/` for extraction output
- `data/reviewed/` for review output
