# Phase 3 extraction prompt (per batch)

You are extracting **product data** from the Pentair Pool Product Catalog 2025-2026 for a database
that must let a person find a replacement part, choose a filter or pump for their pool, and do
anything they would otherwise use the catalog for. Repo: /home/user/product-namer.

Read first: `docs/data-v3-plan.md`, `docs/data-v3-attributes.md`, and this batch file
`data/work/pentair/d3/batches/{BATCH}.json`. Write `data/work/pentair/d3/out/{BATCH}.json`, then run
`python3 scripts/d3_check.py {BATCH}` and fix every error it reports. Don't commit.

## Rules
- **Manufacturer data only, nothing guessed.** Every record cites its `page`. If you can't read a
  value, leave it out and add an `issues` entry.
- **Look at every page image** (`image` path, Read tool) as well as the packet text. The layout
  carries meaning the text loses: which band a row sits under, which column a value is in, which
  diagram a parts list belongs to, footnote marks, colour columns, "not shown" sections.
- **SKUs**: use the MPNs listed in the batch file (`skus` per page). Attach data only to those. An
  MPN marked `excluded` gets no data. If a page prints a part number that isn't listed, add an
  `issues` entry instead of creating it.
- **Units**: convert to the unit in `docs/data-v3-attributes.md` (inches, lb, gpm, hp, BTU/h…).
  Keep the printed text in `raw`. Fractions become decimals in `value` ("2-1/2" → 2.5).
- **Prices**: the catalog's "US List" and "Can. List" columns (sometimes headed "US"/"Can."). Copy
  the numbers exactly; "CALL" or blank → omit and set `"price_note": "CALL"`.
- **Families**: one per product line or series a page is about (heading/subtitle/band), with
  `parent` pointing to a broader family when the page shows one, and `category` as the catalog
  path (side tab › heading). Put the page's descriptive paragraph in `description` and bullet
  points in `features`, word for word. Give each family a stable `id` (lowercase, hyphens, from
  the printed name: `intellipro3-vsf`). Reuse ids that earlier batches would also produce.
- **Fitment** (parts pages): for every part row, record what it fits: the family/models the parts
  list is for (heading, band, model columns), the diagram `item` number, `qty` per unit when
  printed (Qty column, "2 req.", "(X4)"), and any `condition` (build date, HP, model range,
  colour column, "not shown"). One fitment record per part per parts list; a part on three lists
  gets three records.
- **Reference tables** (sizing charts, engineering data, flow tables, pump curves printed as
  tables, conversion tables): copy the table with its title, column headers and rows. Charts drawn
  only as graphs: add `{"kind": "chart", "title", "page", "summary"}` with what the chart shows;
  don't read values off a curve.
- **Specs**: everything a column, bracket, footnote or band says about a SKU (see the attribute
  list). Whole goods get their full ordering-table row. Parts get size, material, colour, thread,
  etc. when printed.

## Output shape
```json
{
 "batch": "d063",
 "families": [{"id", "name", "brand", "parent", "category", "page", "description", "features": []}],
 "products": [{"mpn", "page", "family", "role": "model|part|kit|accessory|replacement",
               "specs": [{"attr", "value", "unit", "raw"}],
               "prices": {"us_list": 0.0, "can_list": 0.0} , "price_note": ""}],
 "fitment": [{"part", "page", "fits": {"family", "models": [], "mpns": []},
              "item": "", "qty": 0, "condition": "", "raw": ""}],
 "references": [{"page", "kind": "table|chart", "title", "columns": [], "rows": [[]], "summary": ""}],
 "issues": [{"page", "mpn": "", "question": ""}]
}
```
A product may appear on several pages: give one `products` entry per page it appears on (the
loader merges them). Report briefly when done: counts per record type, issues, and anything about
the rules that didn't fit what the pages show.
