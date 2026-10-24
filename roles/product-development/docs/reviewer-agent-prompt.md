# Reviewer agent prompt (full catalog run)

Launch one agent per batch per pass. `{PASS}` is `reviews` (pass A) or `reviews_b` (pass B);
`{OTHER}` is the other one. `{PAGES}` comes from `data/work/pentair/batches.json`.
Progress: `python3 scripts/run_status.py`. After both passes: `compare_reviews.py`, adjudicate
disagreements, then `consolidate.py`.

---

You are reviewing pages of the Pentair Pool 2025-2026 product catalog to extract SKUs with
titles. Repo: /home/user/product-namer. Precision is the top priority: a wrong SKU or a
misleading title is worse than a flagged one.

Read these first and follow them exactly:
- /home/user/product-namer/docs/page-review-procedure.md
- /home/user/product-namer/docs/pentair-title-rules.md

Your review directory is `{PASS}`: write /home/user/product-namer/data/work/pentair/{PASS}/pNNN.json
and validate with
`cd /home/user/product-namer && REVIEW_DIR={PASS} python3 scripts/catalog_pages.py validate NNN`.

Pages (PDF page numbers): {PAGES}.
Packets: data/work/pentair/packets/pNNN.json. Images: data/raw/pentair/pdf/png/pNNN.png.
Always view the image with the Read tool; for dense tables crop/zoom with Python PIL into
data/work/pentair/crops_{PASS}/ and Read the crop. Neighbouring pages (packets/images outside
your list) may be viewed for context, e.g. a table continued from the previous page, a legend,
or the directory (p004–p007) for trademark spelling and Sta-Rite families.

Write only your own review JSONs and crops. Do not open data/work/pentair/{OTHER},
data/work/pentair/calibration or data/work/pentair/pilot1: they are independent reviews.
Never edit scripts, rules or packets. Work until every page in your list validates OK.

Reply briefly: per page, page_type, record count, records marked confidence "review" with the
reason; then any rule that was unclear or wrong for a real case (quote the case). Keep it short.
