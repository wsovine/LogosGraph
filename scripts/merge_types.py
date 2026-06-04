"""Merge duplicate typology types into canonical forms.

Applies a merge map to reviewed data files, consolidating near-duplicate
types created during AI-assisted review into generalized canonical types.

Usage:
    python scripts/merge_types.py [--dry-run] [--verbose]
"""

import argparse
import json
import shutil
from pathlib import Path

DATA_DIR = Path("data/reviewed")
SEED_FILE = Path("data/seed/ccc_types.json")
NEW_TYPES_FILE = DATA_DIR / "new_types.jsonl"
APPROVED_FILE = DATA_DIR / "typology_approved.jsonl"

# old ID -> canonical ID
MERGE_MAP: dict[str, str] = {
    # Red Heifer variants
    "red-heifer-sacrifice": "red-heifer",
    "red-heifer-purification-rite": "red-heifer",
    "the-red-heifer-ashes-of-purification": "red-heifer",
    "the-red-heifer-purification-from-defilement": "red-heifer",
    "water-of-purification-ashes-of-the-red-heifer": "red-heifer",
    # Brazen Serpent
    "the-brazen-serpent": "brazen-serpent",
    "the-brazen-serpent-lifted-up": "brazen-serpent",
    # Binding of Isaac
    "isaac-as-willing-sacrifice": "binding-of-isaac",
    "isaacs-willing-sacrifice-the-akkedah": "binding-of-isaac",
    # Sarah
    "sarah-as-blessed-mother": "sarah",
    "sarah-as-mother-of-the-faithful": "sarah",
    "sarah-as-faithful-wife-of-the-patriarch": "sarah",
    # Rebecca
    "rebecca-as-bride-adorned-with-virtues": "rebecca",
    "rebeccas-espousal-to-isaac-at-the-fountain": "rebecca",
    # Joseph (figure-level)
    "joseph-deliverer-from-servitude": "joseph",
    "josephs-exaltation-and-cosmic-homage": "joseph",
    "josephs-sceptre-rod-of-authority": "joseph",
    "joseph-as-figure-of-christ-life-and-character": "joseph",
    # Moses (figure-level)
    "moses-uplifted-hands-against-amalek": "moses",
    "moses-radiant-face-glory-of-the-old-covenant": "moses",
    "moses-rod-striking-the-rock-twice": "moses",
    "moses-ethiopian-wife-inclusion-of-a-foreigner": "moses",
    "the-veil-on-moses-face": "moses",
    # Jacob
    "jacobs-ladder": "jacob",
    "jacob-as-man-of-sorrows": "jacob",
    # Judah
    "judahs-foal-tied-to-the-vine": "judah",
    "washing-robes-in-wine-genesis-49-11": "judah",
    # Adam
    "mans-created-in-gods-image": "adam",
    "man-created-in-gods-image": "adam",
    "adams-disobedience": "adam",
    # Joshua
    "joshua-as-leader-into-the-promised-inheritance": "joshua",
    # Eve
    "eve-as-mother-of-the-living": "eve",
    # Abel
    "abels-martyrdom": "abel",
    # Ishmael
    "ishmaels-persecution-of-isaac": "ishmael",
    # Leah
    "leah-as-the-laborious-wife": "leah",
    # Aaron
    "aarons-budding-rod": "aaron",
    # Miriam
    "miriam-as-figure-of-the-blessed-virgin-mary": "miriam",
    # Burning Bush
    "the-burning-bush-angel-of-the-lord-as-the-son-of-god": "burning-bush",
    # NT Antitypes
    "jesus-christ-in-human-nature": "christ",  # existing seed type
    "christs-cross-passion-and-resurrection": "christs-passion",
    "the-cross-of-christ": "christs-passion",
    # Marian consolidation (round 2)
    "mary-as-mother-of-life": "mary",
    "marys-virginal-motherhood": "mary",
    # Veil consolidation (round 2) — both describe aspects of Christ's passion/death
    "the-rending-of-the-temple-veil-at-christs-death": "christs-passion",
    "christs-removal-of-the-veil-of-the-old-law": "christs-passion",
    # Figure-level generalizations (round 3)
    "noahs-nakedness": "noah",
    "gideons-fleece": "gideon",
    "balaams-star": "balaam",
    # Verbose name simplifications (round 3)
    "levitical-leprosy-laws-priestly-judgment-of-leprosy": "levitical-leprosy-laws",
    "feast-of-pentecost-giving-of-the-law-at-sinai": "feast-of-pentecost",
    "the-cloud-of-legal-observances-old-testament-ceremonial-law": "ceremonial-law",
    "christian-ordained-priesthood-sacrament-of-holy-orders": "holy-orders",
    "final-judgment-and-deluge-of-fire": "final-judgment",
    "clean-and-unclean-animals-dietary-laws": "dietary-laws",
    # Orphaned references
    "the-pillar-of-fire": "cloud-in-desert",  # merge into seed type
}

