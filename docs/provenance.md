# Data Provenance

Why LogosGraph uses the sources it does, and how they work together.

## The Challenge

Building a Catholic Bible knowledge graph requires solving several problems simultaneously:

1. **Complete canon**: Most digital Bible resources only cover 66 books, missing the 7 deuterocanonical books
2. **Catholic interpretation**: Protestant cross-reference sources may not reflect Catholic theological tradition
3. **Typological connections**: The unity of Scripture across Testaments is central to Catholic hermeneutics
4. **Authoritative grounding**: Interpretations should be connected to Magisterial teaching

No single source addresses all these needs. LogosGraph combines multiple sources, each chosen for specific strengths.

---

## Source Rationale

### CPDV (Bible Text)

**The problem**: Finding a digital Bible with all 73 Catholic canon books in a parseable format.

**Why CPDV**: It's the only readily available source meeting these criteria. While the translation itself isn't widely used in Catholic practice, it provides the complete canonical text necessary for comprehensive coverage. The public domain status allows unrestricted use.

**Limitations acknowledged**: The CPDV translation quality varies. For devotional reading, other translations (RSV-CE, NAB, Douay-Rheims) are preferred. For the graph structure, the exact translation matters less than having complete canonical coverage with accurate verse boundaries.

### TSK (Cross-References)

**The problem**: Building a comprehensive cross-reference network requires a large initial dataset.

**Why TSK**: With over 500,000 cross-references, TSK provides broad coverage that would be impossible to compile manually. The crowdsourced voting from OpenBible.info provides some quality signal.

**Limitations acknowledged**: TSK comes from the Protestant scholarly tradition and has significant methodological weaknesses (see [Data Sources](data-sources.md) for details). Many connections are based on English word matching rather than original language analysis. TSK also covers only 66 books, missing deuterocanonical references entirely.

**How we mitigate**: TSK is complemented by Haydock cross-references, which provide Catholic theological perspective and deuterocanonical coverage. The `sources` attribute on each edge allows filtering by source.

### Haydock (Commentary + Cross-References)

**The problem**: TSK represents Protestant scholarship; we need Catholic interpretive tradition.

**Why Haydock**: George Leo Haydock's commentary (1811-1859) draws extensively from Church Fathers and Doctors of the Church. It represents the Catholic exegetical tradition preserved across generations:

- Patristic interpretation from the first millennium
- Medieval scholastic insights (particularly Aquinas)
- Counter-Reformation Catholic scholarship
- English Catholic commentary tradition

**Unique value**: Haydock's cross-references often reflect typological connections—OT passages seen as prefiguring NT realities—that TSK's word-matching methodology misses entirely. The commentary explicitly identifies types and antitypes, providing source material for typology extraction.

**Complete coverage**: Haydock covers all 73 books, including rich commentary on the deuterocanonical books that are absent from Protestant sources.

### CCC (Catechism)

**The problem**: How do we ground typological interpretation in authoritative Catholic teaching?

**Why CCC**: The Catechism of the Catholic Church represents the Magisterium's authoritative summary of Catholic faith. For typology specifically:

- CCC 128-130 establishes the theological basis for typological reading
- Scattered throughout are explicit type/antitype identifications
- These serve as "seed types"—authoritative examples that guide interpretation

**Role in the project**: The CCC doesn't provide comprehensive typology coverage. Instead, it provides Magisterial grounding for the typology framework. CCC-identified types serve as seeds; Haydock extraction expands coverage while maintaining consistency with the authoritative examples.

---

## How Sources Complement Each Other

```
                    ┌─────────────────────────────────────┐
                    │          LogosGraph                 │
                    └─────────────────────────────────────┘
                                    ▲
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│   Bible Text  │           │ Cross-Refs    │           │   Typology    │
│     (CPDV)    │           │ (TSK+Haydock) │           │ (CCC+Haydock) │
└───────────────┘           └───────────────┘           └───────────────┘
        │                           │                           │
        │                    ┌──────┴──────┐             ┌──────┴──────┐
        │                    │             │             │             │
        ▼                    ▼             ▼             ▼             ▼
┌───────────────┐    ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│  73 books     │    │    TSK    │ │  Haydock  │ │    CCC    │ │  Haydock  │
│  complete     │    │ Protestant│ │ Catholic  │ │ Magisterial│ │ Patristic │
│  canon        │    │ scholarly │ │ patristic │ │ authority │ │ tradition │
└───────────────┘    └───────────┘ └───────────┘ └───────────┘ └───────────┘
```

### Cross-References: Protestant + Catholic Traditions

TSK and Haydock together provide broader coverage than either alone:

| Aspect | TSK | Haydock |
|--------|-----|---------|
| Volume | ~500,000 refs | ~80,000 refs |
| Canon | 66 books | 73 books |
| Methodology | Word matching | Theological connection |
| Tradition | Protestant scholarly | Catholic patristic |
| Quality signal | Crowdsourced votes | Single authoritative source |

When both sources attest to a connection, confidence increases. When they diverge, each brings distinct value.

### Typology: Magisterial + Patristic Sources

CCC and Haydock serve different roles in typology:

| Aspect | CCC | Haydock |
|--------|-----|---------|
| Authority | Magisterial | Patristic tradition |
| Coverage | Selective (~25 types) | Comprehensive |
| Role | Seed types, framework | Extensive extraction |
| Confidence | Highest | Requires review |

CCC-identified types are canonical; Haydock extraction extends coverage while maintaining theological consistency.

---

## The Review Process

### Why Human Review Matters

LLM extraction from Haydock commentary identifies potential typological connections, but requires human review because:

1. **Theological nuance**: Distinguishing genuine typology from allegory, moral application, or loose parallelism
2. **Contextual judgment**: Some commentary mentions types without endorsing them
3. **Quality control**: LLMs can hallucinate or misparse complex theological language

### The Review Workflow

```
Haydock Commentary → LLM Extraction → Human Review → Approved Types
        ↑                                    ↓
        └────── CCC Seed Types (guidance) ───┘
```

1. **Extraction**: LLM identifies potential types from Haydock commentary
2. **Review**: Human reviewers assess each candidate
3. **Approval**: Confirmed types enter the graph with `review_status: approved`
4. **Rejection**: False positives are marked `review_status: rejected`

This preserves LLM efficiency while ensuring theological accuracy.

---

## Conclusion

LogosGraph's data sources represent a pragmatic synthesis:

- **CPDV** provides complete canonical coverage
- **TSK** provides volume and broad cross-referencing
- **Haydock** provides Catholic tradition and typological insight
- **CCC** provides Magisterial grounding

Each source has limitations; together they enable a graph that no single source could provide. The attribution system preserves transparency about where each connection originates, allowing users to filter and weight according to their needs.

See also:
- [Data Sources](data-sources.md) - Technical details on each source
- [Theological Concepts](theological-concepts.md) - What typology is, the Catholic canon, and Magisterial interpretation
