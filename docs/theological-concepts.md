# Theological Concepts

The theological foundations underlying LogosGraph's structure and data.

---

## Scripture Interpreting Scripture

### The Principle

A core principle of biblical interpretation holds that Scripture interprets Scripture—passages illuminate each other across the canon. This principle, shared across Christian traditions, recognizes that:

- The Bible, despite multiple human authors, has divine unity
- Earlier passages provide context for later ones
- Later passages reveal the fuller meaning of earlier ones
- Themes, images, and language recur with developing significance

### Cross-References in Practice

Cross-references make this principle navigable. A reference from Romans to Genesis isn't merely a citation—it's an interpretive claim that these passages belong together, that understanding one requires the other.

LogosGraph's cross-reference network enables exploration of these connections:

- **Direct quotations**: NT explicitly quoting OT
- **Allusions**: Intentional echoes without direct quotation
- **Thematic parallels**: Similar concepts across different contexts
- **Verbal connections**: Shared terminology linking passages

Not all cross-references are equally strong. The graph preserves source attribution so users can assess connection quality. See [Data Sources](data-sources.md) for methodology details.

---

## Typology

### Definition

Typology is the theological reading of the Old Testament as containing "types"—persons, events, or institutions that prefigure their fulfillment ("antitypes") in Christ, the Church, and the sacraments.

The Catechism defines this approach (CCC 128-130):

> "The Church, as early as apostolic times, and then constantly in her Tradition, has illuminated the unity of the divine plan in the two Testaments through typology, which discerns in God's works of the Old Covenant prefigurations of what he accomplished in the fullness of time in the person of his incarnate Son."

### Types and Antitypes

| Type (OT) | Antitype (NT/Church) |
|-----------|---------------------|
| Noah's Ark | The Church / Baptism |
| Passover Lamb | Christ crucified |
| Manna | Eucharist |
| Bronze Serpent | Christ on the Cross |
| Melchizedek | Christ the High Priest |
| Isaac's sacrifice | Christ's sacrifice |
| Jonah in the whale | Christ in the tomb |

### Typology Categories

LogosGraph organizes types into categories reflecting their theological significance:

| Category | Description | Example |
|----------|-------------|---------|
| Christological | Prefigures Christ's person or work | Passover lamb → Christ |
| Sacramental | Prefigures sacraments | Flood → Baptism |
| Ecclesial | Prefigures the Church | Noah's Ark → Church |
| Marian | Prefigures Mary | Ark of Covenant → Mary |
| Eschatological | Prefigures end times | Promised Land → Heaven |
| Covenantal | Prefigures new covenant | Circumcision → Baptism |

### Typology vs. Allegory

Typology differs from allegory:

- **Typology** maintains the historical reality of both type and antitype. The Passover actually happened; Christ's sacrifice actually happened. The connection is between real events in salvation history.
- **Allegory** treats the text as symbolic without requiring historical grounding. Characters or events represent abstract concepts.

Catholic interpretation employs both but distinguishes them. Typology is grounded in the Church's understanding of salvation history as a unified divine plan.

### Why Typology Matters

Typology reflects core theological commitments:

1. **Scripture has divine unity**: God is the author of both Testaments
2. **Christ is the key**: All Scripture points to and finds fulfillment in Christ
3. **Revelation is progressive**: Earlier events prepare for later fulfillment
4. **The Church reads Scripture as a whole**: Individual passages are illuminated by the entire canon

---

## The Catholic Canon

### 73 Books

The Catholic Bible contains 73 books:

- **Old Testament**: 46 books
- **New Testament**: 27 books

This differs from the Protestant canon of 66 books. The seven additional books are called "deuterocanonical" (second canon):

| Book | Content |
|------|---------|
| Tobit | Narrative of faithful Israelite in exile |
| Judith | Narrative of Jewish heroine saving her people |
| Wisdom | Wisdom literature attributed to Solomon |
| Sirach (Ecclesiasticus) | Wisdom literature, ethical teaching |
| Baruch | Prophetic book attributed to Jeremiah's scribe |
| 1 Maccabees | History of Maccabean revolt |
| 2 Maccabees | Theological reflection on Maccabean period |

Additionally, the Catholic canon includes longer versions of Esther and Daniel with passages not in the Protestant canon.

### Why This Matters for LogosGraph

Most digital Bible resources only include 66 books, making them incomplete for Catholic use. LogosGraph uses the full 73-book canon to:

- Include all Scripture recognized by Catholic, Orthodox, and some Anglican traditions
- Preserve cross-references to and from deuterocanonical books
- Enable typological connections involving deuterocanonical passages (e.g., 2 Maccabees 12 on prayer for the dead)

The deuterocanonical books were part of the Septuagint (Greek Old Testament) used by the early Church and are quoted or alluded to in the New Testament.

---

## Magisterial Interpretation

### The Role of the Church

Catholic biblical interpretation operates within a framework of Tradition and Magisterium (teaching authority). Scripture is not interpreted in isolation but within the living tradition of the Church.

The Catechism of the Catholic Church represents the Magisterium's authoritative summary of Catholic faith, including how Scripture should be understood. When the CCC identifies a typological connection, that identification carries Magisterial weight.

### CCC in LogosGraph

The Catechism serves specific roles in LogosGraph:

1. **Scripture citations**: The CCC cites Scripture extensively, creating connections between doctrinal teaching and biblical texts
2. **Typology seeds**: CCC-identified types provide authoritative examples that guide interpretation of additional typological connections
3. **Interpretive framework**: The CCC's treatment of Scripture models how the Church reads the Bible

### Levels of Authority

Not all connections in LogosGraph carry equal weight:

| Source | Authority Level |
|--------|-----------------|
| CCC-identified types | Magisterial |
| Haydock (patristic tradition) | Traditional |
| TSK (Protestant scholarship) | Scholarly |
| LLM-extracted (unreviewed) | Provisional |

The graph preserves these distinctions through source attribution and review status, allowing users to filter by confidence level.

---

## Further Reading

- Catechism of the Catholic Church, paragraphs 101-141 (Sacred Scripture)
- Dei Verbum (Vatican II document on Divine Revelation)
- Pontifical Biblical Commission, "The Interpretation of the Bible in the Church" (1993)
