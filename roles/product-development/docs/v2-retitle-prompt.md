# v2 retitle prompt (full catalog)

Built by `scripts/v2_prep.py`. Each batch gets two blind passes ({PASS} = a | b). Then
`scripts/v2_compare.py` runs, and an adjudicator settles the differences (see the end of this file).

---

You are retitling a batch of Pentair SKUs under title rules that the business owner, Matthew, set
by hand. Repo: /home/user/product-namer. Precision matters most. A wrong title costs Matthew time,
and so does an inconsistent one.

Read these first and follow them:
- /home/user/product-namer/docs/title-rules-v2.md holds THE rules. All of it applies, including
  "Settled by the 40-SKU check". Its examples are Matthew's own answers.
- /home/user/product-namer/docs/pentair-title-rules.md is background. Use it for the Sta-Rite
  family list under "Brand", the trademark spellings, the Z suffix and the clean-up list.
  Wherever it conflicts with v2, v2 wins. Its rule that parts are always Pentair no longer applies.
- /home/user/product-namer/data/work/pentair/v2_sample/ shows 40 worked examples, with Matthew's
  verdicts in docs/title-rules-v2.md. In those files, `a.json` matches the approved titles except
  where the rules file says otherwise.
- Your batch: /home/user/product-namer/data/work/pentair/v2/batches/{BATCH}.json. It holds groups
  (a catalog page "pNNN", or a pentair.com URL), each with SKUs. Every SKU carries its old title
  (made under OLD rules, so never copy its style), kind, product line and `evidence`: every row
  Pentair printed for it, as pdf_page, page_type, row and context.

For each SKU:
1. Read the printed rows. Where a row alone is unclear (a model chart, a band, column headers,
   or the Sta-Rite logo), read the page text:
   `python3 -c "import pdfplumber; p=pdfplumber.open('/home/user/product-namer/data/raw/pentair/pdf/catalog2025/pentair-catalog-2025-2026-digital-1-compressed.pdf'); print(p.pages[N-1].extract_text())"`
   If needed, also look at the page image /home/user/product-namer/data/raw/pentair/pdf/png/pNNN.png
   with the Read tool. Pages carrying the Sta-Rite logo show it only in the image.
   For pentair.com SKUs, the row text is the source. Their cached pages are under
   /home/user/product-namer/data/raw/pentair/pages/.
2. Brand:
   - A part or accessory follows the product line(s) it is listed under, using the pages in its
     evidence. Pentair and Sta-Rite lines together give `Pentair/Sta-Rite`.
   - Whole goods take Sta-Rite only for the Sta-Rite families.
   - Pleatco items are Pleatco.
3. Title: built only from printed words, by the rules. Within one parts list, make sure two rows
   don't end up with the same title unless nothing printed tells them apart.
4. Set `unsure: true` when a rule doesn't clearly settle the case, and say why in `why`. Use
   `why` too for any choice that isn't obvious, such as which page's wording you used.

Write /home/user/product-namer/data/work/pentair/v2/{PASS}/{BATCH}.json as a JSON list with one
entry per SKU, in batch order:
[{"mpn", "brand", "title" (full "Brand MPN - Title"), "unsure", "why"}]

Then run `python3 scripts/v2_check.py {PASS} {BATCH}` from the repo root and fix every problem it
reports. Work independently: don't open the other pass's folder. You may write scratch files under
/home/user/product-namer/data/work/pentair/scratch/v2/{PASS}/{BATCH}/. Don't commit.

Report back in a few lines: how many SKUs you marked unsure, and any rule that was unclear for a
real case.

## Adjudicator ({PASS} = final)
Read everything above, plus /home/user/product-namer/data/work/pentair/v2/adjudicate/{BATCH}.json
(the differences) and both passes. Start from whichever pass is right more often. For each
difference, decide from the printed rows and the rules. You may write a better title than either
pass, using printed words only. Keep `unsure: true` only where Matthew must decide, and give the
question in `why`. Write v2/final/{BATCH}.json, run `python3 scripts/v2_check.py final {BATCH}`,
and don't commit.
