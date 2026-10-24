# Pentair catalog: SKU and title rules

Source: Pentair Pool Product Catalog 2025–2026 (digital edition, updated December 2025),
`pentair-catalog-2025-2026-digital-1-compressed.pdf`, 540 PDF pages
(sha256 in `data/work/pentair/SOURCE_SHA256`). Printed page number = PDF page − 2.

Decisions from Matthew are marked **[decided]**.

## Title format

```
{Brand} {MPN} - {Derived title}
```

Reference example (Matthew, printed page 269, case adjusted per the casing decision):
`Pentair 263056 - FullFloXF® 3-Way CPVC 2.5 in Diverter`

| Part | Where it comes from on the page |
|---|---|
| `Pentair` | brand (see Brand) |
| `263056` | Product column, exactly as printed |
| `FullFloXF®` | product family from the page heading, spelled the way Pentair writes the trademark in running text |
| `3-Way CPVC 2.5 in` | Description column; words in parentheses dropped; "in." → "in" |
| `Diverter` | black band "2-WAY AND 3-WAY DIVERTER VALVES" → the product noun |

## Brand [decided]
Pentair is the default brand. Only one brand per SKU.
1. **Whole goods** take Sta-Rite only when the product family is marked ° (circle) in the
   Whole Goods Directory (PDF pp. 4–5) or the page carries the STA-RITE logo.
   Sta-Rite families: System:2™, System:3™ (modular media and D.E.), Cristal-Flo™ II,
   Max-E-Therm®, IntelliPro®, IntelliPro3®, Max-E-ProXF®, SuperMax®, U-3 SwimQuip,
   CSP/5CSP Series, Hair and Lint Strainers. Families marked both (D.E. Separation Tank 100)
   → Pentair.
2. **Pleatco** for Pleatco products (cartridges, grids, Filter Wash, PureStart).
3. **Replacement parts and accessories are always Pentair**, whichever page they are on.
4. Everything else is Pentair.

