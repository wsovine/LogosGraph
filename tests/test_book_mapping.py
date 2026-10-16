"""Tests for Psalm renumbering and reader-facing verse references."""

import pytest

from src.data.book_mapping import display_ref, hebrew_to_vulgate_psalm, vulgate_to_hebrew_psalm


@pytest.mark.parametrize(
    "vulgate, hebrew",
    [
        ((1, 1), (1, 1)),          # 1-8 identical
        ((9, 21), (9, 21)),        # Vulgate 9 first half = Hebrew 9
        ((9, 22), (10, 1)),        # ... second half = Hebrew 10
        ((21, 2), (22, 2)),        # "My God, my God" (offset +1)
        ((109, 4), (110, 4)),      # Melchizedek: "priest forever"
        ((113, 8), (114, 8)),      # Vulgate 113 first half = Hebrew 114
        ((113, 9), (115, 1)),      # ... second half = Hebrew 115
        ((114, 9), (116, 9)),      # Vulgate 114 = Hebrew 116:1-9
        ((115, 1), (116, 10)),     # Vulgate 115 = Hebrew 116:10-19
        ((117, 22), (118, 22)),    # Rejected cornerstone
        ((146, 11), (147, 11)),    # Vulgate 146 = Hebrew 147:1-11
        ((147, 1), (147, 12)),     # Vulgate 147 = Hebrew 147:12-20
        ((150, 6), (150, 6)),      # 148-150 identical
    ],
)
def test_vulgate_to_hebrew_psalm(vulgate, hebrew):
    assert vulgate_to_hebrew_psalm(*vulgate) == hebrew


@pytest.mark.parametrize("vulgate_chapter", [1, 8, 10, 50, 112, 116, 145, 148, 150])
def test_round_trip_for_unsplit_psalms(vulgate_chapter):
    hebrew_chapter, _ = vulgate_to_hebrew_psalm(vulgate_chapter, 1)
    assert hebrew_to_vulgate_psalm(hebrew_chapter) == vulgate_chapter


@pytest.mark.parametrize(
    "verse_id, expected",
    [
        ("GEN-14-18", "Genesis 14:18"),
        ("1CO-10-4", "1 Corinthians 10:4"),
        ("PSA-109-4", "Psalm 109 (110):4"),
        ("PSA-9-22", "Psalm 9:22 (10:1)"),
        ("PSA-147-1", "Psalm 147:1 (147:12)"),
        ("PSA-23-1", "Psalm 23 (24):1"),
        ("PSA-150-1", "Psalm 150:1"),
        ("REV-18-0", "Revelation 18"),
    ],
)
def test_display_ref(verse_id, expected):
    assert display_ref(verse_id) == expected