# New canonical type definitions to add to new_types.jsonl
# (skip types that already exist in seed data)
CANONICAL_TYPES: dict[str, dict] = {
    "red-heifer": {
        "id": "red-heifer",
        "name": "Red Heifer",
        "testament": "OT",
        "description": "The red heifer sacrifice prescribed in Numbers 19, whose ashes mixed with water purified those defiled by contact with the dead.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "brazen-serpent": {
        "id": "brazen-serpent",
        "name": "Brazen Serpent",
        "testament": "OT",
        "description": "The bronze serpent Moses lifted up on a pole in the wilderness so that all who looked upon it were healed (Numbers 21:8-9).",
        "source": "haydock-review",
        "confidence": "high",
        "reviewed": True,
    },
    "binding-of-isaac": {
        "id": "binding-of-isaac",
        "name": "Binding of Isaac",
        "testament": "OT",
        "description": "Abraham's willing sacrifice of his son Isaac on Mount Moriah (Genesis 22).",
        "source": "haydock-review",
        "confidence": "high",
        "reviewed": True,
    },
    "sarah": {
        "id": "sarah",
        "name": "Sarah",
        "testament": "OT",
        "description": "Sarah, wife of Abraham and mother of Isaac, the free woman whose son was born according to the promise.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "rebecca": {
        "id": "rebecca",
        "name": "Rebecca",
        "testament": "OT",
        "description": "Rebecca, wife of Isaac, chosen by divine providence as bride for the patriarch's son.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "joseph": {
        "id": "joseph",
        "name": "Joseph",
        "testament": "OT",
        "description": "Joseph, son of Jacob, sold by his brothers yet exalted to deliver his people from famine.",
        "source": "haydock-review",
        "confidence": "high",
        "reviewed": True,
    },
    "moses": {
        "id": "moses",
        "name": "Moses",
        "testament": "OT",
        "description": "Moses, liberator and lawgiver of Israel, mediator of the Old Covenant.",
        "source": "haydock-review",
        "confidence": "high",
        "reviewed": True,
    },
    "jacob": {
        "id": "jacob",
        "name": "Jacob",
        "testament": "OT",
        "description": "Jacob (Israel), patriarch whose life of struggle and sorrow prefigures Christ.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "judah": {
        "id": "judah",
        "name": "Judah",
        "testament": "OT",
        "description": "Judah, son of Jacob, from whose tribe the Messiah descends (Genesis 49).",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "adam": {
        "id": "adam",
        "name": "Adam",
        "testament": "OT",
        "description": "Adam, the first man, whose creation and fall prefigure Christ as the New Adam.",
        "source": "haydock-review",
        "confidence": "high",
        "reviewed": True,
    },
    "joshua": {
        "id": "joshua",
        "name": "Joshua",
        "testament": "OT",
        "description": "Joshua (Yehoshua), successor of Moses who led Israel into the Promised Land.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "eve": {
        "id": "eve",
        "name": "Eve",
        "testament": "OT",
        "description": "Eve, the first woman and mother of all the living.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "abel": {
        "id": "abel",
        "name": "Abel",
        "testament": "OT",
        "description": "Abel, the just son of Adam whose innocent blood was shed by his brother Cain.",
        "source": "haydock-review",
        "confidence": "high",
        "reviewed": True,
    },
    "ishmael": {
        "id": "ishmael",
        "name": "Ishmael",
        "testament": "OT",
        "description": "Ishmael, son of Abraham by Hagar, the son of the bondwoman born according to the flesh.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "leah": {
        "id": "leah",
        "name": "Leah",
        "testament": "OT",
        "description": "Leah, first wife of Jacob, mother of six of the twelve tribes.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "aaron": {
        "id": "aaron",
        "name": "Aaron",
        "testament": "OT",
        "description": "Aaron, brother of Moses and first high priest of Israel.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "miriam": {
        "id": "miriam",
        "name": "Miriam",
        "testament": "OT",
        "description": "Miriam, sister of Moses and Aaron, prophetess of Israel.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "burning-bush": {
        "id": "burning-bush",
        "name": "Burning Bush",
        "testament": "OT",
        "description": "The bush that burned with fire but was not consumed, in which the Angel of the Lord appeared to Moses (Exodus 3).",
        "source": "haydock-review",
        "confidence": "high",
        "reviewed": True,
    },
    "christs-passion": {
        "id": "christs-passion",
        "name": "Christ's Passion",
        "testament": "NT",
        "description": "The suffering and crucifixion of Jesus Christ for the redemption of mankind.",
        "source": "haydock-review",
        "confidence": "high",
        "reviewed": True,
    },
    "mary": {
        "id": "mary",
        "name": "Mary",
        "testament": "NT",
        "description": "The Blessed Virgin Mary, Mother of God and Mother of the Church.",
        "source": "haydock-review",
        "confidence": "high",
        "reviewed": True,
    },
    # Figure-level generalizations (round 3)
    "noah": {
        "id": "noah",
        "name": "Noah",
        "testament": "OT",
        "description": "Noah, the just man who found favor with God and was preserved through the Flood.",
        "source": "haydock-review",
        "confidence": "high",
        "reviewed": True,
    },
    "gideon": {
        "id": "gideon",
        "name": "Gideon",
        "testament": "OT",
        "description": "Gideon, judge of Israel who delivered his people with a small band chosen by God.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "balaam": {
        "id": "balaam",
        "name": "Balaam",
        "testament": "OT",
        "description": "Balaam, the pagan seer whose oracles included the prophecy of the Star from Jacob (Numbers 24:17).",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    # Verbose name simplifications (round 3)
    "levitical-leprosy-laws": {
        "id": "levitical-leprosy-laws",
        "name": "Levitical Leprosy Laws",
        "testament": "OT",
        "description": "The Levitical laws governing the diagnosis, quarantine, and purification of leprosy (Leviticus 13-14).",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "feast-of-pentecost": {
        "id": "feast-of-pentecost",
        "name": "Feast of Pentecost",
        "testament": "OT",
        "description": "The Feast of Weeks (Shavuot), celebrating the firstfruits of the harvest and the giving of the Law at Sinai.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "ceremonial-law": {
        "id": "ceremonial-law",
        "name": "Ceremonial Law",
        "testament": "OT",
        "description": "The ceremonial and ritual prescriptions of the Old Testament Law, fulfilled and surpassed in the New Covenant.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "holy-orders": {
        "id": "holy-orders",
        "name": "Holy Orders",
        "testament": "NT",
        "description": "The Sacrament of Holy Orders, by which men are ordained to the Christian priesthood.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "final-judgment": {
        "id": "final-judgment",
        "name": "Final Judgment",
        "testament": "NT",
        "description": "The Last Judgment at the end of time, when Christ will judge the living and the dead.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    "dietary-laws": {
        "id": "dietary-laws",
        "name": "Dietary Laws",
        "testament": "OT",
        "description": "The Mosaic laws distinguishing clean and unclean animals (Leviticus 11, Deuteronomy 14).",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
    # Orphaned type definitions
    "the-wilderness-pilgrimage-toward-the-promised-land": {
        "id": "the-wilderness-pilgrimage-toward-the-promised-land",
        "name": "Wilderness Pilgrimage toward the Promised Land",
        "testament": "OT",
        "description": "Israel's forty-year journey through the wilderness toward the earthly Promised Land.",
        "source": "haydock-review",
        "confidence": "high",
        "reviewed": True,
    },
    "the-holy-spirit-as-divine-guide": {
        "id": "the-holy-spirit-as-divine-guide",
        "name": "The Holy Spirit as Divine Guide",
        "testament": "NT",
        "description": "The Holy Spirit who guides the Church and individual believers, as the pillar of cloud guided Israel.",
        "source": "haydock-review",
        "confidence": "medium",
        "reviewed": True,
    },
}


def load_jsonl(path: Path) -> list[dict]:
    lines = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    return lines


def write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_seed_type_ids() -> set[str]:
    with open(SEED_FILE) as f:
        data = json.load(f)
    return {t["id"] for t in data["types"]}


def rewrite_id(type_id: str) -> str:
    return MERGE_MAP.get(type_id, type_id)


def main():
    parser = argparse.ArgumentParser(description="Merge duplicate typology types")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without modifying files")
    parser.add_argument("--verbose", action="store_true", help="Print detailed changes")
    args = parser.parse_args()

    seed_ids = load_seed_type_ids()

    # --- Process new_types.jsonl ---
    new_types = load_jsonl(NEW_TYPES_FILE)
    old_type_ids = {t["id"] for t in new_types}

    # IDs to remove (they're being merged into canonical forms)
    ids_to_remove = set(MERGE_MAP.keys())

    # Keep types not in the merge map
    kept_types = [t for t in new_types if t["id"] not in ids_to_remove]
    kept_ids = {t["id"] for t in kept_types}

    # Add canonical types that don't exist in seed or already-kept types
    added_canonical = []
    for cid, cdef in CANONICAL_TYPES.items():
        if cid not in seed_ids and cid not in kept_ids:
            added_canonical.append(cdef)

    final_types = kept_types + added_canonical
    removed_count = len(old_type_ids) - len({t["id"] for t in kept_types})

    # --- Process typology_approved.jsonl ---
    approved = load_jsonl(APPROVED_FILE)
    rewrite_count = 0
    dedup_before = len(approved)

    for record in approved:
        old_type = record["type_id"]
        old_anti = record["antitype_id"]
        record["type_id"] = rewrite_id(old_type)
        record["antitype_id"] = rewrite_id(old_anti)
        if record["type_id"] != old_type or record["antitype_id"] != old_anti:
            rewrite_count += 1
            if args.verbose:
                changes = []
                if record["type_id"] != old_type:
                    changes.append(f"type: {old_type} -> {record['type_id']}")
                if record["antitype_id"] != old_anti:
                    changes.append(f"antitype: {old_anti} -> {record['antitype_id']}")
                print(f"  {record['verse_id']}: {', '.join(changes)}")

    # Deduplicate by (verse_id, type_id, antitype_id) — keep first occurrence
    seen = set()
    deduped = []
    for record in approved:
        key = (record["verse_id"], record["type_id"], record["antitype_id"])
        if key not in seen:
            seen.add(key)
            deduped.append(record)
    dedup_removed = dedup_before - len(deduped)

    # --- Validate: every referenced ID exists in seed or new types ---
    all_defined_ids = seed_ids | {t["id"] for t in final_types}
    referenced_ids = set()
    for record in deduped:
        referenced_ids.add(record["type_id"])
        referenced_ids.add(record["antitype_id"])

    orphaned = referenced_ids - all_defined_ids
    if orphaned:
        print(f"WARNING: {len(orphaned)} orphaned type IDs still referenced but not defined:")
        for oid in sorted(orphaned):
            print(f"  - {oid}")

    # --- Summary ---
    print(f"\nnew_types.jsonl:")
    print(f"  Removed: {removed_count} duplicate type definitions")
    print(f"  Added:   {len(added_canonical)} canonical type definitions")
    print(f"  Total:   {len(old_type_ids)} -> {len(final_types)}")

    print(f"\ntypology_approved.jsonl:")
    print(f"  Rewritten: {rewrite_count} type/antitype references")
    print(f"  Deduped:   {dedup_removed} duplicate records removed")
    print(f"  Total:     {dedup_before} -> {len(deduped)}")

    if orphaned:
        print(f"\nValidation: FAILED ({len(orphaned)} orphaned references)")
    else:
        print(f"\nValidation: PASSED (all referenced IDs defined)")

    if args.dry_run:
        print("\n[DRY RUN] No files modified.")
        return

    # --- Back up and write ---
    shutil.copy2(NEW_TYPES_FILE, NEW_TYPES_FILE.with_suffix(".jsonl.bak"))
    shutil.copy2(APPROVED_FILE, APPROVED_FILE.with_suffix(".jsonl.bak"))

    write_jsonl(NEW_TYPES_FILE, final_types)
    write_jsonl(APPROVED_FILE, deduped)

    print("\nFiles updated. Backups saved as .jsonl.bak")


if __name__ == "__main__":
    main()
