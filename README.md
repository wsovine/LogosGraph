# LogosGraph

A Neo4j graph database for exploring Scripture through cross-reference connections.

## What This Is

LogosGraph contains the complete 73-book Catholic Bible as an interconnected graph:

| Metric | Value |
|--------|-------|
| Verses | 35,817 nodes |
| Cross-References | ~580,000 edges |
| Sources | TSK + Haydock Commentary |
| Books | 73 (complete Catholic canon) |

Built for exploring thematic connections between Scripture passages using graph traversal, path finding, and network analysis.

## Quick Start

```bash
# 1. Start Neo4j
docker compose up -d

# 2. Install dependencies
uv sync --extra notebooks

# 3. Import data (downloads, parses, and populates graph)
python scripts/import_all.py

# 4. Validate
python scripts/validate_import.py

# 5. Explore
# Browser: http://localhost:7474
# Notebook: jupyter notebook notebooks/
```

## Documentation

Full documentation in [docs/](docs/README.md):

- [CLI Reference](docs/cli-reference.md) - All scripts and options
- [Graph Schema](docs/graph-schema.md) - Neo4j schema and sample queries
- [Data Sources](docs/data-sources.md) - TSK, Haydock, CPDV, and CCC details
- [Theological Concepts](docs/theological-concepts.md) - Cross-references, typology, Catholic canon
- [Typology Workflow](docs/typology-workflow.md) - Extraction and review guide
- [Architecture](docs/architecture.md) - Project design

## Roadmap

- **Phase 3/4 (Complete)**: Catechism of the Catholic Church integration (2,865 paragraphs, Scripture citations, external documents)
- **Typology (In Progress)**: OT type → NT antitype connections from CCC and Haydock
- **Future**: Patristic sources, original language cross-references

## License & Credits

- **CPDV Bible Text**: Public domain
- **TSK Cross-References**: CC Attribution (OpenBible.info)
- **Haydock Commentary**: Public domain (1883 edition)
- **CCC**: Vatican standard usage terms

See [docs/provenance.md](docs/provenance.md) for why these sources were chosen and how they work together.

---

*LogosGraph uses the 73-book Catholic Bible to be inclusive of all Christians who recognize the deuterocanonical books.*
