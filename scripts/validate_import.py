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