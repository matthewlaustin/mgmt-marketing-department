# v2 final sweep prompt

Each sweep agent owns a range of batches ({RANGE}) and may edit only
`data/work/pentair/v2/final/bNN.json` files in that range. Repo: /home/user/product-namer.

1. Read `docs/title-rules-v2.md` in full. Many interim calls at the end were added after early
   batches were finalized, so finals in your range may not follow them.
2. Read `docs/v2-sweep-notes.md`. Do every item assigned to your range below; the rest are for
   other agents.
3. For every record in your range, check the title and brand against the printed evidence in
   `data/work/pentair/v2/batches/bNN.json` and every rule. Fix what doesn't follow the rules, and
   append to `why` a short "Sweep: …" note saying what changed and why. Don't change titles that
   already follow the rules; don't reword for taste.
4. `unsure` stays true only where Matthew must decide. Clear it where a later call settles the
   question (per-unit counts, EC- twins with an exact match, bare generic titles, etc.).
5. Brands: ignore any "(parts are Pentair)" note in batch context; the brand rules decide.
6. Keep one pattern per printed table: if a sibling in another batch (outside your range) uses a
   different pattern, follow the rules, and list the conflict in your report rather than editing
   the other file.
7. Run `python3 scripts/v2_check.py final bNN` for every file you touch. Don't commit.

Report briefly: per batch, how many titles changed (with 2–3 examples), how many unsure remain and
the questions behind them (grouped), and any cross-range conflicts for the coordinator.
