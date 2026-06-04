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

A typological concept from either testament — an OT "type" or its NT "antitype".

```cypher
(:Type {
  id: "noahs-flood",          # kebab-case slug (no prefix)
  name: "Noah's Flood",
  testament: "OT",            # "OT" or "NT"
  category: "Sacramental",    # seed types only; canonical category lives on PREFIGURES
  description: "...",         # may be null for review-created types
  source: "CCC-1094",         # "CCC-<n>", "haydock", "haydock-review", or "haydock-review-ai"
  confidence: "high",         # high, medium, low
  reviewed: true
})
```

- IDs are kebab-case slugs (`noahs-flood`, `melchizedek`, `christ-high-priest`).
- `category` is present on the 20 CCC seed types for convenience; the **authoritative** category for a
  typological connection lives on the `PREFIGURES` edge (review-created types have no node category).

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

Connects an OT type to its NT antitype (typological relationship). **One edge per type→antitype pair**:
when many sources attest the same connection, their provenance is accumulated into the `sources` and
`source_verses` arrays (the same convention as `CROSS_REFERENCES.sources`).

```cypher
[:PREFIGURES {
  category: "Christological",            # canonical typology category (may be null for CCC-seed-only edges)
  confidence: "high",                    # high, medium, or low
  sources: ["CCC-1094", "haydock"],      # every source attesting this connection
  source_verses: ["GEN-1-26", "..."],    # Haydock-commentary verses that attest it (may be empty)
  notes: "..."                           # description/reviewer note (first source's note)
}]
```

- `category`: One of Sacramental, Christological, Ecclesial, Marian, Eschatological, Covenantal. Null on the
  handful of edges sourced only from `ccc_prefigures.json` (which carries no category).
- `confidence`: Confidence level in the connection.
- `sources`: Array of attestations — CCC paragraph ids (`"CCC-1094"`) and/or `"haydock"`.
- `source_verses`: Array of verse ids whose Haydock commentary attests the connection (rich provenance;
  e.g. `david → christ` carries ~26 source_verses).
- `notes`: Authoritative description (CCC) or reviewer note (Haydock review).

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

CREATE INDEX type_category_idx IF NOT EXISTS FOR (t:Type) ON (t.category);
CREATE INDEX type_testament_idx IF NOT EXISTS FOR (t:Type) ON (t.testament);
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

### Typology Queries

Current graph (2026-06-03): 198 Type nodes (156 OT / 42 NT), 272 PREFIGURES, 555 MEMBER_OF, 33 TEACHES.

**What prefigures Baptism?** — OT types pointing at the `baptism` antitype (→ 17 results).

```cypher
MATCH (ot:Type)-[r:PREFIGURES]->(:Type {id: 'baptism'})
RETURN ot.name, r.category, r.sources
ORDER BY ot.name
```
> e.g. Circumcision, Crossing of the Jordan, Crossing of the Red Sea, Noah's Flood/Ark,
> God's Wonders by Water, The Pool of Siloam, The Mark of Tau, Levitical Purifications, …

**Which Types does a verse support?** — follow MEMBER_OF up from a verse.

```cypher
MATCH (:Verse {id: 'GEN-7-11'})-[:MEMBER_OF]->(t:Type)
RETURN t.id, t.name, t.testament
```
> → `noahs-flood` (Noah's Flood, OT)

**What Types does a Catechism paragraph teach?**

```cypher
MATCH (:CatechismParagraph {id: 'CCC-1094'})-[:TEACHES]->(t:Type)
RETURN t.id, t.testament ORDER BY t.testament, t.id
```
> → 9 types: noahs-flood, noahs-ark, red-sea-crossing, cloud-in-desert, water-from-rock, manna (OT);
> baptism, eucharist, spiritual-gifts-of-christ (NT)

**Full chain: OT verse → OT type → NT antitype → NT verse.**

```cypher
MATCH (ov:Verse)-[:MEMBER_OF]->(ot:Type {id: 'manna'})-[:PREFIGURES]->(nt:Type)
OPTIONAL MATCH (nv:Verse)-[:MEMBER_OF]->(nt)
RETURN ot.name, nt.name, collect(DISTINCT ov.id)[..3] AS ot_verses,
       collect(DISTINCT nv.id)[..3] AS nt_verses
```
> e.g. Manna → Eucharist (`EXO-16-4`, `JHN-6-31`, …)

**Best-attested typologies** — PREFIGURES edges ranked by how many Haydock verses attest them.

```cypher
MATCH (a:Type)-[r:PREFIGURES]->(b:Type)
RETURN a.name, b.name, r.category, size(r.source_verses) AS verses
ORDER BY verses DESC LIMIT 10
```
> Top: David → Christ (26), The Temple of Jerusalem → The One True Church (11),
> Old Testament Priesthood → Christ the High Priest (10), Moses → Christ (9), Solomon → Christ (9)
