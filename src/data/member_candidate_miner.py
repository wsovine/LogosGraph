"""Mine MEMBER_OF candidate verses from the cross-reference layer.

A verse becomes a candidate member of a Type when it is cross-referenced by
multiple existing member verses of that Type (corroboration). Hub verses with
very high cross-reference degree are excluded, since they connect to
everything and carry little type-specific signal.

Candidates are structural signals only -- they must pass LLM adjudication
(src/review/member_adjudicator.py) and human review before import.
"""

import logging

from src.db.connection import Neo4jConnection, get_connection

logger = logging.getLogger(__name__)

# Conservative defaults; see scripts/mine_member_candidates.py for rationale
DEFAULT_MIN_CORROBORATION = 2
DEFAULT_MAX_DEGREE = 150
DEFAULT_PER_TYPE_CAP = 40
MAX_CORROBORATING_SAMPLES = 5

MINE_QUERY = """
    MATCH (m:Verse)-[:MEMBER_OF]->(t:Type)
    MATCH (m)-[:CROSS_REFERENCES]-(cand:Verse)
    WHERE NOT (cand)-[:MEMBER_OF]->(t)
    WITH t, cand, collect(DISTINCT m) AS members
    WHERE size(members) >= $min_corroboration
    WITH t, cand, members, COUNT { (cand)-[:CROSS_REFERENCES]-() } AS cand_degree
    WHERE cand_degree <= $max_degree
    RETURN t.id AS type_id,
           t.name AS type_name,
           t.testament AS type_testament,
           t.description AS type_description,
           cand.id AS verse_id,
           cand.text AS verse_text,
           cand.book_name AS book_name,
           cand.chapter AS chapter,
           cand.verse AS verse,
           size(members) AS corroboration,
           [x IN members[..$max_samples] | {id: x.id, text: x.text}]
               AS corroborating_verses,
           cand_degree AS candidate_degree
    ORDER BY t.id, corroboration DESC, cand_degree ASC
"""


def mine_candidates(
    connection: Neo4jConnection | None = None,
    min_corroboration: int = DEFAULT_MIN_CORROBORATION,
    max_degree: int = DEFAULT_MAX_DEGREE,
    per_type_cap: int | None = DEFAULT_PER_TYPE_CAP,
) -> list[dict]:
    """Mine candidate (verse, type) memberships from cross-references.

    Args:
        connection: Neo4j connection. Defaults to singleton connection.
        min_corroboration: Minimum number of distinct existing member verses
            that must cross-reference the candidate.
        max_degree: Exclude candidate verses with more total cross-references
            than this (hub-verse filter).
        per_type_cap: Keep at most this many candidates per type, ranked by
            corroboration. None disables the cap.

    Returns:
        List of candidate dicts ready for JSONL serialization, ordered by
        type then descending corroboration.
    """
    if connection is None:
        connection = get_connection()

    logger.info(
        "Mining candidates (min_corroboration=%d, max_degree=%d, per_type_cap=%s)",
        min_corroboration, max_degree, per_type_cap,
    )

    with connection.session() as session:
        result = session.run(
            MINE_QUERY,
            min_corroboration=min_corroboration,
            max_degree=max_degree,
            max_samples=MAX_CORROBORATING_SAMPLES,
        )
        rows = [dict(record) for record in result]

    if per_type_cap is not None:
        capped: list[dict] = []
        kept_for_type = 0
        current_type = None
        dropped = 0
        for row in rows:  # rows arrive ordered by type, corroboration DESC
            if row["type_id"] != current_type:
                current_type = row["type_id"]
                kept_for_type = 0
            if kept_for_type < per_type_cap:
                capped.append(row)
                kept_for_type += 1
            else:
                dropped += 1
        if dropped:
            logger.info("Per-type cap dropped %d candidates", dropped)
        rows = capped

    logger.info("Mined %d candidates across %d types",
                len(rows), len({r["type_id"] for r in rows}))
    return rows