## MPN
- Exactly as printed in the SKU column (Product / Part No. / Item # / "Product Number By …"),
  character for character, including suffix letters (`354545SS`, `6020018Z`).
- Part numbers printed with a space ("PKG 188Z", "SD 35") are recorded exactly as printed, space
  included; the validator accepts them when the words appear consecutively on the page.
- Remove only footnote markers (`*`, `¹`, `†`) and record what they meant.
- Must exist exactly in the page's text layer. Numbers read only from the image are never accepted.
- Never take numbers from cross-reference columns (Mfr #, Unicel, Filbur, competitor or OEM
  numbers). Those are other companies' SKUs.

## Derived title
Built only from words printed in the catalog, in this order:

1. **Product family**: from the page heading, but spelled the way Pentair writes the trademark in
   mixed case (body text, photo caption, or directory): `SuperFlo®`, `FullFloXF®`,
   `IntelliBrite®`, `SuperMax®`, `IntelliFloXF®`. Never the all-caps heading form. Keep ®/™ where
   Pentair prints them on the name. Leave out generic heading words the noun repeats
   ("DIVERTER & CHECK VALVES"), sizes covered by the row, and "(CONT'D)".
   **Accessories get no product-family prefix [decided]** (they are often shared across lines):
   `Pentair 356904Z - Keypad Relocation Kit`.
   If the printed description itself names the product it fits ("ETi 250 Propane Conversion
   Kit"), keep that name — it is description, not a prefix. For model-specific accessories whose
   description does not name the product, append "for {Family}" from the page heading
   (`Propane Gas Conversion Kit for ETi® 400`), so it cannot be confused with other heaters' kits.
   An item in an ordering table that repairs or replaces part of *that* product (rebuild kit,
   replacement cartridge, motor) is `kind: part` and keeps the family:
   `Pentair 270119Z - FullFloXF® Check Valve Rebuild Kit`. Add-ons used alongside the product
   (cables, risers, elbows, keypad kits) are `kind: accessory`, no family.
2. **What makes this SKU what it is**: the Description column, ignoring words in parentheses
   [decided]. Exception: when the parenthetical is the *only* difference between two sibling SKUs
   on the page (e.g. "short thread" / "long thread"), keep those words without the brackets.
   When there is no description column, use the band text and the distinguishing columns.
   In grid tables, include the column header the SKU sits under (e.g. "50 ft Cord").
3. **Specs only when needed to tell siblings apart [decided]**: add HP, voltage, size, wattage,
   cord length etc. only if, without them, two SKUs would get the same title. A page with one
   pump gets no specs. Voltage: as printed plus "V" (`115/208-230V`).
4. **Product noun** in singular, Title Case: Diverter, Pump, Pool Light, Filter, Heater.
   **Order: family, then description words and any added specs, then the noun last**,
   with three allowed exceptions that keep Pentair's wording natural:
   - a printed "with …" or "for …" qualifier may follow the noun
     (`THS Single Tank Manifold Kit with Butterfly Valves`, `Free Standing Base for Dynamic Filter Series II and III`);
   - a variant footnote ("* with 2 in. valve") becomes "with 2 in Valve" after the noun;
   - a parenthetical that is the only sibling difference follows after a comma (`…, Long Thread`).
   (`IntelliBrite® Architectural Series Color 12V 50 ft Cord Pool Light`). Only a pack size
   follows the noun (`…, Set of 4`). Dimensions use lowercase "x": `7 in x 14-1/8 in`.

Clean-up:
- Drop assembly quantities and diagram references from parts lists: "(Qty. 2)",
  "(Includes Items 24-26)", item numbers. They describe the drawing, not the SKU.
- Pack sizes that define the SKU go at the end: "…, Set of 4" (also when only the `-PAK4`
  suffix and pack-specific cross numbers show it is a 4-pack; mark confidence "review").
- Units: "in." / `"` / `”` → "in"; "ft." / `'` / `′` (feet) → "ft"; keep HP, V, W, GPM as printed.
- Keep only the name part of a description followed by a sales sentence or note:
  "XF Riser Base - Simplifies installation…" → "XF Riser Base"; "… - includes 2" → drop.
- Abbreviations: expand only when the page itself spells the word out nearby (band, heading,
  sibling row): "Comp" → "Complete" when the band prints COMPLETE; BLK → Black, WHT → White.
  Ambiguous ones (GRY: Gray or Dark Gray?) stay as printed with confidence "review".
- Obvious catalog typos ("Cryatal") are corrected only when the correct spelling is printed for
  the same item elsewhere on the page; note it.
- Title Case for description words printed in lower case too ("3-way solar drain down valve" →
  "3-Way Solar Drain Down Valve"); keep units and acronyms as in the rules (in, ft, V, GPM, GFCI).
- When a row has a Model column and no description, the model goes in the title.
- Columns in thousands ("BTU (000's)") give a model size, not a unit: `MasterTemp® 250 … Heater`,
  never "250 BTU".
- Codes that are not orderable as printed (templates needing an option letter, e.g. Stark
  "5S1-30-06" vs "5S3-50A-10") are recorded with confidence "review" and a note.
- Pleatco cartridges, grids and cleaners are `kind: part`.
- Pleatco Advanced numbers listed in an "Upgrade For" column of the Ultra tables are dismissed
  with reason `other` ("Pleatco SKU, recorded on its own page"); the Ultra number is the row's SKU.
- Title Case for words taken from all-caps bands ("DOE COMPLIANT SINGLE-SPEED TEFC" →
  "DOE Compliant Single-Speed TEFC"; keep acronyms upper case).
- Titles must be unique: no two SKUs may end up with the same derived title.

## Replacement parts [decided]
`Pentair {MPN} - {Family} {Model} {Part}`, with the parent product from the page heading and
the "Replacement Parts for Product #…" line. Pentair's "Noun, Qualifier" wording is put in
natural order: "O-Ring, Lid" → "Lid O-Ring".
Examples: `Pentair 357255 - SuperFlo® DOE Pump Lid O-Ring` ("O-Ring, Lid");
`Pentair 350091Z - SuperFlo® DOE Pump Lid` ("Lid").
Parts are always brand Pentair, even on Sta-Rite product pages.
A part number listed under more than one product family (e.g. 230010Z under Low Profile and
Top Feed; QuikSkim and QuikSkim Ultra parts pages) gets **no family** in its title; keep the
printed part description only. Kit letters ("Kit (A)", "Kit D") are kept without brackets
when they are the only difference between sibling kits.

## Pleatco cartridges [decided: short, no fit list]
`Pleatco {MPN} - {Line} Filter Cartridge {sq ft} sq ft {diameter} x {length}`, e.g.
`Pleatco PCC60 - Advanced Filter Cartridge 60 sq ft 7 in x 14-1/8 in` (line: Ultra / Advanced;
the "PLEATCO" in the heading is not repeated). On the cross-reference pages, page reviews write
the provisional title `Pleatco {MPN} - {Line} Filter Cartridge` (plus ", Set of 4" for packs) and
put the compatibility text in `fits`; consolidation takes the final title from the measurement
page. Packs: per-cartridge sq ft (the single SKU's figure) and ", Set of 4" at the end, e.g.
`Pleatco PCC60-PAK4 - Advanced Filter Cartridge 60 sq ft 7 in x 14-1/8 in, Set of 4`.
Ultra rows print "Optimized" instead of sq ft: leave sq ft out
(`Pleatco ULTRA-A4 - Ultra Filter Cartridge 7 in x 14-1/8 in`). Where two SKUs still share a
title, append ", Upgrade for {SKU}" from the row's "Upgrade for" text and mark confidence
"review". The `*` (discontinued) legend printed on pp. 34–37 applies to the whole Pleatco
section. Suffixes like P4 / -P4 / -IN-4 are NOT assumed to be packs unless the page says so. The compatibility list goes in the `fits` field, not
the title. Dimensions come from "Filter Cartridges by Measurement" (PDF pp. 38–42) and are
added at consolidation, because the cross-reference page itself has no distinguishing words.

## Status and scope [decided]
- USA only: SKUs under a "NOT FOR SALE IN THE USA" band (and `-INT` models on those rows) are
  recorded with status `not_for_sale_usa` and **excluded from the export**.
- Discontinued (`*` "Indicates discontinued item" and similar) → status `discontinued`,
  replacement SKU in `replaced_by`; **kept in the database, excluded from the export**.

## Pages whose titles are provisional
On `cross_reference` and `discontinued_list` pages titles may repeat (validator allows it), and on
`discontinued_list` pages, which print no descriptive words, write `"title": ""`. These pages
are for status, replacement and fit; the title comes from the SKU's ordering or measurement page.

## Same SKU on several pages
One record per MPN. Title source priority: the product's own whole-goods ordering table,
then an accessories table, then a parts list. Every page it appears on is kept as evidence.
Conflicting titles between pages are flagged for review.
