# Pentair catalog: SKU and title rules

Source: Pentair Pool Product Catalog 2025–2026 (digital edition, updated December 2025),
`pentair-catalog-2025-2026-digital-1-compressed.pdf`, 540 PDF pages.
Printed page number = PDF page − 2.

Status: **DRAFT.** Rules marked *(proposed)* are awaiting Matthew's decision.

## Title format

```
{Brand} {MPN} - {Derived title}
```

Reference example (from Matthew), printed page 269:
`Pentair 263056 - FULLFLOXF® 3-Way CPVC 2.5 in Diverter`

| Part | Where it comes from on the page |
|---|---|
| `Pentair` | brand of the product family (see Brand) |
| `263056` | Product column, exactly as printed |
| `FULLFLOXF®` | page heading, product line name as printed (caps, ® kept) |
| `3-Way CPVC 2.5 in` | Description column; parenthetical "(3 in. slip outside)" dropped; "in." → "in" |
| `Diverter` | black band "2-WAY AND 3-WAY DIVERTER VALVES" → the product noun |

## Brand
1. Sta-Rite when the product family is marked ° (circle) in the Whole Goods Directory
   (PDF pp. 4–5) or the page carries the STA-RITE logo. Pentair when marked • (dot).
2. Pleatco for everything in the Pleatco section (cartridges, grids, cleaners), even though the
   directory marks it •.
3. Families marked both • and ° (e.g. D.E. Separation Tank 100): use the logo on the page; if
   none, flag for review.
4. *(proposed)* Accessories and replacement parts take the brand of the product family whose
   page they are on. A SKU that appears under two brands is flagged, not guessed.

## MPN
- Exactly as printed in the SKU column (Product / Part No. / Item #), character for character,
  including suffix letters (`354545SS`, `6020018Z`) and suffixes such as `-INT`.
- Remove only footnote markers (`*`, `¹`, `†`), and record what they meant (e.g. discontinued).
- Must exist exactly in the page's text layer. Numbers read only from the image are never accepted.
- Never take numbers from cross-reference columns (Mfr #, Unicel, Filbur, competitor or OEM
  numbers). Those are other companies' SKUs.

## Derived title
Built only from words printed on the page, in this order:

1. **Product line**: the line name from the page heading, as printed (capitals, ®/™ kept):
   `FULLFLOXF®`, `SUPERMAX®`, `INTELLIBRITE®`. Leave out generic heading words that the noun
   repeats ("DIVERTER & CHECK VALVES"), sizes covered by the row, and "(CONT'D)".
2. **What makes this SKU different from its siblings**: the Description column. When there is no
   description column, the distinguishing columns (HP, voltage, wattage, size, color, model)
   and the band text. In grid tables, the column header that the SKU sits under
   (e.g. cord length "50 ft Cord").
3. **Product noun** in singular: Diverter, Pump, Pool Light, Filter, Heater, Cartridge.
   Taken from the band, subtitle or heading.

Clean-up:
- Drop secondary-spec parentheticals: "(3 in. slip outside)".
- Drop assembly quantities and diagram references from parts lists: "(Qty. 2)",
  "(Includes Items 24-26)", item numbers. These describe the drawing, not the SKU.
- Keep pack sizes that define the SKU: "(Set of 4)" → "Set of 4".
- Units: "in." → "in", "ft." → "ft", "′"/"'" (feet) → "ft"; keep HP, V, W, GPM as printed.
- Keep only the name part of a description followed by a sales sentence:
  "XF Riser Base - Simplifies installation…" → "XF Riser Base".
- No words that are not on the page, apart from unit clean-up and making the noun singular.

## Replacement parts *(proposed)*
`{Brand} {MPN} - {LINE} {Model} {Part}`, with the parent product from the page heading and
"Replacement Parts for Product #…" line. Pentair's "Noun, Qualifier" wording is put in natural
order: "O-Ring, Lid" → "Lid O-Ring".
Example: `Pentair 350091Z - SUPERFLO® DOE Pump Lid`.

## Status flags (stored as fields, not in the title)
- `discontinued`: `*` "Indicates discontinued item" (Pleatco) and similar notes; keep the
  replacement SKU (ULTRA Replacement column) in `replaced_by`.
- `not_for_sale_usa`: band says "NOT FOR SALE IN THE USA".
- `call_for_price`: not tracked (pricing is out of scope).

## Same SKU on several pages
One record per MPN. Title source priority: the product's own whole-goods ordering table,
then an accessories table, then a parts list. Every page it appears on is kept as evidence.
Conflicting titles or brands between pages are flagged for review.
