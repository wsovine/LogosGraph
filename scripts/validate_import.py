#!/usr/bin/env python3
"""Validate the Bible graph database import."""

import sys

from src.db.connection import get_connection

# Expected values
EXPECTED_VERSE_COUNT = 31000  # Approximate
EXPECTED_BOOK_COUNT = 73
EXPECTED_CROSSREF_COUNT = 340000  # Approximate minimum
DEUTEROCANONICAL_BOOKS = ["TOB", "JDT", "WIS", "SIR", "BAR", "1MA", "2MA"]

# CCC expected values
EXPECTED_CCC_PARAGRAPHS = 2800  # Approximate minimum (~2,865 actual)
EXPECTED_CCC_INTERNAL_REFS = 3500  # Approximate minimum (~3,713 actual)
EXPECTED_CCC_SCRIPTURE_REFS = 1900  # Approximate minimum (~2,006 actual)
EXPECTED_EXTERNAL_DOCS = 350  # Approximate minimum (~390 actual)
EXPECTED_CCC_EXTERNAL_REFS = 500  # Approximate minimum (~556 actual)

# Typology expected values (full seed + reviewed import; ~198 types)
EXPECTED_TYPE_COUNT = 150  # Approximate minimum (~198 actual)
EXPECTED_PREFIGURES = 250  # Approximate minimum (~272 actual)
EXPECTED_BAPTISM_TYPES = 5  # OT types prefiguring Baptism (~17 actual)
EXPECTED_CCC1094_TYPES = 9  # Types taught by CCC-1094 (9 actual)


def check(name: str, passed: bool, details: str = "") -> bool:
    """Print check result and return pass/fail."""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"  {status}: {name}")
    if details:
        print(f"         {details}")
    return passed


