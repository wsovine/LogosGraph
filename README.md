# LogosGraph

A Neo4j graph database for exploring Scripture through cross-reference connections.

## What This Is

LogosGraph contains the complete 73-book Bible as an interconnected graph:

| Metric | Value |
|--------|-------|
| Verses | 35,817 nodes |
| Cross-References | ~580,000 edges |
| Sources | TSK + Haydock Commentary |
| Books | 73 (complete Catholic canon) |

Built for exploring thematic connections between Scripture passages using graph traversal, path finding, and network analysis.

## Current Contents (Phase 2)

- **Bible Text**: Catholic Public Domain Version (CPDV) - all 73 books including deuterocanonicals
- **Cross-References**:
  - Treasury of Scripture Knowledge (TSK) via OpenBible.info
  - Haydock Catholic Bible Commentary (1811-1859)
- **Graph Analytics**: Neo4j Graph Data Science plugin for PageRank, community detection, centrality measures
- **Exploration Tools**: Jupyter notebooks with pyvis visualization

## Quick Start

```bash
# 1. Start Neo4j
docker compose up -d

# 2. Install dependencies
uv sync --extra notebooks

# 3. Import data
python scripts/import_all.py

# 4. Validate
python scripts/validate_import.py

# 5. Explore
# Browser: http://localhost:7474
# Notebook: jupyter notebook notebooks/
```

## Graph Schema

**Verse Nodes:**
```
(:Verse {
  id: "GEN-1-1",
  book_id: "GEN",
  book_name: "Genesis",
  chapter: 1,
  verse: 1,
  text: "In the beginning..."
})
```

**Cross-Reference Edges:**
```
[:CROSS_REFERENCES {
  sources: ["TSK", "Haydock"],  # One or both sources
  votes: 85,                     # TSK only (null for Haydock-only edges)
  passage_group: "uuid"          # Groups edges from verse ranges
}]
```

- `sources`: Array of sources attesting this connection. Edges may have `["TSK"]`, `["Haydock"]`, or both.
- `votes`: TSK crowdsourced quality score (only present when TSK is a source)
- `passage_group`: UUID linking edges from a single range reference (e.g., "Prov 8:22-30")

## Sample Queries

**Most Referenced Verses:**
```cypher
MATCH (v:Verse)<-[r:CROSS_REFERENCES]-()
WITH v, count(r) AS refs
ORDER BY refs DESC LIMIT 20
RETURN v.id, v.book_name, refs
```

**Shortest Path Between Passages:**
```cypher
MATCH path = shortestPath(
  (a:Verse {id:'GEN-1-1'})-[:CROSS_REFERENCES*]-(b:Verse {id:'REV-22-21'})
)
RETURN [n IN nodes(path) | n.id] AS path, length(path) AS hops
```

**Book Interconnections:**
```cypher
MATCH (a:Verse)-[r:CROSS_REFERENCES]->(b:Verse)
WHERE a.book_id <> b.book_id
RETURN a.book_id AS from_book, b.book_id AS to_book, count(r) AS connections
ORDER BY connections DESC LIMIT 20
```

**PageRank (Most Important Verses):**
```cypher
CALL gds.graph.project('bible', 'Verse', 'CROSS_REFERENCES')
YIELD graphName;

CALL gds.pageRank.stream('bible')
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS verse, score
ORDER BY score DESC LIMIT 25
RETURN verse.id, verse.book_name, round(score, 4) AS pagerank;

CALL gds.graph.drop('bible');
```

## About TSK Cross-References

### History

The Treasury of Scripture Knowledge was compiled across generations:

- **William Canne** (17th century) - Created original marginal Bible references
- **Thomas Scott** - Expanded in his biblical commentary
- **R.A. Torrey** (late 19th century) - Compiled and significantly expanded into the Treasury of Scripture Knowledge

The original work contains over 500,000 cross-references linking Scripture passages.

### Methodology & Limitations

Understanding the limitations of TSK helps interpret the data appropriately:

**1. Protestant Canon Only**

TSK covers the 66 Protestant-canon books. The 7 deuterocanonical books (Tobit, Judith, Wisdom, Sirach, Baruch, 1-2 Maccabees) are not covered by TSK but are included via Haydock cross-references.

