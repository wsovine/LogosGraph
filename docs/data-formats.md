# Data Formats

This document describes the JSON and JSONL file formats used throughout the project.

## Seed Data (JSON)

Curated data files in `data/seed/` that define the initial typology graph.

### ccc_types.json

Defines Type nodes extracted from the Catechism.

```json
{
  "types": [
    {
      "id": "noahs-flood",
      "name": "Noah's Flood",
      "testament": "OT",
      "category": "Sacramental",
      "description": "The flood that cleansed the earth...",
      "source": "CCC-1094",
      "confidence": "high",
      "reviewed": true
    }
  ]
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique slug identifier (kebab-case) |
| `name` | string | yes | Human-readable name |
| `testament` | `"OT"` or `"NT"` | yes | Old or New Testament |
| `category` | string | no | Category (see below) |
| `description` | string | no | Brief description |
| `source` | string | yes | Source reference (e.g., "CCC-1094") |
| `confidence` | `"high"`, `"medium"`, `"low"` | yes | Confidence level |
| `reviewed` | boolean | yes | Whether human-reviewed |

**Note:** Category on Type nodes is optional/legacy. Category now primarily lives on PREFIGURES relationships.

---

### ccc_prefigures.json

Defines PREFIGURES relationships between OT types and NT antitypes.

```json
{
  "relationships": [
    {
      "from_type": "noahs-flood",
      "to_type": "baptism",
      "source": "CCC-1094",
      "confidence": "high",
      "notes": "The flood prefigured salvation by Baptism"
    }
  ]
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from_type` | string | yes | OT type ID |
| `to_type` | string | yes | NT antitype ID |
| `source` | string | yes | Source reference (e.g., "CCC-1094") |
| `confidence` | string | yes | Confidence level |
| `category` | string | no | Category for this relationship |
| `notes` | string | no | Authoritative description (becomes `description` on PREFIGURES edge) |

---

### ccc_verse_memberships.json

Maps verses to the types they support as scriptural evidence.

```json
{
  "memberships": [
    {
      "type_id": "noahs-flood",
      "verse_ids": ["GEN-7-1", "GEN-7-7", "1PE-3-20", "1PE-3-21"]
    }
  ]
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type_id` | string | yes | Type ID |
| `verse_ids` | string[] | yes | List of verse IDs |

**Verse ID Format:** `BOOK-CHAPTER-VERSE` (e.g., `GEN-7-1`, `1CO-10-4`)

---

### ccc_teaches.json

Maps CCC paragraphs to the types they discuss.

```json
{
  "teaches": [
    {
      "ccc_id": "CCC-1094",
      "type_ids": ["noahs-flood", "noahs-ark", "red-sea-crossing", "baptism"]
    }
  ]
}
```

---

## Extraction Data (JSONL)

Line-delimited JSON files in `data/extracted/` produced by extraction scripts.

### haydock_footers.jsonl

All footer comments extracted from Haydock USFM files.

```json
{"verse_id": "GEN-1-6", "book": "GEN", "chapter": 1, "verse": 6, "text": "A firmament. By this name...", "source": "Haydock"}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `verse_id` | string | Verse identifier |
| `book` | string | Book abbreviation |
| `chapter` | int | Chapter number |
| `verse` | int | Verse number |
| `text` | string | Commentary text |
| `source` | string | Always "Haydock" |

---

### haydock_typology_candidates.jsonl

Footers filtered for typology keywords.

```json
{"verse_id": "GEN-2-24", "book": "GEN", "chapter": 2, "verse": 24, "text": "...prefigured by this indissoluble marriage...", "source": "Haydock", "matched_keywords": ["\\bprefigure"]}
```

**Additional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `matched_keywords` | string[] | Regex patterns that matched |

---

### haydock_typology_raw.jsonl

LLM extraction results.

```json
{
  "verse_id": "GEN-1-26",
  "book": "GEN",
  "chapter": 1,
  "verse": 26,
  "original_text": "Let us make man to our image...",
  "has_typology": true,
  "extractions": [
    {
      "type_name": "Man created in the image of God",
      "type_description": "The human being, particularly Adam...",
      "antitype_name": "Jesus Christ in human nature",
      "antitype_description": "Christ who assumed human nature...",
      "category": "Christological",
      "confidence": "high",
      "reasoning": "The commentary explicitly states..."
    }
  ],
  "notes": "Additional LLM notes...",
  "model": "claude-haiku-4-5",
  "input_tokens": 895,
  "output_tokens": 376,
  "error": null
}
```

**Extraction Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `type_name` | string | LLM-suggested OT type name |
| `type_description` | string | Description of the type |
| `antitype_name` | string | LLM-suggested NT antitype name |
| `antitype_description` | string | Description of the antitype |
| `category` | string | One of the valid categories |
| `confidence` | string | `high`, `medium`, or `low` |
| `reasoning` | string | LLM's explanation |

---

## Reviewed Data (JSONL)

Human-reviewed data in `data/reviewed/`.

### typology_approved.jsonl

Approved extractions with normalized type IDs.

```json
{
  "verse_id": "GEN-1-26",
  "book": "GEN",
  "chapter": 1,
  "verse": 26,
  "original_text": "Let us make man to our image...",
  "type_id": "adam",
  "antitype_id": "christ",
  "category": "Christological",
  "confidence": "high",
  "extraction": { ... },
  "reviewer_notes": "Optional notes",
  "source": "haydock"
}
```

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `type_id` | string | Normalized OT type ID |
| `antitype_id` | string | Normalized NT antitype ID |
| `category` | string | Category for PREFIGURES edge |
| `confidence` | string | Confidence level for the relationship |
| `extraction` | object | Original LLM extraction |
| `reviewer_notes` | string | Reviewer explanation (becomes `logosgraph_notes` on PREFIGURES edge) |
| `source` | string | Source identifier (e.g., "haydock") |

---

### typology_rejected.jsonl

Rejected extractions.

```json
{
  "verse_id": "GEN-1-6",
  "book": "GEN",
  "chapter": 1,
  "verse": 6,
  "extraction": { ... },
  "rejection_reason": "Not actually typology"
}
```

---

### new_types.jsonl

New types created during review.

```json
{
  "id": "adam",
  "name": "Adam",
  "testament": "OT",
  "description": "The first man, created in God's image",
  "source": "haydock-review",
  "confidence": "medium",
  "reviewed": true
}
```

---

## Categories

Valid categories for typological relationships:

| Category | Description |
|----------|-------------|
| `Sacramental` | Types of Baptism, Eucharist, sacraments |
| `Christological` | Types of Christ (persons, events, objects) |
| `Ecclesial` | Types of the Church |
| `Marian` | Types of Mary |
| `Eschatological` | Types of end times, heaven, judgment |
| `Covenantal` | Types relating to covenant fulfillment |

---

## ID Conventions

| Entity | Format | Examples |
|--------|--------|----------|
| Verse | `BOOK-CHAPTER-VERSE` | `GEN-1-1`, `1CO-10-4`, `REV-21-1` |
| Type | kebab-case slug | `noahs-ark`, `red-sea-crossing`, `christ` |
| CCC | `CCC-{paragraph}` | `CCC-1094`, `CCC-527` |
| Book | 3-letter abbreviation | `GEN`, `EXO`, `1CO`, `REV` |
