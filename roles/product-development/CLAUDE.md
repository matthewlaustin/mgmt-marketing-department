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

## Matthew's preferences (added with his permission)
- Send reports, results and questions for Matthew as an Artifact page he can review in the Claude desktop or iOS app, with places to answer questions and leave follow-ups in the page (read answers back with ArtifactData). Keep the chat reply short and link the page.
- Never ask Matthew a series of questions in chat: no question lists in the reply and no multiple-choice
  prompts in the terminal. Put every question on an Artifact page, test the page before sending it, and
  reply with a few lines and the link. (Matthew, 2026-10-25)