**2. English-Based Word Matching**

Many TSK connections are based on English word matching in the King James Version, not the original languages:

- The Greek word *agape* (unconditional love) and *phileo* (friendship love) both translate to English "love"
- Hebrew terms may be linked to unrelated Greek terms simply because English translators used the same word
- Connections that appear meaningful in English may have no basis in Greek or Hebrew

This is a fundamental methodological weakness. A word study that seems profound in English may evaporate when examining the source texts.

**3. Broad Hermeneutic**

The 19th-century approach emphasized finding any thematic or verbal parallel:

- Assumed the Bible forms a unified whole where virtually any parallel might illuminate meaning
- A shared word or concept was often sufficient to warrant a cross-reference
- Modern scholars would distinguish between:
  - **Direct quotations** (NT quoting OT)
  - **Clear allusions** (obvious intentional references)
  - **Thematic parallels** (similar concepts in different contexts)
  - **Verbal coincidences** (same English word, unrelated meaning)

TSK largely treats all of these as equivalent, which can obscure genuine connections.

**4. Devotional Purpose**

TSK was designed for preachers and Bible students seeking material for meditation and sermon preparation:

- Quantity had practical value even if not every reference was exegetically sound
- Some connections are tenuous—shared words used in completely different contexts
- Comprehensiveness served apologetic purposes by demonstrating the Bible's internal coherence

### Quality Signal

The `votes` field comes from OpenBible.info's crowdsourced voting system, providing some quality filtering:

- Higher votes indicate stronger community confidence in a connection
- However, even high-voted connections may still be based on English word matching
- Use votes as a rough heuristic, not a guarantee of scholarly validity

## About Haydock Cross-References

The Haydock Catholic Bible Commentary was compiled by George Leo Haydock between 1811-1859. It represents a comprehensive Catholic commentary on Scripture:

- **Complete Coverage**: All 73 books of the Catholic Bible, including deuterocanonicals
- **Patristic Sources**: Cross-references drawn from Church Fathers and Doctors of the Church
- **Catholic Perspective**: Grounded in Catholic theological tradition
- **Public Domain**: Original 1883 edition freely available

Unlike TSK's word-matching approach, Haydock's references often reflect theological and typological connections identified in the Catholic interpretive tradition.

Haydock edges do not have a `votes` property since they come from a single authoritative source rather than crowdsourced validation.

## Roadmap

### Phase 3: Catechism Citations
Integrate Scripture citations from the Catechism of the Catholic Church:
- Authoritative teaching document
- Curated, high-quality Scripture connections
- New edge type: `[:CITED_BY]`

### Phase 4: Patristic Sources
Expand to Church Fathers, Council documents, and papal encyclicals.

### Future Consideration: Original Language Sources
Cross-references grounded in Greek, Hebrew, and Aramaic would address TSK's core limitation. Sources that analyze connections based on the original texts rather than English translations would significantly improve reliability.

## Technical Details

| Component | Version |
|-----------|---------|
| Python | 3.12+ |
| Neo4j | 5.24-community |
| GDS Plugin | Enabled |

**Dependencies:**
```
neo4j>=5.0
requests>=2.28
python-dotenv>=1.0
tqdm>=4.65
usfm-grammar>=3.0
```

**Optional (notebooks):**
```
jupyter>=1.0
pandas>=2.0
pyvis>=0.3
```

## Project Structure

```
LogosGraph/
├── docker-compose.yml      # Neo4j container
├── pyproject.toml          # Dependencies
├── src/
│   ├── config.py           # Settings
│   ├── db/                 # Neo4j connection & schema
│   ├── data/               # Parsers & downloaders
│   ├── import_pipeline/    # Batch importers
│   └── queries/            # Sample queries & GDS analytics
├── scripts/
│   ├── import_all.py       # Run full import
│   └── validate_import.py  # Verify data
└── notebooks/              # Jupyter exploration
```

## License & Credits

- **CPDV Bible Text**: Public domain
- **TSK Cross-References**: CC Attribution (OpenBible.info)
- **Haydock Commentary**: Public domain (1883 edition)
- **This Project**: [Your license here]

---

*LogosGraph uses the original 73-book Bible to be inclusive of all Christians who recognize the deuterocanonical books.*
