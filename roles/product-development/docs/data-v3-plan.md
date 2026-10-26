# Phase 3: product data (Pentair catalog)

Goal (Matthew, 2026-10-26): attach every piece of data the catalog prints about a SKU to that SKU,
so a person can find the part they need for a pump, pick a filter for their equipment and pool
size, and do anything they now use the catalog for. Same rules as before: manufacturer data only,
evidence on everything, nothing guessed.

## What gets captured

| Record | What | Example |
|---|---|---|
| **family** | A product line or series, with its place in the catalog tree, description and feature bullets | IntelliPro3® VSF, under Pumps › Inground › Variable speed |
| **spec** | One attribute of one SKU, from an ordering table column, a bracket, a footnote or a band | 013075 thp = 3 hp; port_size = 2 in x 2 in or 2.5 in x 2.5 in |
| **price** | US and Canadian list price as printed (Dec 2025 edition) | 013075 us_list 2,341.00 |
| **membership** | Which family a SKU belongs to and its role (model, kit, part, accessory) | 013075 is a model of IntelliPro3® VSF |
| **fitment** | Which products a part fits, with diagram item number, quantity per unit, and conditions (build date, size, colour, HP) | 071131Z fits IntelliFlo3®/IntelliPro3® VSF, item 35, 2 per pump, almond |
| **reference table** | Selection and engineering tables that aren't about one SKU (sizing, pump curves as tables, turnover) | Filter sizing by pool gallons |
| **issue** | Anything unreadable or contradictory, for Matthew | |

Attributes use a controlled list (`docs/data-v3-attributes.md`) with fixed units, so they can be
filtered and compared. A value the list doesn't cover is written with an `x_` key and reviewed.

## How

1. `scripts/d3_prep.py` cuts the 540 pages into batches of 3–5 pages in reading order (a parts
   section stays with its diagrams). Each batch carries the page packets (text lines with bands and
   bold headers), the page images, and the final title of every active SKU on those pages.
2. One extraction pass per batch by a **Sonnet** agent (cheaper than Opus; picked after a pilot
   that compares it with Haiku and with my own read of the same pages).
3. `scripts/d3_check.py` validates every batch: schema, known SKUs, attribute keys and units,
   numbers parse, every record cites a page.
4. Quality instead of double passes: an Opus agent re-reads a random sample of pages plus every
   page with issues or unknown attributes, and fixes the batch. Sampling error rates decide
   whether a section needs a full second pass.
5. `scripts/consolidate.py` loads it all into SQLite and Neon (`mfr_catalog`), with new tables
   `families`, `specs`, `prices`, `fitment`, `reference_tables`.
6. Questions go to Matthew on an artifact page, grouped, never as a list in chat.

## Decisions (Matthew, review page, 2026-10-26)
- Discontinued numbers that the catalog maps to a current replacement are stored as `replaces` on the
  ACTIVE replacement (chains followed to the active end). Discontinued SKUs themselves still get no data.
- Pleatco "Pack #" is a case count (`case_pack`).
- A lone digit under a Certifications column is that page's footnote mark (e.g. 1 = UL, 2 = NSF).
- Weights printed without a unit are pounds.
- Logos printed once per page go on the page's main products only.
- A part printed at different list prices: use the price printed on the most pages (`product_prices`);
  ties use the later page. Matthew then chose the price for 25 of the 26 (`d3/price_picks.json`). All page prices stay in `prices`.
- Next: gather data for the web-only SKUs from pentair.com (manufacturer data only).

## Data review (2026-10-26): what was normalized and why
Extraction was accurate but values were not comparable. `scripts/d3_normalize.py` now runs inside the loader:
- categorical values lower-cased and mapped through synonym tables (colour 49 -> 34 spellings, material 102 -> 76,
  surface 16 -> 6, pool type 34 -> 7, certification 23 -> 12, program 6 -> 4); lists split into one row per value
- sizes keep their printed text and get a number (`value_num`) for filtering; missing units filled from the key list
- 60 frequent `x_` keys promoted to the controlled list; `x_` rows fell from 19% to 8% of specs
- new query tables: `cross_references` (competitor number -> SKU), `replacements` (old number -> SKU; an old number
  that is still sold becomes an `upgrade` spec instead), `family_links` (family parent + parts-page links from
  `d3/family_links.json`, each with page evidence), `model_parts` (every product–part pair the catalog supports,
  found by walking the family links; 983 of 1,171 whole-goods SKUs reach their parts)
- parts lists for lines no longer in the catalog (dated headings, legacy pumps/cleaners) stay unlinked on purpose

## Media review (Matthew, 2026-10-26)
- Documents: keep our own copies of every PDF (all languages) in data/raw/pentair/docs/ (gitignored); the
  `documents` table keeps Pentair's URL and the local file.
- Photos: the line's main pentair.com image is the primary photo of every SKU in the line; gallery images are
  extra views. Parts use the catalog's exploded diagram as their picture for now ("we need to expand our web
  search for pictures" - manufacturer sources only, per the working rules).
- Discontinued lines whose parts are still sold: attach their manuals, parts sheets and photos to the parts
  lists; build product pages for them when data exists (rule amended in CLAUDE.md). Catalog-active SKUs on
  pentair.com pages marked Discontinued are discontinued (owner_decisions.json).
- Next: add the SKUs that current pentair.com pages list but the catalog never printed (88), then the
  discontinued-with-parts lines, with titles under docs/title-rules-v2.md.

## 2026-10-26 (later): parts diagrams re-done, brochures from FlippingBook
- Matthew: "The parts diagram still doesn't look right. Review them all as rendered and figure out what is wrong."
  Found: 124 of the 299 "diagram" pages were accessory tables with no exploded view; crops followed the text
  layout (side tab, Prop 65 frame, table bars, blank right third kept); drawings beside/below tables missed.
  Now `scripts/diagram_crops.py` finds each drawing from the PDF's curve objects and embedded artwork, masks
  table cells, headings and the Prop 65 box, renders at 300 dpi and trims: 166 images from 146 pages, 14
  "(CONT'D)" pages reuse their drawing, 15 table-only pages and 124 accessory pages get none.
- Brochures, sell sheets: pentair.com embeds them as FlippingBook flipbooks (`a.fbo-embed`), not PDF links.
  `web_media.py` records them (kinds brochure / sell sheet, host flippingbook); `scripts/fbo_fetch.js` drives
  the viewer's Download button for Pentair's original PDF (40 publications). Kept pending Matthew's answer on
  the review page (reports/diagram-review.html, question d3). Owner's manuals were already captured as the
  page's "User's Guide".
- Storage: all downloaded media lives in the container's gitignored data/raw/; an R2 bucket (or similar) is
  needed. Asked on the review page (d2) with the secret names I would read.
