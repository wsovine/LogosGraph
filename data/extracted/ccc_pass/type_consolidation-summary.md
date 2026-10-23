# Type consolidation summary: Catechism typology pass

**2026-10-20** · decisions in `type_decisions.jsonl` · `reconcile_ccc_typology.py --check-decisions`: 26 decisions, 0 errors

## Counts

| action | decisions | ledger entries covered |
|---|---|---|
| `new` | 22 | 26 new-Type groups (4 pairs of duplicate proposals joined) |
| `broaden` | 4 | 2 existing Types + 3 new-Type groups absorbed into existing Types |
| `use_existing` / `rename` / `merge` / `reject` | 0 | — |
| **total** | **26** | **31** (29 groups + 2 existing Types) |

The 29 proposed groups produce 22 new Types (catalog 198 → 220). Three proposals did not need a new node: the Sinai cloud and
the Temple cloud now fall under `cloud-in-desert`, and the Old Covenant falls under `the-mosaic-law`. Four pairs of duplicate
proposals were joined: creation (2→1), Sabbath (2→1), the marriage covenant (2→1) and Carmel (2→1).

There are no `use_existing` decisions because in every case the nearest catalog Type either names a different figure, or has to
be broadened before the rows read true. There are no `reject` decisions because every proposed figure turned out to be a real
one. Whether each *row* stands is a question for verification. Two Types depend only on weak rows and land only if a row
survives: Confirmation (two synthesized rows) and the Creation rows from §759/§778 (low confidence).

**New Types.** OT: `abraham`, `abrahams-hospitality-at-mamre`, `the-creation-of-the-world`, `the-spirit-over-the-waters`,
`the-sabbath`, `the-daughter-of-zion`, `gods-marriage-covenant-with-israel`, `wisdom-personified`, `eve-formed-from-adams-side`,
`elijahs-sacrifice-on-mount-carmel`, `the-lord-passing-by-at-horeb`, `the-mercy-seat`, `ot-laying-on-of-hands`,
`the-seventy-elders`. NT: `the-new-creation-in-christ`, `the-lords-day`, `the-annunciation`, `the-baptism-of-jesus`,
`the-temptation-in-the-desert`, `the-transfiguration`, `confirmation`, `matrimony`.

**Broadened (ids kept).** `israel-jeshurun` → *Israel, the Chosen People* · `the-twelve-patriarchs` → *The Twelve Patriarchs
and Tribes of Israel* · `cloud-in-desert` → *The Cloud of the Lord's Glory* · `the-mosaic-law` → *The Law of Moses (Old
Covenant)*. The link test passed for all 10 current links on these four Types; each one is listed in `affected_links`.

## Hardest calls

1. **The cloud (§697): one Type, not three.** The proposals made the Sinai cloud and the Temple cloud new Types beside the
   wilderness pillar. §697 speaks of "the cloud" as one image in several theophanies, and its own footnotes join the desert cloud
   (1 Cor 10:1-2; Exod 40:36), Sinai (Exod 24:15-18) and the tent (Exod 33:9-10). 1 Kgs 8:10-11 also repeats Exod 40:34-35 word for word.
   Broadening `cloud-in-desert` keeps all three of its links true (→ Baptism rests on 1 Cor 10:2, which §697 itself cites). As
   a result, the two §697 rows duplicate the existing bucket-A row `c697:cloud-in-desert>christ` and should be folded into it at
   review. *If you prefer separate nodes* (for a future Sinai cloud → Transfiguration pair), the rejected alternative is
   recorded in td-003.
2. **The Old Covenant (§§759, 778, 781): broaden the Law, don't twin it.** A new "Old Covenant" Type would sit beside "The
   Mosaic Law", and both would point at "The Gospel (New Covenant)". Scripture and the Catechism bind the covenant and the Law
   together: Exod 24:7-8, Gal 4:24, 2 Cor 3:14; "the covenant of Mount Sinai and, through Moses, ... his law" (§62); "the gift of
   the commandments and of the Law is part of the covenant" (§2060). Haydock already uses this Type for "that covenant of the
   former law delivered on Mount Sina" (`ishmael →`). The new name mirrors its antitype exactly: *The Law of Moses (Old
   Covenant)* ↔ *The Gospel (New Covenant)*. `ceremonial-law` and `dietary-laws` stay as narrower Types.
