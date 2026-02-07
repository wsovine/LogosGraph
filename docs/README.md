# LogosGraph Documentation

Detailed documentation for LogosGraph, a Neo4j knowledge graph of the Catholic Bible.

## Contents

| Document | Description |
|----------|-------------|
| [CLI Reference](cli-reference.md) | All scripts with options, examples, and output descriptions |
| [Graph Schema](graph-schema.md) | Neo4j node/relationship schemas and sample Cypher queries |
| [Data Sources](data-sources.md) | Technical details on TSK, Haydock, CPDV, and CCC |
| [Data Provenance](provenance.md) | Why sources were chosen and how they complement each other |
| [Theological Concepts](theological-concepts.md) | Cross-references, typology, Catholic canon, Magisterial interpretation |
| [Data Formats](data-formats.md) | JSON/JSONL file schemas for seed and extracted data |
| [Typology Workflow](typology-workflow.md) | End-to-end guide for typology extraction and review |
| [Architecture](architecture.md) | Project structure, design decisions, and data flow |

## Quick Links

### Getting Started

1. See [README.md](../README.md) for installation and quick start
2. Run `python scripts/import_all.py` to populate the database
3. Explore with Neo4j Browser at http://localhost:7474

### Common Tasks

| Task | Command |
|------|---------|
| Full import | `python scripts/import_all.py` |
| Validate data | `python scripts/validate_import.py` |
| Extract typology | `python scripts/extract_typology_llm.py` |
| Review typology | `python scripts/review_typology.py` |

See [CLI Reference](cli-reference.md) for all options.

### Understanding the Data

- **Graph structure**: [Graph Schema](graph-schema.md)
- **Cross-reference quality**: [Data Sources](data-sources.md)
- **File formats**: [Data Formats](data-formats.md)

### Working with Typology

The typology pipeline extracts OT type → NT antitype connections:

1. Extract Haydock footers (`extract_haydock_footers.py`)
2. Process through LLM (`extract_typology_llm.py`)
3. Human review (`review_typology.py`)
4. Import to Neo4j

Full details in [Typology Workflow](typology-workflow.md).

## Project Structure

```
LogosGraph/
├── scripts/              # CLI entry points
├── src/
│   ├── config.py         # Environment settings
│   ├── data/             # Parsers and extractors
│   ├── db/               # Neo4j schema
│   ├── import_pipeline/  # Database import
│   └── review/           # Review workflow
├── data/
│   ├── raw/              # Source files
│   ├── seed/             # Curated seed data
│   ├── extracted/        # LLM output
│   └── reviewed/         # Reviewed data
├── docs/                 # This documentation
└── notebooks/            # Jupyter exploration
```

See [Architecture](architecture.md) for design details.
