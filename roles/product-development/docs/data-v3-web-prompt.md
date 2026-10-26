# Phase 3 extraction from pentair.com (web-only SKUs, batches wNN)

Follow `docs/data-v3-prompt.md` exactly, with these differences:

- The source is Pentair's own product web page, not the catalog. Each page in the batch file has
  `url`, `page_name`, `text` (path to the page's readable text: description, feature bullets, spec
  tables, notes) and `skus` with the spec-table rows already parsed (`headers` + `rows`). Read the
  text file for every page. There are no page images.
- `page` is always `0` (meaning pentair.com) on every record, and every family, product, fitment,
  reference and issue also carries `"url": "<the page url>"`.
- Attach data only to the SKUs listed in the batch (they are the web-only SKUs; other SKUs on the same
  page already have catalog data). Family records are still welcome for context.
- Reuse catalog family ids whenever the page is the same product line (list them with
  `grep -ho '"id": "[^"]*"' data/work/pentair/d3/out/d*.json | sort -u`). A web-only SKU that belongs to a
  catalog line gets that line's id as its `family`.
- The website prints no list prices: no `prices`; set no `price_note`.
- "Purchase Options" / "Available Through Dealer" / "Where to Buy" text is not data.
- Ignore anything the page marks discontinued.
