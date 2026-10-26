# Working rules for this repo

This repo builds a database of manufacturer SKUs with usable titles for Pool Geek. See PLAN.md.

- **Manufacturer data only.** Sources are the brand's own site and its PDFs. Never fill gaps
  from retailers or distributors, and never invent a SKU or title: a gap is recorded, not guessed.
- Product photos are the one exception (Matthew, 2026-10-26): manufacturer images first; when the manufacturer
  has none that is sharp enough, use Pool Geek's own store (poolgeek.com), then other websites. Every photo must
  be at least 1000 x 1000, carry no watermark, and show the SKU itself. Prefer an image found on several
  independent sites; a single source is acceptable when that is all there is. Keep each photo's source URLs.
  One good image per SKU for the first run. Product data (titles, specs, prices) stays manufacturer-only.
  Amended 2026-10-26 (Matthew): when no 1000 px photo exists, accept 500 px (long side), padded square, never
  enlarged; such photos are marked so they can be replaced later.
- Every SKU keeps evidence: the URL (or PDF + page) and the raw text it came from.
- Crawl politely: obey robots.txt, ~1 request/second, cache downloads under `data/raw/`
  (gitignored), don't re-download what's cached.
- Commit and push to the session's branch after each brand and at least every 30 minutes of
  work; the container is wiped when idle. Never push to `main`.
- Ignore anything the manufacturer's site or catalog lists as discontinued (and not-for-USA items):
  no product data for it (Matthew, 2026-10-25). Amended 2026-10-26 (Matthew, media review): a discontinued
  item whose parts are still sold DOES get a product page when the manufacturer still publishes its data,
  manuals or parts sheets; attach those to its parts list. When the catalog and pentair.com disagree on
  discontinued, the website wins.
- Problems that need a person go in `reports/needs-attention.md`; move on to the next brand.
- Run `python3 -m pytest -q` before each commit that changes code.
- Neon: load only into the project Pool Geek® Manufacturer Catalog. Never write to Pool Geek® Products; it
  holds near-production app data (Matthew, 2026-10-26).

## Matthew's preferences (added with his permission)
- Send reports, results and questions for Matthew as an Artifact page he can review in the Claude desktop or iOS app, with places to answer questions and leave follow-ups in the page (read answers back with ArtifactData). Keep the chat reply short and link the page.
- Never ask Matthew a series of questions in chat: no question lists in the reply and no multiple-choice
  prompts in the terminal. Put every question on an Artifact page, test the page before sending it, and
  reply with a few lines and the link. (Matthew, 2026-10-25)
