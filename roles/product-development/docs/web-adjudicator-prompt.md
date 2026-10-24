# Phase 2 web adjudicator prompt

Run after `web_compare.py` queued a packet in data/work/pentair/web/adjudicate/.

---

You are the adjudicator for one packet of Pentair website-only SKUs. Repo: /home/user/product-namer.
Two reviewers titled the packet independently and disagreed somewhere. Write the final review.
Precision is the top priority.

Read first and follow:
- /home/user/product-namer/docs/web-reviewer-prompt.md (the task and output format; everything below
  its `---` line applies to you, except that you write the `final` pass)
- /home/user/product-namer/docs/pentair-title-rules.md
- the differences: /home/user/product-namer/data/work/pentair/web/adjudicate/{PACKET}.json
- both reviews: /home/user/product-namer/data/work/pentair/web/a/{PACKET}.json and .../b/{PACKET}.json
- the packet: /home/user/product-namer/data/work/pentair/web/packets/{PACKET}.json

Start from the review that is right more often. For each difference decide from Pentair's published
rows, the page name and the catalog titles on the same page, which version follows the rules; you may
also write a better title than either when both are wrong (only printed words). Records where A and B
agree stay as they are unless they clearly break a rule. Add a `resolution` list to the file: one entry
per difference, `{"mpn", "field", "chosen", "why"}`.

Write /home/user/product-namer/data/work/pentair/web/final/{PACKET}.json, then run
`python3 scripts/web_check.py final {PACKET}` and fix every problem it reports. Write only that file
and do not commit.

Report back briefly: differences resolved, decisions left at confidence "review" and why.
