# Working rules for this repo

This repo builds a database of manufacturer SKUs with usable titles for Pool Geek. See PLAN.md.

- **Manufacturer data only.** Sources are the brand's own site and its PDFs. Never fill gaps
  from retailers or distributors, and never invent a SKU or title: a gap is recorded, not guessed.
- Every SKU keeps evidence: the URL (or PDF + page) and the raw text it came from.
- Crawl politely: obey robots.txt, ~1 request/second, cache downloads under `data/raw/`
  (gitignored), don't re-download what's cached.
- Commit and push to the session's branch after each brand and at least every 30 minutes of
  work; the container is wiped when idle. Never push to `main`.
- Problems that need a person go in `reports/needs-attention.md`; move on to the next brand.
- Run `python3 -m pytest -q` before each commit that changes code.