3. **Israel (§§60, 751, 753, 759, 762, 781).** `israel-jeshurun` becomes *Israel, the Chosen People* (the Catechism's words).
   Jeshurun moves into the description, since it is only a poetic name for Israel (Isa 44:2). Both Haydock links still read
   true. I did **not** fold the Synagogue Types into it: no proposal touches them, and they need your own decision (see suggestion 1).
4. **The Sabbath (§§314, 345-349, 2002, 2169-2176, 2190): God's rest and Israel's day are one Type.** Usually an event and an
   institution are kept apart, but here Scripture grounds the commandment in God's rest (Exod 20:11), Heb 4:4-10 reads them as
   one figure, and the Catechism uses "sabbath" for both. The description is neutral; the "replaced" wording of §2175/§2190 stays
   in the quotes and is not put on the node.
5. **Creation (§§280, 315, 349, 759, 778, 1218, 1224).** "First Creation" and "Creation of the World" are one Type. *The
   Spirit over the Waters* stays separate, because the Easter Vigil (§1218) and §1224 single out Gen 1:2 as a figure of Baptism,
   just as the catalog separates the flood from the ark. *The New Creation in Christ* is new: it is neither the Resurrection,
   which begins it (§349), nor heaven.
6. **Abraham vs Mamre (§762, §2571): two Types.** Abraham, father of a great people → the Church, is a figure at the level of the
   person. §2571 makes *the hospitality at Mamre* the figure of the Annunciation, event to event. This follows the catalog's
   `isaac` / `binding-of-isaac` precedent.
7. **Kept separate on purpose:** *Daughter of Zion* vs Israel ("Israel → Mary" would not read true; §2676 has "daughter of Zion in
   person"). *Eve Formed from Adam's Side* vs *Marriage of Adam and Eve* (the Church born from the pierced side, §766, vs the
   spousal union). *God's Marriage Covenant with Israel* vs the Canticle spouse (§1611 names them as separate witnesses).
   *Elijah's Sacrifice on Mount Carmel* vs `elijah` (that Type's → Eucharist link rests on the bread of 1 Kgs 19:8, not
   Carmel). *The Mercy Seat* vs the Ark (§433: the hilasterion of Rom 3:25, not the dwelling).

## Held rows that share a name (rule 6)

These resolve automatically, because they have the same group key: *The Baptism of Jesus* (§§536, 556), *The Transfiguration*
(§556), *The Lord's Day* (§2175 → eternal life), and *Matrimony* (§§1617, 1659, 1661). **One needs a manual mapping later:**
§2384 "Matrimony (Sacramental Marriage)" → `matrimony`. *The Promise to Abraham* (§§422, 706) is an oracle, which is a different
claim from the patriarch, so it was left unaligned.

## catalog_suggestions (not acted on)

1. **Synagogue Types: sensitive, decide as one item.** `the-synagogue-old-covenant-assembly` is described by its rejection of the
   Messiah, and its only note (Augustine on Ps 21) makes a collective claim. Yet §751's "assembly of the Chosen People" at Sinai
   is Israel itself: give it a neutral description, or fold it into `israel-jeshurun`, whose → Church link already exists.
   `the-synagogue-as-preparation-for-the-church` is labeled NT but names an OT reality, so `deborah →` it reads OT → OT (batch 01,
   §60). Deborah already links to the Church, so this node could be retired. `the-synagogues-persecution-of-the-church` overlaps
   `persecutors-of-the-church`; its one link (`ishmael`) could move there and keep Paul's own words (Gal 4:29).
2. **Exile and Jerusalem.** `the-babylonian-exile`'s description carries a collective claim ("the long desolation the Jews
   endured after rejecting Christ"). Suggested: "The deportation of Judah to Babylon after the fall of Jerusalem (2 Kgs 25; Ps 137)".
   `destruction-of-jerusalem-as-divine-judgment` has no description and its name states a verdict. Suggested: *The Destruction of
   Jerusalem*, with Luke 19:41-44; 21:20-24.
3. **`heaven` vs `eternal-life`:** near-duplicates. Merge them, or define them apart (God's dwelling vs the inheritance). This
   ties in with the queued §1222 fix (`the-promised-land → eternal-life`, while `the-promised-land → heaven` already exists).
4. **Temple and Tabernacle family:** `the-temple-of-jerusalem`, `the-rebuilt-temple`, `the-tabernacle-gods-dwelling-place`,
   `the-holy-of-holies`, `the-veil-of-the-tabernacle`, `the-altar-of-incense`, `the-golden-candlestick-menorah`,
   `the-table-of-showbread-bread-of-the-presence`, `the-ark-of-the-covenant`, `cherubim-of-the-ark` (and now `the-mercy-seat`).
   The Tabernacle and the Temple share the same antitypes; four Types lack descriptions; the tabernacle → destruction-of-Jerusalem link is filed Ecclesial.
5. **`the-one-true-church` → *The Church*.** This is the most-linked NT node and has no description; "One True" reads as an
   apologetic label rather than a plain name.
6. **`christ-church`** ("Christ's union with the Church": no description, odd casing) → *Christ and the Church (Bridegroom and
   Bride)*, Eph 5:25-32.
7. **No Holy Spirit NT Type.** `the-holy-spirit-as-divine-guide` is narrow, yet §§694-701 make water, fire, cloud and dove all
   figures of the Spirit, and the Carmel row had to settle for Pentecost. Consider broadening it to *The Holy Spirit*.
8. **45 Types have no description,** among them `david`, `elijah`, `elisha`, `samson`, `adam-and-eve`, `antichrist`, and
   `anointing-of-kings-priests-and-prophets` (which gains Confirmation).
9. **Category oddities:** `cloud-in-desert → the-holy-spirit-as-divine-guide` (Christological), `moses → christs-passion`
   (Covenantal), `goliath → christs-victory` (Ecclesial), `the-foolish-shepherd → persecutors-of-the-church` (Eschatological).