def main():
    print("\n" + "=" * 60)
    print("LogosGraph Import Validation")
    print("=" * 60 + "\n")

    connection = get_connection()
    connection.connect()

    all_passed = True

    with connection.session() as session:
        # Check 1: Total verse count
        result = session.run("MATCH (v:Verse) RETURN count(v) AS count")
        verse_count = result.single()["count"]
        passed = verse_count >= EXPECTED_VERSE_COUNT
        all_passed &= check(
            "Verse count",
            passed,
            f"Found {verse_count:,} verses (expected >= {EXPECTED_VERSE_COUNT:,})"
        )

        # Check 2: Book count
        result = session.run("MATCH (v:Verse) RETURN count(DISTINCT v.book_id) AS count")
        book_count = result.single()["count"]
        passed = book_count == EXPECTED_BOOK_COUNT
        all_passed &= check(
            "Book count",
            passed,
            f"Found {book_count} books (expected {EXPECTED_BOOK_COUNT})"
        )

        # Check 3: Deuterocanonical books present
        result = session.run("""
            MATCH (v:Verse)
            WHERE v.book_id IN $books
            RETURN DISTINCT v.book_id AS book
        """, books=DEUTEROCANONICAL_BOOKS)
        found_books = [r["book"] for r in result]
        missing_books = set(DEUTEROCANONICAL_BOOKS) - set(found_books)
        passed = len(missing_books) == 0
        all_passed &= check(
            "Deuterocanonical books",
            passed,
            f"Found: {sorted(found_books)}" + (f", Missing: {sorted(missing_books)}" if missing_books else "")
        )

        # Check 4: Cross-reference count
        result = session.run("MATCH ()-[r:CROSS_REFERENCES]->() RETURN count(r) AS count")
        crossref_count = result.single()["count"]
        passed = crossref_count >= EXPECTED_CROSSREF_COUNT
        all_passed &= check(
            "Cross-reference count",
            passed,
            f"Found {crossref_count:,} edges (expected >= {EXPECTED_CROSSREF_COUNT:,})"
        )

        # Check 5: Genesis 1:1 has edges
        result = session.run("""
            MATCH (v:Verse {id: 'GEN-1-1'})-[r:CROSS_REFERENCES]-()
            RETURN count(r) AS count
        """)
        gen_edges = result.single()["count"]
        passed = gen_edges >= 10
        all_passed &= check(
            "Genesis 1:1 connectivity",
            passed,
            f"Found {gen_edges} edges (expected >= 10)"
        )

        # Check 6: John 3:16 has edges
        result = session.run("""
            MATCH (v:Verse {id: 'JHN-3-16'})-[r:CROSS_REFERENCES]-()
            RETURN count(r) AS count
        """)
        jhn_edges = result.single()["count"]
        passed = jhn_edges >= 1
        all_passed &= check(
            "John 3:16 connectivity",
            passed,
            f"Found {jhn_edges} edges"
        )

        # Check 7: Sources array exists on edges
        result = session.run("""
            MATCH ()-[r:CROSS_REFERENCES]->()
            WHERE r.sources IS NOT NULL
            RETURN count(r) AS count
            LIMIT 1
        """)
        has_sources = result.single()["count"] > 0
        all_passed &= check(
            "Edge sources property",
            has_sources,
            "sources array present on edges"
        )

        # Check 8: Passage groups exist
        result = session.run("""
            MATCH ()-[r:CROSS_REFERENCES]->()
            WHERE r.passage_group IS NOT NULL
            RETURN count(DISTINCT r.passage_group) AS count
        """)
        passage_groups = result.single()["count"]
        passed = passage_groups > 0
        all_passed &= check(
            "Passage groups",
            passed,
            f"Found {passage_groups:,} distinct passage groups"
        )

        # Check 9: Haydock source exists
        result = session.run("""
            MATCH ()-[r:CROSS_REFERENCES]->()
            WHERE "Haydock" IN r.sources
            RETURN count(r) AS count
        """)
        haydock_count = result.single()["count"]
        passed = haydock_count > 0
        all_passed &= check(
            "Haydock cross-references",
            passed,
            f"Found {haydock_count:,} Haydock edges"
        )

        # Check 10: Deuterocanonical books have edges
        result = session.run("""
            MATCH (v:Verse)-[r:CROSS_REFERENCES]-()
            WHERE v.book_id IN $books
            RETURN count(r) AS count
        """, books=DEUTEROCANONICAL_BOOKS)
        deut_edges = result.single()["count"]
        passed = deut_edges > 0
        all_passed &= check(
            "Deuterocanonical connectivity",
            passed,
            f"Found {deut_edges:,} edges involving deuterocanonical books"
        )

        # Check 11: Multi-source edges exist
        result = session.run("""
            MATCH ()-[r:CROSS_REFERENCES]->()
            WHERE size(r.sources) > 1
            RETURN count(r) AS count
        """)
        multi_source = result.single()["count"]
        passed = multi_source > 0
        all_passed &= check(
            "Multi-source edges",
            passed,
            f"Found {multi_source:,} edges with multiple sources"
        )

        # Print source distribution
        print("\n  Source distribution:")
        result = session.run("""
            MATCH ()-[r:CROSS_REFERENCES]->()
            RETURN r.sources AS sources, count(r) AS count
            ORDER BY count DESC
        """)
        for record in result:
            sources = record["sources"]
            count = record["count"]
            print(f"         {sources}: {count:,}")

        # CCC Validation Checks
        print("\n  Catechism (CCC) Checks:")

        # Check 12: CCC paragraph count
        result = session.run("MATCH (c:CatechismParagraph) RETURN count(c) AS count")
        ccc_count = result.single()["count"]
        passed = ccc_count >= EXPECTED_CCC_PARAGRAPHS
        all_passed &= check(
            "CCC paragraph count",
            passed,
            f"Found {ccc_count:,} paragraphs (expected >= {EXPECTED_CCC_PARAGRAPHS:,})"
        )

        # Check 13: CCC internal cross-references
        result = session.run("""
            MATCH (:CatechismParagraph)-[r:CROSS_REFERENCES]->(:CatechismParagraph)
            RETURN count(r) AS count
        """)
        ccc_internal = result.single()["count"]
        passed = ccc_internal >= EXPECTED_CCC_INTERNAL_REFS
        all_passed &= check(
            "CCC internal refs",
            passed,
            f"Found {ccc_internal:,} edges (expected >= {EXPECTED_CCC_INTERNAL_REFS:,})"
        )

        # Check 14: CCC→Verse citations
        result = session.run("""
            MATCH (:CatechismParagraph)-[r:CITES]->(:Verse)
            RETURN count(r) AS count
        """)
        ccc_scripture = result.single()["count"]
        passed = ccc_scripture >= EXPECTED_CCC_SCRIPTURE_REFS
        all_passed &= check(
            "CCC→Scripture citations",
            passed,
            f"Found {ccc_scripture:,} edges (expected >= {EXPECTED_CCC_SCRIPTURE_REFS:,})"
        )

        # Check 15: External document count
        result = session.run("MATCH (d:ExternalDocument) RETURN count(d) AS count")
        ext_doc_count = result.single()["count"]
        passed = ext_doc_count >= EXPECTED_EXTERNAL_DOCS
        all_passed &= check(
            "External document nodes",
            passed,
            f"Found {ext_doc_count:,} documents (expected >= {EXPECTED_EXTERNAL_DOCS:,})"
        )

        # Check 16: CCC→ExternalDocument citations
        result = session.run("""
            MATCH (:CatechismParagraph)-[r:CITES]->(:ExternalDocument)
            RETURN count(r) AS count
        """)
        ccc_external = result.single()["count"]
        passed = ccc_external >= EXPECTED_CCC_EXTERNAL_REFS
        all_passed &= check(
            "CCC→ExtDoc citations",
            passed,
            f"Found {ccc_external:,} edges (expected >= {EXPECTED_CCC_EXTERNAL_REFS:,})"
        )

        # Check 17: Sample CCC→Scripture edge (CCC 232 → Mt 28:19)
        result = session.run("""
            MATCH (c:CatechismParagraph {id: 'CCC-232'})-[r:CITES]->(v:Verse {id: 'MAT-28-19'})
            RETURN count(r) AS count
        """)
        sample_edge = result.single()["count"]
        passed = sample_edge > 0
        all_passed &= check(
            "CCC-232 → MAT-28-19",
            passed,
            "Trinity citation edge exists" if passed else "Missing expected edge"
        )

        # Check 18: CCC passage groups exist
        result = session.run("""
            MATCH (:CatechismParagraph)-[r:CROSS_REFERENCES]->(:CatechismParagraph)
            WHERE r.passage_group IS NOT NULL
            RETURN count(DISTINCT r.passage_group) AS count
        """)
        ccc_passage_groups = result.single()["count"]
        passed = ccc_passage_groups > 0
        all_passed &= check(
            "CCC passage groups",
            passed,
            f"Found {ccc_passage_groups:,} distinct passage groups"
        )

        # Typology Validation Checks
        print("\n  Typology Checks:")

        # Check 19: Type node count
        result = session.run("MATCH (t:Type) RETURN count(t) AS count")
        type_count = result.single()["count"]
        passed = type_count >= EXPECTED_TYPE_COUNT
        all_passed &= check(
            "Type node count",
            passed,
            f"Found {type_count:,} types (expected >= {EXPECTED_TYPE_COUNT:,})"
        )

        # Check 20: PREFIGURES edges
        result = session.run("MATCH (:Type)-[r:PREFIGURES]->(:Type) RETURN count(r) AS count")
        prefigures_count = result.single()["count"]
        passed = prefigures_count >= EXPECTED_PREFIGURES
        all_passed &= check(
            "PREFIGURES edges",
            passed,
            f"Found {prefigures_count:,} type → antitype edges (expected >= {EXPECTED_PREFIGURES:,})"
        )

        # Check 21: MEMBER_OF edges
        result = session.run("MATCH (:Verse)-[r:MEMBER_OF]->(:Type) RETURN count(r) AS count")
        member_count = result.single()["count"]
        passed = member_count > 0
        all_passed &= check(
            "MEMBER_OF edges",
            passed,
            f"Found {member_count:,} Verse → Type edges"
        )

        # Check 22: TEACHES edges
        result = session.run("MATCH (:CatechismParagraph)-[r:TEACHES]->(:Type) RETURN count(r) AS count")
        teaches_count = result.single()["count"]
        passed = teaches_count > 0
        all_passed &= check(
            "TEACHES edges",
            passed,
            f"Found {teaches_count:,} CCC → Type edges"
        )

        # Check 23: Sample PREFIGURES edge (Melchizedek → Christ the High Priest)
        result = session.run("""
            MATCH (:Type {id: 'melchizedek'})-[r:PREFIGURES]->(:Type {id: 'christ-high-priest'})
            RETURN count(r) AS count
        """)
        sample_prefig = result.single()["count"]
        passed = sample_prefig > 0
        all_passed &= check(
            "melchizedek → christ-high-priest",
            passed,
            "PREFIGURES edge exists" if passed else "Missing expected edge"
        )

        # Check 24: Sample MEMBER_OF (verses attesting the melchizedek type)
        result = session.run("""
            MATCH (:Verse)-[r:MEMBER_OF]->(:Type {id: 'melchizedek'})
            RETURN count(r) AS count
        """)
        sample_member = result.single()["count"]
        passed = sample_member > 0
        all_passed &= check(
            "Verses → melchizedek",
            passed,
            f"Found {sample_member} verse memberships"
        )

        # Check 25: Reviewed (Haydock) provenance present on PREFIGURES edges
        result = session.run("""
            MATCH (:Type)-[r:PREFIGURES]->(:Type)
            WHERE 'haydock' IN r.sources
            RETURN count(r) AS count
        """)
        haydock_prefig = result.single()["count"]
        passed = haydock_prefig > 0
        all_passed &= check(
            "Haydock-sourced PREFIGURES",
            passed,
            f"Found {haydock_prefig:,} edges with 'haydock' in sources"
        )

        # Typology Integrity Checks (must hold for a consistent graph)
        print("\n  Typology Integrity Checks:")

        # Check 26: No PREFIGURES self-loops (a type prefiguring itself)
        result = session.run("MATCH (t:Type)-[r:PREFIGURES]->(t) RETURN count(r) AS count")
        self_loops = result.single()["count"]
        all_passed &= check(
            "No PREFIGURES self-loops",
            self_loops == 0,
            f"Found {self_loops} self-loops (expected 0)"
        )

        # Check 27: Every PREFIGURES edge has provenance (non-empty sources)
        result = session.run("""
            MATCH ()-[r:PREFIGURES]->()
            WHERE r.sources IS NULL OR size(r.sources) = 0
            RETURN count(r) AS count
        """)
        no_sources = result.single()["count"]
        all_passed &= check(
            "PREFIGURES provenance present",
            no_sources == 0,
            f"Found {no_sources} edges with empty sources (expected 0)"
        )

        # Check 28: All Type nodes have valid name + testament
        result = session.run("""
            MATCH (t:Type)
            WHERE t.name IS NULL OR NOT t.testament IN ['OT', 'NT']
            RETURN count(t) AS count
        """)
        bad_types = result.single()["count"]
        all_passed &= check(
            "Type required properties",
            bad_types == 0,
            f"Found {bad_types} Types with missing name or invalid testament (expected 0)"
        )

        # Check 29: MEMBER_OF / TEACHES only point at Type nodes
        result = session.run("""
            MATCH (:Verse)-[r:MEMBER_OF]->(x) WHERE NOT x:Type
            RETURN count(r) AS count
        """)
        bad_member = result.single()["count"]
        result = session.run("""
            MATCH (:CatechismParagraph)-[r:TEACHES]->(x) WHERE NOT x:Type
            RETURN count(r) AS count
        """)
        bad_teaches = result.single()["count"]
        all_passed &= check(
            "MEMBER_OF / TEACHES endpoints are Types",
            bad_member == 0 and bad_teaches == 0,
            f"Found {bad_member} bad MEMBER_OF, {bad_teaches} bad TEACHES (expected 0)"
        )

        # Typology Sample Queries (Phase 5.2 acceptance — must return results)
        print("\n  Typology Sample Queries:")

        # Check 30: "What prefigures Baptism?"
        result = session.run("""
            MATCH (ot:Type)-[:PREFIGURES]->(:Type {id: 'baptism'})
            RETURN count(ot) AS count
        """)
        baptism_types = result.single()["count"]
        all_passed &= check(
            "What prefigures Baptism?",
            baptism_types >= EXPECTED_BAPTISM_TYPES,
            f"Found {baptism_types} OT types → baptism (expected >= {EXPECTED_BAPTISM_TYPES})"
        )

        # Check 31: "What Types does CCC-1094 teach?"
        result = session.run("""
            MATCH (:CatechismParagraph {id: 'CCC-1094'})-[:TEACHES]->(t:Type)
            RETURN count(t) AS count
        """)
        ccc1094_types = result.single()["count"]
        all_passed &= check(
            "CCC-1094 teaches Types",
            ccc1094_types >= EXPECTED_CCC1094_TYPES,
            f"Found {ccc1094_types} types taught by CCC-1094 (expected >= {EXPECTED_CCC1094_TYPES})"
        )

        # Check 32: Verse → Type membership (GEN-7-11 supports noahs-flood)
        result = session.run("""
            MATCH (:Verse {id: 'GEN-7-11'})-[:MEMBER_OF]->(t:Type {id: 'noahs-flood'})
            RETURN count(t) AS count
        """)
        sample_membership = result.single()["count"]
        all_passed &= check(
            "GEN-7-11 → noahs-flood",
            sample_membership > 0,
            "MEMBER_OF edge exists" if sample_membership else "Missing expected edge"
        )

        # Informational typology reports (not pass/fail)
        print("\n  Typology Distribution (informational):")
        result = session.run("MATCH (t:Type) RETURN t.testament AS k, count(*) AS n ORDER BY n DESC")
        print("         Testament:   " + ", ".join(f"{r['k']}={r['n']}" for r in result))
        result = session.run("""
            MATCH (a:Type)-[:PREFIGURES]->(b:Type)
            RETURN a.testament + '->' + b.testament AS k, count(*) AS n ORDER BY n DESC
        """)
        print("         Direction:   " + ", ".join(f"{r['k']}={r['n']}" for r in result))
        result = session.run("""
            MATCH ()-[r:PREFIGURES]->()
            RETURN coalesce(r.category, '(none)') AS k, count(*) AS n ORDER BY n DESC
        """)
        print("         Category:    " + ", ".join(f"{r['k']}={r['n']}" for r in result))
        result = session.run("""
            MATCH ()-[r:PREFIGURES]->()
            RETURN coalesce(r.confidence, '(none)') AS k, count(*) AS n ORDER BY n DESC
        """)
        print("         Confidence:  " + ", ".join(f"{r['k']}={r['n']}" for r in result))
        orphans = session.run("MATCH (t:Type) WHERE NOT (t)--() RETURN count(t) AS n").single()["n"]
        no_member = session.run(
            "MATCH (t:Type) WHERE NOT (:Verse)-[:MEMBER_OF]->(t) RETURN count(t) AS n"
        ).single()["n"]
        print(f"         Orphan Types (no edges): {orphans}")
        print(f"         Types with no MEMBER_OF (no scriptural evidence): {no_member}")
        print("         Most-attested PREFIGURES (by source_verses):")
        result = session.run("""
            MATCH (a:Type)-[r:PREFIGURES]->(b:Type)
            RETURN a.id AS f, b.id AS t, size(r.source_verses) AS nv
            ORDER BY nv DESC LIMIT 5
        """)
        for r in result:
            print(f"           {r['f']} → {r['t']}  ({r['nv']} verses)")

    connection.close()

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All validation checks passed!")
        print("=" * 60 + "\n")
        return 0
    else:
        print("✗ Some validation checks failed")
        print("=" * 60 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())