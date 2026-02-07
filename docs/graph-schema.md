# Graph Schema

Neo4j schema and sample queries for LogosGraph.

## Node Types

### Verse

```cypher
(:Verse {
  id: "GEN-1-1",
  book_id: "GEN",
  book_name: "Genesis",
  chapter: 1,
  verse: 1,
  text: "In the beginning..."
})
```

### Book

```cypher
(:Book:Writing {
  id: "GEN",
  name: "Genesis",
  testament: "OT",
  ...dates...
})
```

### CatechismParagraph

```cypher
(:CatechismParagraph {
  id: "CCC-1",
  paragraph: 1,
  text: "...",
  section: "..."
})
```

### Type

```cypher
(:Type {
  id: "type-noahs-flood",
  name: "Noah's Flood",
  testament: "OT",
  description: "...",
  source: "CCC",
  confidence: "high",
  reviewed: true
})
```

## Relationships

### CROSS_REFERENCES

```cypher
[:CROSS_REFERENCES {
  sources: ["TSK", "Haydock"],  # One or both sources
  votes: 85,                     # TSK only (null for Haydock-only edges)
  passage_group: "uuid"          # Groups edges from verse ranges
}]
```

- `sources`: Array of sources attesting this connection. Edges may have `["TSK"]`, `["Haydock"]`, or both.
- `votes`: TSK crowdsourced quality score (only present when TSK is a source)
- `passage_group`: UUID linking edges from a single range reference (e.g., "Prov 8:22-30")

### PREFIGURES

Connects OT types to their NT antitypes (typological relationships).

```cypher
[:PREFIGURES {
  category: "Sacramental",    # Typology category
  confidence: "high",         # high, medium, or low
  source: "CCC-1094",         # Source reference (CCC paragraph or "haydock")
  description: "...",         # Authoritative description (from CCC)
  logosgraph_notes: "..."     # Reviewer notes from LogosGraph review process
}]
```

- `category`: One of Sacramental, Christological, Ecclesial, Marian, Eschatological, Covenantal
- `confidence`: Confidence level in the connection
- `source`: Where this typology was identified (CCC paragraph number or "haydock")
- `description`: Authoritative explanation from the source (CCC text or paraphrase)
- `logosgraph_notes`: Notes added during LogosGraph review process (less authoritative)

### Other Relationships

```cypher
(:Verse)-[:NEXT]->(:Verse)                           # Sequential ordering
(:CatechismParagraph)-[:CITES]->(:Verse)             # Scripture citations
(:Verse)-[:MEMBER_OF]->(:Type)                       # Verse supports type
(:CatechismParagraph)-[:TEACHES]->(:Type)            # CCC teaches about type
```

## Constraints and Indexes

```cypher
CREATE CONSTRAINT verse_id IF NOT EXISTS FOR (v:Verse) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT book_id IF NOT EXISTS FOR (b:Book) REQUIRE b.id IS UNIQUE;
CREATE CONSTRAINT ccc_id IF NOT EXISTS FOR (c:CatechismParagraph) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT type_id IF NOT EXISTS FOR (t:Type) REQUIRE t.id IS UNIQUE;
```

## Sample Queries

### Most Referenced Verses

```cypher
MATCH (v:Verse)<-[r:CROSS_REFERENCES]-()
WITH v, count(r) AS refs
ORDER BY refs DESC LIMIT 20
RETURN v.id, v.book_name, refs
```

### Shortest Path Between Passages

```cypher
MATCH path = shortestPath(
  (a:Verse {id:'GEN-1-1'})-[:CROSS_REFERENCES*]-(b:Verse {id:'REV-22-21'})
)
RETURN [n IN nodes(path) | n.id] AS path, length(path) AS hops
```

### Book Interconnections

```cypher
MATCH (a:Verse)-[r:CROSS_REFERENCES]->(b:Verse)
WHERE a.book_id <> b.book_id
RETURN a.book_id AS from_book, b.book_id AS to_book, count(r) AS connections
ORDER BY connections DESC LIMIT 20
```

### PageRank (Most Important Verses)

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

### Catechism Citations for a Verse

```cypher
MATCH (ccc:CatechismParagraph)-[:CITES]->(v:Verse {id: 'JHN-3-16'})
RETURN ccc.paragraph, ccc.text
```

### What Prefigures Baptism?

```cypher
MATCH (ot:Type)-[:PREFIGURES]->(nt:Type {name: 'Baptism'})
RETURN ot.name, ot.description
```
