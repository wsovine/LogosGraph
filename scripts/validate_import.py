#!/usr/bin/env python3
"""Validate the Bible graph database import."""

import sys

from src.db.connection import get_connection

# Expected values
EXPECTED_VERSE_COUNT = 31000  # Approximate
EXPECTED_BOOK_COUNT = 73
EXPECTED_CROSSREF_COUNT = 340000  # Approximate minimum
DEUTEROCANONICAL_BOOKS = ["TOB", "JDT", "WIS", "SIR", "BAR", "1MA", "2MA"]


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