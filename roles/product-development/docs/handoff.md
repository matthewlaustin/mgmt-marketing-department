# Handoff: where the project stands (2026-10-27)

Read this first in a new session, then CLAUDE.md (the rules) and the end of docs/data-v3-plan.md (the decision log,
every answer Matthew has given, newest at the bottom).

## What exists

- **The catalog**: `data/catalog.db` (SQLite, committed), 4,725 active SKUs for Pentair, Sta-Rite and Pleatco: titles,
  specs (18,726 values), derived facts, product lines (families), parts lists per model (model_parts, 32,018 rows),
  fitment, cross references and replaced numbers, documents (556 PDFs), images (diagrams, charts, gallery), product
  photos (3,540 SKUs). Schema in `docs/neon_schema.sql`; how it was built in `docs/data-v3-plan.md`.
- **Neon mirror**: project "Pool Geek® Manufacturer Catalog" (id still-union-48288873, aws-us-east-2), schema
  `mfr_catalog`, loaded by `scripts/load_neon.py` (see `docs/neon.md`). Never load into "Pool Geek® Products".
  The connection string was kept in the session scratchpad, which does not survive the session: a new session
  gets it again with the Neon MCP tool get_connection_string for that project and keeps it in its own scratchpad
  (chmod 600), never in the repo or in chat.
- **Media in R2**: bucket `pool-geek-data-specialist`, keys `pentair/{photos,docs,diagrams,charts}/...` and
  `product-photos/<sha>.ext`; maps in `data/work/pentair/r2_objects.json` and `data/work/photos/r2_photos.json`;
  public URLs on the `documents`, `images` and `product_photos` rows. Credentials are environment variables
  (R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_URL). The public URL is an r2.dev
  test URL, rate-limited; a custom domain is needed before anything serves from it.
- **Downloads** (`data/raw/`, gitignored) are gone with the container: pentair.com pages, PDFs, images. Every
  script that needs them re-downloads politely and caches; nothing in the catalog depends on re-downloading.
- **Working files** (`data/work/`, mostly committed): review packets and verdicts for every phase, the photo
  candidates, choices, hashes and rejections (`data/work/photos/`), diagram crops metadata (`data/work/pentair/d3/`).
- **Review pages** for Matthew (`reports/*.html`, published as Artifacts; answers come back through ArtifactData):
  - Shopify import plan: https://claude.ai/artifact/S9eW5ytxv9b2y9k1a5UYa9 (collections `shopify_answers`,
    `shopify_followups`). **Twelve questions are waiting here.** Built by `scripts/shopify_plan_page.py`.
  - Product photos: https://claude.ai/artifact/R39ePqtz5guLhg9qYQTbZr (`photo_answers`, `photo_followups`).
  - Parts diagrams and media: https://claude.ai/artifact/9kWhxJJ3pkAUS51ZDADhkW (`diagram_answers`, `diagram_followups`).
  - Product data (phase 3): https://claude.ai/artifact/DfxbfFuUvGa4AtuoaN6Tq5; media review 6arnkX8eFNvFF2B3cFqsz1;
    pump page demo C4mAuMTs74z4Ph1FQfPw2Z.
  Matthew says "Answered" or "Done" in chat; read the collections back with ArtifactData then.

## The next step: Shopify

Matthew's direction (2026-10-27): put the data into a **Shopify development store on the Ignite theme** and reshape
the theme around the data to find a better way of presenting the products. Do not build on how poolgeek.com is laid
out today; moving to the live store is a later step with its own questions. The plan is on the page above and in
`reports/shopify-plan.html`; its core:

1. `mfr_catalog` stays untouched as the audit trail. A separate `shop` layer (SQLite tables beside the catalog, a
   Neon schema `shop`, CSV exports under `exports/shopify/`) is built from it by whitelist in `scripts/shop_build.py`
   (to be written), with a test that fails the build if any internal marker (evidence, conflicts, data_issues,
   needs_review, review_notes, basis, source, via, raw, pages, pdf_page, `catalog://`, CALL, photo tiers, local
   paths) reaches an exported value. Manufacturer text only; no invented copy (question 4 on the page decides
   whether fixed template lines are allowed).
2. Data shape: category (14-category tree proposed on the page) > product line (metaobject `product_line` with its
   own page) > model (product, one per SKU) > part or accessory (product, one per SKU). Specs, facts, fitment,
   parts lists with diagram positions, documents and part numbers as typed metafields (namespaces specs, facts,
   line, fits, parts, docs, numbers).
3. Storefront pieces on Ignite: product-line page with model comparison table, model page with clickable exploded
   diagram, part page with every model it fits, collection filters from facts, part-number lookup (current, old
   and cross-referenced numbers), document library. Theme code to be pulled into `theme/` and versioned.
4. Order: store access, shop layer, definitions, one product line end to end (IntelliFlo3 proposed), theme
   reshaped on it with a review page, full run in batches with a log, reconcile.

**Store access**: Matthew created an app in the Shopify Dev Dashboard and put its credentials in the environment
as SHOPIFY_SHOP, SHOPIFY_CLIENT_ID and SHOPIFY_CLIENT_SECRET (a legacy permanent token would be SHOPIFY_ADMIN_TOKEN).
The session that wrote this started before they were added and could not see them. **First thing in the new
session**: `python3 scripts/shopify_client.py check` (read-only: store name, development-store flag, granted
scopes). It needs scopes for products, files, metaobjects, metafield definitions and themes; if any is missing,
tell Matthew which, in a line. Never print or commit the credentials.

Then read the twelve answers from `shopify_answers` (ArtifactData, artifact S9eW5ytxv9b2y9k1a5UYa9), log them in
`docs/data-v3-plan.md`, and start on `scripts/shop_build.py`.

## Open threads, not blocking

- 1,185 SKUs have no photo; Matthew said keep searching (43 web-search batches remain in
  `data/work/photos/search/`; `scripts/page_images.py`, `photo_select.py`, `photo_review.py`, `photo_load.py`).
- `reports/needs-attention.md` lists the items that need a person.
- The r2.dev public URL needs a custom domain before production.

## How to work here

- Rules in CLAUDE.md; Matthew's preferences there too: reports and questions go on an Artifact page with answer
  boxes (pattern: `scripts/*_template.html` with `/*DATA*/` injection, `window.claude.use("db")`, tested with
  Playwright before publishing), never a list of questions in chat.
- `python3 -m pytest -q` before each code commit (36 tests). Commit and push to the session branch often; never
  push to main directly (this handoff was merged through a pull request at Matthew's request).
- Agents that did the heavy review work ran from the prompts in `docs/*-prompt.md`; cost so far about $1,100 in
  list-price tokens since 2026-10-24 (Matthew asked once; the method is in the decision log).
