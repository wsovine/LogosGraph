"""Graph Data Science (GDS) analytics queries."""

# Create a graph projection for analytics
CREATE_PROJECTION = """
CALL gds.graph.project(
    $graph_name,
    'Verse',
    'CROSS_REFERENCES'
)
YIELD graphName, nodeCount, relationshipCount
RETURN graphName, nodeCount, relationshipCount
"""

# Drop a graph projection
DROP_PROJECTION = """
CALL gds.graph.drop($graph_name, false)
YIELD graphName
RETURN graphName
"""

# Check if projection exists
PROJECTION_EXISTS = """
CALL gds.graph.exists($graph_name)
YIELD exists
RETURN exists
"""

# PageRank - find most important verses
PAGERANK = """
CALL gds.pageRank.stream($graph_name)
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS verse, score
ORDER BY score DESC
LIMIT $limit
RETURN verse.id AS verse_id, verse.book_name AS book,
       verse.text AS text, round(score, 4) AS pagerank
"""

# Degree centrality - most connected verses
DEGREE_CENTRALITY = """
CALL gds.degree.stream($graph_name)
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS verse, score
ORDER BY score DESC
LIMIT $limit
RETURN verse.id AS verse_id, verse.book_name AS book,
       verse.text AS text, toInteger(score) AS degree
"""

# Betweenness centrality - bridge verses
BETWEENNESS_CENTRALITY = """
CALL gds.betweenness.stream($graph_name)
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS verse, score
WHERE score > 0
ORDER BY score DESC
LIMIT $limit
RETURN verse.id AS verse_id, verse.book_name AS book,
       verse.text AS text, round(score, 2) AS betweenness
"""

# Louvain community detection
COMMUNITY_DETECTION = """
CALL gds.louvain.stream($graph_name)
YIELD nodeId, communityId
WITH communityId, collect(gds.util.asNode(nodeId).id) AS members
RETURN communityId, size(members) AS size, members[0..5] AS sample_members
ORDER BY size DESC
LIMIT $limit
"""

# Weakly connected components
CONNECTED_COMPONENTS = """
CALL gds.wcc.stream($graph_name)
YIELD nodeId, componentId
WITH componentId, count(*) AS size
RETURN componentId, size
ORDER BY size DESC
LIMIT $limit
"""


class GDSAnalytics:
    """Helper class for running GDS analytics."""

    def __init__(self, session, graph_name: str = "bible-graph"):
        self.session = session
        self.graph_name = graph_name

    def create_projection(self) -> dict:
        """Create the graph projection."""
        result = self.session.run(CREATE_PROJECTION, graph_name=self.graph_name)
        return dict(result.single())

    def drop_projection(self) -> bool:
        """Drop the graph projection if it exists."""
        # Check if exists first
        result = self.session.run(PROJECTION_EXISTS, graph_name=self.graph_name)
        if result.single()["exists"]:
            self.session.run(DROP_PROJECTION, graph_name=self.graph_name)
            return True
        return False

    def pagerank(self, limit: int = 25) -> list[dict]:
        """Get top verses by PageRank."""
        result = self.session.run(PAGERANK, graph_name=self.graph_name, limit=limit)
        return [dict(r) for r in result]

    def degree_centrality(self, limit: int = 25) -> list[dict]:
        """Get top verses by degree centrality."""
        result = self.session.run(DEGREE_CENTRALITY, graph_name=self.graph_name, limit=limit)
        return [dict(r) for r in result]

    def betweenness(self, limit: int = 25) -> list[dict]:
        """Get top verses by betweenness centrality."""
        result = self.session.run(BETWEENNESS_CENTRALITY, graph_name=self.graph_name, limit=limit)
        return [dict(r) for r in result]

    def communities(self, limit: int = 20) -> list[dict]:
        """Detect communities using Louvain algorithm."""
        result = self.session.run(COMMUNITY_DETECTION, graph_name=self.graph_name, limit=limit)
        return [dict(r) for r in result]

    def components(self, limit: int = 10) -> list[dict]:
        """Find weakly connected components."""
        result = self.session.run(CONNECTED_COMPONENTS, graph_name=self.graph_name, limit=limit)
        return [dict(r) for r in result]