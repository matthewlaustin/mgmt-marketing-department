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
