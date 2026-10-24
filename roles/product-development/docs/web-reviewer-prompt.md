# Phase 2 web reviewer prompt (website-only Pentair SKUs)

Run after `pentair_web_specs.py` and `web_prep.py`. Two blind passes per packet (`{PASS}` = a | b),
then `web_compare.py` and an adjudicator writes `final` for packets where the passes disagree.

---

You are titling Pentair SKUs that are on pentair.com but not in the 2025-26 printed catalog. Repo:
/home/user/product-namer. Precision is the top priority: a wrong or misleading title is worse than a
flagged one.

Read first and follow:
- /home/user/product-namer/docs/pentair-title-rules.md (all title rules apply)
- /home/user/product-namer/docs/audit-agent-prompt.md, the "Catalog-wide conventions" list only
  (generic noun prefix, hardware, heat pump vs heater, dates, counts, spec wording, trademarks)
- your packet: /home/user/product-namer/data/work/pentair/web/packets/{PACKET}.json

The packet groups product pages. Each page has `page_name` (the product name Pentair gives the page),
`catalog_titles_on_this_page` (finished titles of the page's other SKUs, already in the database: match
their style) and `skus`, each with every spec-table row Pentair publishes for it (`headers`, `cells`,
`row_text`). These rows and the page name are your only sources: never use a retailer, a distributor
or your own knowledge for a word in a title. If you need more of the page, the cached HTML is in
/home/user/product-namer/data/raw/pentair/pages/ (file names start with the URL path).

For each SKU:
1. **Brand**: Pentair, or Sta-Rite for Sta-Rite whole goods (see the rules), or Pleatco for Pleatco
   cartridges. Parts and accessories are always Pentair.
2. **Kind**: whole_good, accessory, part or service, judged from the page and the row.
3. **Title**: `{Brand} {MPN} - {derived title}` built from the row's description plus the page's
   product family and noun, exactly like the catalog titles on the same page. Drop secondary
   parentheticals, expand only abbreviations spelled out on the page, put specs before the noun and
   colour right before the noun phrase. Add a spec only when it is needed to tell siblings apart.
4. **Status**: active, unless the row or page says discontinued, replaced or not for sale in the USA
   (then discontinued / not_for_sale_usa, with the replacement in notes).
5. **Confidence**: "review" when the row is thin (a bare code, no noun), ambiguous, or contradicts
   the page; say why in `notes`.
6. **Z twins**: a trailing "Z" is the same part packed for retail/service (Matthew). If a SKU here
   is the Z or non-Z twin of a catalog SKU, describe it the same way as the twin (say so in notes);
   web_check allows that shared title. The suffix never makes either number discontinued.
7. A row that is not a sellable SKU of this product (a spec line, a dimension row), or a SKU whose
   rows are too thin to title without guessing, is dismissed with a reason instead.

Write /home/user/product-namer/data/work/pentair/web/{PASS}/{PACKET}.json:

```json
{"packet": "{PACKET}", "records": [
  {"mpn": "07017-0151", "brand": "Pentair", "title": "Pentair 07017-0151 - 1-1/2 in NPT Hydrostatic Valve",
   "kind": "part", "status": "active", "product_line": "", "confidence": "high",
   "source_row": "07017-0151 | 1-1/2 in. NPT hydrostatic valve", "notes": "Pool Specialty Fittings page"}
 ],
 "dismissed": [{"mpn": "…", "reason": "…"}]}
```

`source_row` must be copied exactly from one of the SKU's `row_text` values. Then run
`python3 scripts/web_check.py {PASS} {PACKET}` from the repo root and fix every problem it reports.

Work independently: do not open the other pass's folder (data/work/pentair/web/a or b, whichever is not
yours). Write only your review file (scratch files may go in
/home/user/product-namer/data/work/pentair/scratch/web/{PASS}/{PACKET}/). Do not commit.

Report back briefly: SKUs titled, dismissed, at "review" and why, and any rule that was unclear for a
real case.
