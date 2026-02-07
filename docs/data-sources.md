# Data Sources

Technical documentation for all data sources used in LogosGraph.

## Source Summary

| Source | Content | Format | License | Repository/URL |
|--------|---------|--------|---------|----------------|
| CPDV | Bible text (73 books) | JSON | Public Domain | [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) |
| TSK | Cross-refs (~500K) | TSV | CC Attribution | [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) |
| Haydock | Commentary + cross-refs | USFM | Public Domain | [cmahte/ENG-B-Haydock1883-pd-PSFM](https://github.com/cmahte/ENG-B-Haydock1883-pd-PSFM) |
| CCC | Catechism (2,865 paras) | HTML | Vatican | [vatican.va](https://www.vatican.va/archive/ENG0015/_INDEX.HTM) |

---

## Bible Text (CPDV)

The Catholic Public Domain Version provides the Scripture text for all verse nodes.

### Source Details

- **URL**: `https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/en/CPDV/CPDV.json`
- **Format**: JSON (books → chapters → verses)
- **License**: Public domain
- **Parser**: `src/data/cpdv_parser.py`

### Why CPDV?

The CPDV is the only readily available digital Bible with all 73 Catholic canon books in a parseable format. Most digital Bible sources only include the 66-book Protestant canon. While the CPDV translation itself is not widely used in Catholic practice, it provides complete canonical coverage necessary for a comprehensive Catholic Bible graph.

### Content

- 73 books (including deuterocanonicals)
- 35,817 verses
- Complete Old Testament (including Tobit, Judith, Wisdom, Sirach, Baruch, 1-2 Maccabees)
- Complete New Testament

---

## TSK Cross-References

### Source Details

- **URL**: `https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/extras/cross_references.txt`
- **Format**: Tab-separated values
- **License**: CC Attribution (via OpenBible.info)
- **Parser**: `src/data/tsk_parser.py`

### History

The Treasury of Scripture Knowledge was compiled across generations:

- **William Canne** (17th century) - Created original marginal Bible references
- **Thomas Scott** - Expanded in his biblical commentary
- **R.A. Torrey** (late 19th century) - Compiled and significantly expanded into the Treasury of Scripture Knowledge

The original work contains over 500,000 cross-references linking Scripture passages.

### Methodology & Limitations

Understanding the limitations of TSK helps interpret the data appropriately:

#### 1. Protestant Canon Only

TSK covers the 66 Protestant-canon books. The 7 deuterocanonical books (Tobit, Judith, Wisdom, Sirach, Baruch, 1-2 Maccabees) are not covered by TSK but are included via Haydock cross-references.

#### 2. English-Based Word Matching

Many TSK connections are based on English word matching in the King James Version, not the original languages:

- The Greek word *agape* (unconditional love) and *phileo* (friendship love) both translate to English "love"
- Hebrew terms may be linked to unrelated Greek terms simply because English translators used the same word
- Connections that appear meaningful in English may have no basis in Greek or Hebrew

This is a fundamental methodological weakness. A word study that seems profound in English may evaporate when examining the source texts.

#### 3. Broad Hermeneutic

The 19th-century approach emphasized finding any thematic or verbal parallel:

- Assumed the Bible forms a unified whole where virtually any parallel might illuminate meaning
- A shared word or concept was often sufficient to warrant a cross-reference
- Modern scholars would distinguish between:
  - **Direct quotations** (NT quoting OT)
  - **Clear allusions** (obvious intentional references)
  - **Thematic parallels** (similar concepts in different contexts)
  - **Verbal coincidences** (same English word, unrelated meaning)

TSK largely treats all of these as equivalent, which can obscure genuine connections.

#### 4. Devotional Purpose

TSK was designed for preachers and Bible students seeking material for meditation and sermon preparation:

- Quantity had practical value even if not every reference was exegetically sound
- Some connections are tenuous—shared words used in completely different contexts
- Comprehensiveness served apologetic purposes by demonstrating the Bible's internal coherence

### Quality Signal

The `votes` field comes from OpenBible.info's crowdsourced voting system, providing some quality filtering:

- Higher votes indicate stronger community confidence in a connection
- However, even high-voted connections may still be based on English word matching
- Use votes as a rough heuristic, not a guarantee of scholarly validity

## Haydock Cross-References

### Source Details

- **URL**: `https://github.com/cmahte/ENG-B-Haydock1883-pd-PSFM/archive/refs/heads/master.zip`
- **Format**: USFM (Unified Standard Format Markers)
- **License**: Public domain (1883 edition)
- **Parsers**: `src/data/haydock_parser.py`, `src/data/haydock_footer_parser.py`

### History

The Haydock Catholic Bible Commentary was compiled by George Leo Haydock between 1811-1859. It represents a comprehensive Catholic commentary on Scripture:

- **Complete Coverage**: All 73 books of the Catholic Bible, including deuterocanonicals
- **Patristic Sources**: Cross-references drawn from Church Fathers and Doctors of the Church
- **Catholic Perspective**: Grounded in Catholic theological tradition
- **Public Domain**: Original 1883 edition freely available

Unlike TSK's word-matching approach, Haydock's references often reflect theological and typological connections identified in the Catholic interpretive tradition.

Haydock edges do not have a `votes` property since they come from a single authoritative source rather than crowdsourced validation.

## Source Attribution in the Graph

Each `CROSS_REFERENCES` edge includes a `sources` array indicating which source(s) attest to the connection:

| sources | Meaning |
|---------|---------|
| `["TSK"]` | TSK only |
| `["Haydock"]` | Haydock only |
| `["TSK", "Haydock"]` | Both sources agree |

Connections attested by both sources may have stronger validity, though this is not guaranteed.

## Catechism of the Catholic Church (CCC)

### Source Details

- **URL Pattern**: `https://www.vatican.va/archive/ENG0015/__P{hex}.HTM` (hex codes 1-6C)
- **Format**: HTML pages (108 total)
- **License**: Vatican (standard usage terms)
- **Parsers**: `src/data/catechism_html_parser.py`, `src/data/catechism_citation_parser.py`

### Content

- 2,865 paragraphs organized across four pillars
- Scripture citations embedded in text
- Cross-references to other CCC paragraphs
- References to Church councils, papal documents, and Church Fathers

### Why CCC?

The Catechism provides Magisterial authority for identifying typological relationships. CCC paragraphs 128-130 establish the Church's teaching on typology, and scattered throughout the text are explicit identifications of types and antitypes (e.g., Noah's ark as a type of the Church, the Passover lamb as a type of Christ).

The CCC serves as seed data for typology extraction—providing authoritative examples that guide the interpretation of additional typological connections from Haydock and other sources.

### Parsing Approach

The HTML parsing extracts:
- Paragraph numbers and text
- Scripture citations (parsed into verse references)
- Internal CCC cross-references
- Section hierarchy (parts, sections, chapters, articles)

---

## Future Considerations

### Original Language Sources

Cross-references grounded in Greek, Hebrew, and Aramaic would address TSK's core limitation. Sources that analyze connections based on the original texts rather than English translations would significantly improve reliability.

### Additional Catholic Resources

Several resources could enhance the graph:

- **Navarre Bible Commentary**: Modern Catholic scholarly commentary with rich cross-references
- **Catena Aurea**: Aquinas's compilation of patristic commentary on the Gospels
- **Church Fathers directly**: Systematic extraction from patristic texts
- **Lectionary connections**: Links between readings in the liturgical cycle
- **Papal documents on Scripture**: Dei Verbum, Divino Afflante Spiritu, etc.
