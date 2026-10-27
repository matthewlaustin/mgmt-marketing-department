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
- Matthew (2026-10-26): "Flipping book is just a pdf wrapper" — the brochure and sell-sheet PDFs downloaded through
  the FlippingBook viewer count as Pentair's own PDFs; keep them (question d3 withdrawn from the review page).
- Diagram review answered (Matthew, 2026-10-26 18:04): d1 the new diagrams are right, use them. d2 yes to R2;
  he asked where to put the credentials (answered in chat: the cloud environment's settings, Network secrets /
  environment variables, names R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_URL).
  `scripts/r2_upload.py` is ready (dry run: 1,193 files, 1.65 GB). Follow-up, not yet: "can you search the web
  for images and download them for all these skus?" — assessed in chat; needs an amendment to the
  manufacturer-only rule before any retailer image is taken.
- R2 set up by Matthew (bucket pool-geek-data-specialist, public r2.dev URL). `scripts/r2_upload.py` uploaded
  1,193 files (1.65 GB); images.object_key/public_url and documents.object_key/public_url filled locally from
  data/work/pentair/r2_objects.json (web_media_load.py apply_r2). Columns added in Neon mfr_catalog.
- Matthew (2026-10-26): "Pool Geek Products is a separate instance with pretty close to production data in it."
  Neon writes paused. Checked: mfr_catalog (22 tables, 31 MB) has no foreign keys or views shared with public
  (19 app tables, 90 MB). Recommended moving the catalog to its own Neon project; asked on the review page (d4).
- Matthew (2026-10-26 18:50, d4): move the catalog to its own Neon project. Created Pool Geek® Manufacturer
  Catalog (still-union-48288873, aws-us-east-2, Postgres 18); schema copied from the live tables
  (docs/neon_schema.sql); loaded and verified (22 tables, every count equals data/catalog.db). Fixed a gap:
  cross_references, replacements, family_links and model_parts were never in load_neon.py, so they were empty
  in Neon until now. CLAUDE.md now says never load into Pool Geek® Products. Removing the stale copy there
  (DROP SCHEMA mfr_catalog CASCADE) waits for Matthew's answer on the review page (d5).
- Matthew (2026-10-26 19:06, d5): remove the old copy. Checked first: no views, foreign keys or functions outside
  mfr_catalog depended on it. Ran DROP SCHEMA mfr_catalog CASCADE on Pool Geek® Products at 19:07:06 UTC. The
  app's 20 tables in public and drizzle had 35,957 rows before and after, identical per table. Restorable
  from Neon history until about 2026-10-27 19:07 UTC. The Products connection string was deleted from the
  session scratchpad; only the Manufacturer Catalog string remains (scratchpad/neon_catalog_url).

## 2026-10-26: product photos, first run
- Matthew: photos for as many products as possible; 1000 x 1000+, no watermark; manufacturer first, then
  poolgeek.com, then the web; prefer a picture several independent sites share; one image per SKU for now.
  Recorded as an exception to "manufacturer data only" in CLAUDE.md.
- Sources: Pentair originals (scripts/pentair_originals.py), 36 Shopify store catalogs that allow /products.json
  (scripts/shopify_fetch.py, incl. poolgeek.com), web search for the rest (101 batches of 30 SKUs; only the first
  8 batches ran because WebSearch is capped at ~200 calls per turn; scripts/page_images.py checks the pages).
- Selection (scripts/photo_select.py): exact SKU match (or one part number in the title / description), store
  placeholders dropped, perceptual hash for "same picture on several sites", order Pentair > Pool Geek > shared >
  single site; nothing upscaled (Leslie's image server enlarges unless told not to).
- Watermark review by eye (scripts/photo_review.py, three rounds, 2,581 photos): 379 rejected. Whole stores
  excluded: bathandspaparts (every photo), discountpoolmart (225/225), sospool, thepoolsupplywarehouse,
  nwpoolsupply.
- Result: product_photos table, 3,048 of 4,725 SKUs (851 Pentair, 111 Pool Geek, 897 shared, 1,189 single
  site), every photo copied to R2 (product-photos/<sha>.ext) and loaded to Neon. 163 near-misses and 1,514
  without a photo. Questions on reports/product-photos.html (p1 single-site photos, p2 padding, p3 more search).
- Matthew's answers (2026-10-26 20:57, product-photos page): p1 keep single-site photos; p2 pad near-misses onto
  a white square (no enlarging); p3 keep searching the web. Search round 2: 1,630 SKUs still to search, whole
  goods first, ~180 searches per turn.
- Search round 2 (2026-10-26, ~180 searches, whole goods first): 425 SKUs checked in all, 45 with a 1000x1000+
  image online. Near-misses reviewed (25 of 163 rejected) and padded to white squares. Rejections now follow the
  picture (perceptual hash) for content problems; watermark rejections block only unreviewed copies. Result:
  3,199 SKUs with an approved photo (149 padded), all in R2 and Neon; 1,526 without. New question p4 on the
  photos page: keep searching, ask Pentair for its dealer image library, photograph in-house, or stop.
- Matthew (2026-10-26 22:10, p4): "Keep searching anyway", note "Take the cutoff down to 500 px". Applied as: a
  1000 px photo still wins; otherwise a reviewed photo whose long side is 500-999 px, padded square, never enlarged,
  tier marked "(500-999 px)". Search batches r2_006-011 run (~180 searches). Reviewed 581 + replacements: 116
  rejected (mostly a "(c) APC" mark carried by an image supplier across many stores; rulers in O-ring photos pass).
  Result: 3,540 SKUs with a photo (336 at 500-999 px, 330 padded), 1,185 without; 43 search batches remain.

## 2026-10-27: plan for the Shopify import
- Matthew: next step is readying the data for Shopify; the Neon database is full of internal notes, so how is
  the data prepared for production? Plan published as reports/shopify-plan.html (scripts/shopify_plan_page.py +
  template; Artifact https://claude.ai/artifact/S9eW5ytxv9b2y9k1a5UYa9; answers in ArtifactData collections
  shopify_answers / shopify_followups). Core of the plan: mfr_catalog stays untouched as the audit trail; a
  separate `shop` layer (SQLite + Neon schema `shop` + CSV exports) is built by whitelist from it, with a test
  that fails the build if any internal marker (evidence, basis, source, via, raw, pages, catalog://, CALL, tiers)
  reaches an exported value; Shopify fields mapped from manufacturer data only; specs and facts as typed
  metafields; fitment and parts lists as product references; manuals as Shopify Files; the 259 SKUs already on
  poolgeek.com enriched, not replaced; Admin API push with dry run, 25-SKU pilot as drafts, then batches.
  Fourteen questions wait on the page (home for the shop layer, import route, matched-SKU policy, pricing,
  dual-brand vendor, trademark marks, template copy, type/tag mapping, document hosting, status, SKUs without
  photos, variants, pilot location, inventory).
