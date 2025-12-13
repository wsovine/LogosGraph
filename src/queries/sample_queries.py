"""Sample Cypher queries for exploring the Bible graph."""

# Most referenced verses (incoming edges)
MOST_REFERENCED = """
MATCH (v:Verse)<-[r:CROSS_REFERENCES]-()
WITH v, count(r) AS refs
ORDER BY refs DESC
LIMIT $limit
RETURN v.id AS verse_id, v.book_name AS book, v.text AS text, refs
"""

# Most referencing verses (outgoing edges)
MOST_REFERENCING = """
MATCH (v:Verse)-[r:CROSS_REFERENCES]->()
WITH v, count(r) AS refs
ORDER BY refs DESC
LIMIT $limit
RETURN v.id AS verse_id, v.book_name AS book, v.text AS text, refs
"""

# Find shortest path between two verses
SHORTEST_PATH = """
MATCH path = shortestPath(
    (a:Verse {id: $from_id})-[:CROSS_REFERENCES*]-(b:Verse {id: $to_id})
)
RETURN [n IN nodes(path) | n.id] AS path, length(path) AS hops
"""

# Get all cross-references for a verse
VERSE_CROSSREFS = """
MATCH (v:Verse {id: $verse_id})-[r:CROSS_REFERENCES]->(target:Verse)
RETURN target.id AS target_id, target.book_name AS book,
       target.text AS text, r.votes AS votes, r.passage_group AS passage_group
ORDER BY r.votes DESC
"""

# Get cross-references pointing to a verse
VERSE_REFERENCED_BY = """
MATCH (source:Verse)-[r:CROSS_REFERENCES]->(v:Verse {id: $verse_id})
RETURN source.id AS source_id, source.book_name AS book,
       source.text AS text, r.votes AS votes
ORDER BY r.votes DESC
"""

# Chapter cross-references
CHAPTER_CROSSREFS = """
MATCH (v:Verse {book_id: $book_id, chapter: $chapter})-[r:CROSS_REFERENCES]->(target:Verse)
WHERE target.book_id <> $book_id OR target.chapter <> $chapter
RETURN DISTINCT target.book_id AS target_book, target.chapter AS target_chapter,
       count(r) AS connections
ORDER BY connections DESC
LIMIT $limit
"""

# Book interconnections
BOOK_INTERCONNECTIONS = """
MATCH (a:Verse)-[r:CROSS_REFERENCES]->(b:Verse)
WHERE a.book_id <> b.book_id
RETURN a.book_id AS from_book, b.book_id AS to_book, count(r) AS connections
ORDER BY connections DESC
LIMIT $limit
"""

# Find all verses in a passage group
PASSAGE_GROUP_VERSES = """
MATCH (source:Verse {id: $source_id})-[r:CROSS_REFERENCES]->(target:Verse)
WHERE r.passage_group IS NOT NULL
WITH DISTINCT r.passage_group AS pg, source
MATCH (source)-[r2:CROSS_REFERENCES]->(related:Verse)
WHERE r2.passage_group = pg
RETURN pg AS passage_group,
       collect(DISTINCT related.id) AS grouped_verses,
       collect(DISTINCT related.text) AS texts
"""

# Verses with highest vote confidence
HIGH_CONFIDENCE_REFS = """
MATCH (a:Verse)-[r:CROSS_REFERENCES]->(b:Verse)
WHERE r.votes >= $min_votes
RETURN a.id AS from_verse, b.id AS to_verse,
       a.text AS from_text, b.text AS to_text, r.votes AS votes
ORDER BY r.votes DESC
LIMIT $limit
"""

# Book statistics
BOOK_STATS = """
MATCH (v:Verse)
WITH v.book_id AS book, v.book_name AS name, count(v) AS verses
OPTIONAL MATCH (v2:Verse {book_id: book})-[r:CROSS_REFERENCES]->()
WITH book, name, verses, count(r) AS outgoing
OPTIONAL MATCH ()-[r2:CROSS_REFERENCES]->(v3:Verse {book_id: book})
RETURN book, name, verses, outgoing, count(r2) AS incoming
ORDER BY book
"""


def run_query(session, query: str, **params):
    """Execute a query and return results as list of dicts."""
    result = session.run(query, **params)
    return [dict(record) for record in result]