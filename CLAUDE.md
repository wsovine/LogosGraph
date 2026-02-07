# CLAUDE.md

AI context file for LogosGraph development sessions.

## Project Overview

LogosGraph is a Neo4j knowledge graph of the Catholic Bible with cross-references, Catechism connections, and biblical typology.

| Metric | Value |
|--------|-------|
| Verses | 35,817 nodes |
| Cross-References | ~580,000 edges |
| Sources | TSK + Haydock Commentary |
| Books | 73 (complete Catholic canon) |

## Repository Structure

```
LogosGraph/
├── scripts/              # CLI entry points
├── src/
│   ├── config.py         # Environment settings
│   ├── data/             # Parsers and extractors
│   ├── db/               # Neo4j schema and utilities
│   ├── import_pipeline/  # Database import functions
│   └── review/           # Review workflow tools
├── data/
│   ├── raw/              # Source files (Haydock USFM, etc.)
│   ├── seed/             # Curated seed data (CCC types)
│   ├── extracted/        # LLM extraction output
│   └── reviewed/         # Human-reviewed data
├── docs/                 # User documentation
├── notebooks/            # Jupyter exploration
└── docker-compose.yml    # Neo4j container
```

## Documentation Map

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Quick start and project overview |
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/cli-reference.md](docs/cli-reference.md) | All scripts and options |
| [docs/data-formats.md](docs/data-formats.md) | JSON/JSONL schemas |
| [docs/graph-schema.md](docs/graph-schema.md) | Neo4j schema and sample queries |
| [docs/data-sources.md](docs/data-sources.md) | TSK and Haydock background |
| [docs/typology-workflow.md](docs/typology-workflow.md) | Typology extraction guide |
| [docs/architecture.md](docs/architecture.md) | Design decisions |

## Key Technical Details

- **Database**: Neo4j 5.24-community with GDS plugin
- **Python**: 3.12+ with uv for dependency management
- **Neo4j URI**: `bolt://localhost:7687` (default)
- **Data paths**: `data/raw/`, `data/extracted/`, `data/reviewed/`

## Common Tasks

```bash
# Start Neo4j
docker compose up -d

# Full import pipeline
python scripts/import_all.py

# Validate import
python scripts/validate_import.py

# Run typology extraction (requires ANTHROPIC_API_KEY)
python scripts/extract_typology_llm.py

# Interactive typology review
python scripts/review_typology.py
```

See [docs/cli-reference.md](docs/cli-reference.md) for all options.

## Important Reminders

### At Session Start

- Check `git status` to understand current work
- Review open tasks in dev/ if present
- Confirm Neo4j is running if database work needed

### During Development

- Use existing parsers in `src/data/` for new data sources
- Follow JSONL format for extraction outputs (append-friendly)
- Validate schemas with `src/data/typology_schemas.py`
- Test parsers with `python -m src.data.<module>`

### Before Committing

- Run `python scripts/validate_import.py` if database changed
- Check for uncommitted data files (they're gitignored)
- Update docs if CLI options changed

## Documentation Guidelines

This project uses **hub-and-spoke documentation**:

- **README.md**: High-level overview, quick start, pointers to docs/
- **CLAUDE.md**: This file - slim AI context for agent sessions
- **docs/**: Detailed documentation by topic

When adding documentation:
- Keep README.md scannable (< 100 lines)
- Put detailed content in topic-specific docs/*.md files
- Update docs/README.md index when adding new docs
