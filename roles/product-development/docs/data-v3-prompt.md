# Phase 3 extraction prompt (per batch)

You are extracting **product data** from the Pentair Pool Product Catalog 2025-2026 for a database
that must let a person find a replacement part, choose a filter or pump for their pool, and do
anything they would otherwise use the catalog for. Repo: /home/user/product-namer.

Read first: `docs/data-v3-plan.md`, `docs/data-v3-attributes.md`, and this batch file
`data/work/pentair/d3/batches/{BATCH}.json`. Write `data/work/pentair/d3/out/{BATCH}.json`, then run
`python3 scripts/d3_check.py {BATCH}` and fix every error it reports. Don't commit.
Other agents run at the same time: keep any helper scripts or scratch files in your own folder
`/tmp/claude-0/-home-user-product-namer/28224544-019c-5471-b0e0-39374ec9eedf/scratchpad/d3_{BATCH}/`,
never a shared name like `gen.py` in the scratchpad root.

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

## Lessons from the pilot (follow these)
- **issues are questions only**: something unreadable, contradictory or ambiguous that a person must
  settle. Don't file notes like "no prices on this page" or "stored as printed".
- **No guessing what an unlabelled number means.** A number in a column with no header, or a
  footnote digit that could be a qty or a mark: keep it in `raw`, add one issue.
- **Parts lists**: what a column or cell says about *which pump* (1.5 HP, 3.0 HP, build date,
  model) is a fitment `condition`, not a spec of the part. A `color` spec only when the part sits
  in a single colour column (Almond, Black); a number spanning both colour columns gets no colour.
- A parts list covering several pumps: `fits.family` may be a list of family ids.
- **Family links**: when a page prints "SEE PAGE N FOR REPLACEMENT PARTS" (or similar), add
  `"links": [{"kind": "replacement_parts", "printed_page": N}]` to the family.
- Whole goods: option text that sets a SKU apart (relay board, touchscreen) → `options`. Don't copy
  the description as a spec; the band text goes in `band` on the product, not a spec.
- Dimension drawings whose numbers aren't labelled: one `chart` reference with a summary, no table.
- **Logos count**: certification or program marks printed as logos for a product (UL, CSA, ETL,
  NSF, AHRI, Energy Star, TradeGrade) → `certification` / `program` specs on each SKU the logo covers,
  with `raw` like "logo: UL". Footnote digits are dropped from description/feature text.
- Printed notes and footnotes about a family (installation, GFCI, compatibility, "sold
  individually") go word for word in the family's `notes` list, not in `description`.
- A reference table or chart about a product line (sizing, dimensions, performance) names that
  line in `family` (an id or list of ids), even when the SKUs are printed on another page. Specs go
  on a SKU only when its own row is on a page of this batch.
- Skip page boilerplate: the California Prop 65 warning box, "see catalog page 23 for GFCI" and
  similar notices printed on every page are not data.
- Blank price cells: `"price_note": "blank"`.
- **Family ids are shared across batches.** Before inventing one, list existing ids with
  `grep -ho '"id": "[^"]*"' data/work/pentair/d3/out/*.json | sort -u` and reuse the id when it is
  the same product line (a parts page for IntelliFlo3 uses the whole-goods page's id when it fits).
- Check `docs/data-v3-attributes.md` before inventing an x_ key (hhp, case_pack, media_weight,
  upgrade, options, min/max_speed exist).

## Output shape
```json
{
 "batch": "d063",
 "families": [{"id", "name", "brand", "parent", "category", "page", "description", "features": [], "notes": [], "links": []}],
 "products": [{"mpn", "page", "family", "band", "role": "model|part|kit|accessory|replacement",
               "specs": [{"attr", "value", "unit", "raw"}],
               "prices": {"us_list": 0.0, "can_list": 0.0} , "price_note": ""}],
 "fitment": [{"part", "page", "fits": {"family", "models": [], "mpns": []},
              "item": "", "qty": 0, "condition": "", "raw": ""}],
 "references": [{"page", "kind": "table|chart", "family": "id or list", "title", "columns": [], "rows": [[]], "summary": ""}],
 "issues": [{"page", "mpn": "", "question": ""}]
}
```
A product may appear on several pages: give one `products` entry per page it appears on (the
loader merges them). Report briefly when done: counts per record type, issues, and anything about
the rules that didn't fit what the pages show.
