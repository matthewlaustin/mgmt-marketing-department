# Adjudicator agent prompt

Run after both blind passes cover a page and `scripts/prepare_adjudication.py` queued it in
`data/work/pentair/adjudicate/`. `{PAGES}` are PDF page numbers; `{FIRST_PAGE}` the first of them.

---

You are the adjudicator for pages of the Pentair Pool 2025-2026 catalog. Two reviewers worked
on each page independently and disagreed somewhere. Your job is to write the final, correct
review for each page. Precision is the top priority. Repo: /home/user/product-namer.

Read first, and apply the CURRENT version (it has been tightened since some reviews were written):
- /home/user/product-namer/docs/pentair-title-rules.md
- /home/user/product-namer/docs/page-review-procedure.md

For each page NNN in: {PAGES}
1. Read data/work/pentair/adjudicate/pNNN.json (the list of differences), both reviews
   data/work/pentair/reviews/pNNN.json (A) and data/work/pentair/reviews_b/pNNN.json (B), and
   the packet data/work/pentair/packets/pNNN.json.
2. Look at the page image data/raw/pentair/pdf/png/pNNN.png (Read tool; crop/zoom with PIL into
   data/work/pentair/scratch/final/p{FIRST_PAGE}/ for dense tables). Decide each difference from
   the page itself and the rules, not by preferring A or B. Neither may be right: write the
   correct value. Re-check records where A and B agree only if the page shows they are wrong.
3. Write data/work/pentair/reviews_final/pNNN.json in the normal review format, starting from
   the better review, and add a top-level "resolution" list: one entry per difference,
   {"mpn": ..., "field": ..., "chosen": ..., "why": "<short reason from the page/rules>"}.
4. Validate: `cd /home/user/product-namer && REVIEW_DIR=reviews_final python3 scripts/catalog_pages.py validate NNN`
   and fix until OK. Never edit scripts, rules, packets, or the A/B reviews.

Keep helper scripts only in data/work/pentair/scratch/final/p{FIRST_PAGE}/.
Reply briefly: per page, number of differences resolved and any that remain genuinely
uncertain (left as confidence "review" with a note) — those go to the business owner.
