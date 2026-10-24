# Page review procedure (catalog PDFs)

You turn one catalog page into SKU records. Precision matters more than speed: a wrong SKU or
a misleading title costs more than a flagged one.

## Inputs per page
- `data/work/pentair/packets/pNNN.json`: heading, subtitle, side tab, black band headers, text
  lines with the band each sits under, notes ("Replacement Parts for Product #…",
  "SEE PAGE …"), and `candidate_tokens`, every SKU-shaped token in the text layer.
- The page image named in the packet (`image`). **Always look at the image.** The layout
  (columns, grid headers, bands, logos, asterisks, which column is which) is only reliable there.
- Rules: `docs/pentair-title-rules.md` (title format, brand, MPN, clean-up, status). Follow it.

## Steps
1. Look at the image. Identify every table, its column headers and its bands. Note which
   column holds this company's SKUs (Product / Part No. / Item # / "Product Number By …")
   and which columns are cross-references to other companies.
2. Brand: apply the rules (STA-RITE logo on page → Sta-Rite; Pleatco section → Pleatco; else
   Pentair unless the Whole Goods Directory marks the family Sta-Rite °. Sta-Rite families:
   System:2, System:3, Cristal-Flo II, Max-E-Therm, IntelliPro, IntelliPro3, Max-E-ProXF,
   SuperMax, U-3 SwimQuip, CSP/5CSP Series, Hair and Lint Strainers; the D.E. Separation
   Tank 100 is marked both.)
3. For each SKU cell, write a record. Copy the MPN from the packet's text tokens (exact
   characters), not from your reading of the image. Build the title per the rules.
4. Every token in `candidate_tokens` must end up as a record or in `dismissed` with a reason.
5. Write `data/work/pentair/<review dir>/pNNN.json` and run
   `REVIEW_DIR=<review dir> python3 scripts/catalog_pages.py validate NNN`. Fix until OK.
   Never change the scripts or rules files to make validation pass.
6. If something is genuinely ambiguous, still write your best record, set
   `"confidence": "review"` and explain in `notes`. Do not guess silently.

## Output format
```json
{
  "page": 271,
  "printed_page": "269",
  "page_type": "whole_goods | parts | cross_reference | directory | other",
  "records": [
    {
      "mpn": "263056",
      "brand": "Pentair",
      "title": "Pentair 263056 - FULLFLOXF® 3-Way CPVC 2.5 in Diverter",
      "kind": "whole_good | accessory | part",
      "status": "active | discontinued | not_for_sale_usa",
      "replaced_by": "",
      "product_line": "FULLFLOXF®",
      "parent_product": "",
      "source_row": "263056 | 3-Way CPVC 2.5 in. (3 in. slip outside) | 1 | 4",
      "context": "heading: FULLFLOXF® DIVERTER & CHECK VALVES 2-1/2 IN. & 3 IN.; band: 2-WAY AND 3-WAY DIVERTER VALVES",
      "confidence": "high | review",
      "notes": ""
    }
  ],
  "dismissed": [
    {"token": "C-7469", "reason": "cross_reference", "note": "Unicel column"}
  ]
}
```
`source_row` is the row as printed (all cells, ` | ` separated), so a human can audit the title.
Pages without SKUs (covers, section dividers, engineering data) still get a file with
`records: []` and any tokens dismissed.
