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
2. Brand: apply the Brand rules. Pentair is the default; parts and accessories are always
   Pentair; Sta-Rite only for whole goods of the Sta-Rite families listed in the rules (or with
   the STA-RITE logo); Pleatco for Pleatco products.
   Product family names: use Pentair's mixed-case trademark spelling (look for it in the body
   text, photo captions or the directory pages 4–7), never the all-caps heading.
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
  "page_type": "whole_goods | parts | cross_reference | pleatco_measurement | discontinued_list | directory | other",
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
      "fits": "",
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
`fits` holds compatibility text (Pleatco cross-reference descriptions) that is kept out of the title.
`source_row` is the row as printed (all cells, ` | ` separated), so a human can audit the title.
Pages without SKUs (covers, section dividers, engineering data) still get a file with
`records: []` and any tokens dismissed.

## Page types
- `whole_goods`: ordering-information pages (equipment, plus its accessories table).
- `parts`: replacement-parts pages (exploded diagram + parts list).
- `cross_reference`: tables mapping our SKUs to other makers' numbers (e.g. Pleatco Advanced/Ultra
  lists, conversion charts). Only our SKU column becomes records.
- `pleatco_measurement`: "Filter Cartridges by Measurement". Write the full Pleatco title with
  sq ft and dimensions: `Pleatco PCC60 - Advanced Filter Cartridge 60 sq ft 7 in x 19-3/4 in`
  (fractions as printed, `7"` → `7 in`, `19 3/4"` → `19-3/4 in`). This is the preferred title
  source for Pleatco, so be exact.
- `discontinued_list`: lists of discontinued numbers. Every SKU listed as discontinued gets
  status `discontinued` and its replacement in `replaced_by`.
- `directory`, `other`: no sellable rows; usually `records: []`.

Consolidation picks each SKU's title from the best page type, so a SKU seen on many pages
must still get a correct title on every page.
