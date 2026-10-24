# Harmonizer agent prompt (cross-page title pass)

Run after every page is final: `consolidate.py` → `harmonize_prep.py` → one agent per packet
(`{PACKET}` = h01, h02, …) → `harmonize_check.py all` → `consolidate.py` again.

---

You are harmonizing titles for Pentair SKUs across the whole 2025-2026 Pentair Pool catalog. Repo:
/home/user/product-namer. Every page has already been reviewed twice and adjudicated. Your job is
different: a SKU printed on several pages must end up with ONE title, the same style as its
neighbours, and no two SKUs may share a title. Precision is the top priority: a misleading title is
worse than a flagged one.

Read first, and follow:
- /home/user/product-namer/docs/pentair-title-rules.md (all title rules; they apply here too)
- your packet: /home/user/product-namer/data/work/pentair/harmonize/packets/{PACKET}.json

Each SKU in the packet has `why` (why it is here), `current_title` (what consolidation picked),
`evidence` (every page's record: title, source_row = the printed row, context, notes) and
`page_headings`. Page images are at /home/user/product-namer/data/raw/pentair/pdf/png/pNNN.png
(PDF page number) if you need to look.

For every SKU decide one title:

1. **Source of the words.** Use only words printed for this SKU on some page (any of its evidence
   rows), plus the product noun or line name from a page heading/band where it is listed. Never
   invent a word. Abbreviations/typos may be expanded/corrected when the full or correct form is
   printed for this SKU or in the same catalog section.
2. **Whole goods and accessories:** the title from the whole-goods or accessory page wins
   (page_type whole_goods / accessory tables), unless it is clearly less specific.
3. **Parts: family.** Look at every page the SKU is listed on.
   - All pages are one product line (or models of one line per the rules' line list) → the line
     name, without a model unless the SKU is on only one model's page.
   - Different lines → no trademark family. Then prefix the generic product noun that EVERY one of
     those lines shares, when there is one: "Pump", "Filter", "Heater", "Light", "Valve",
     "Multiport Valve", "Skimmer", "Cleaner", "Automatic Feeder"… e.g. "Pump Impeller",
     "Filter Lid O-Ring", "Multiport Valve Handle". Hardware that is used across product types
     (bolts, screws, washers, nuts, generic O-rings used on pumps AND filters) gets no noun prefix.
   - Model fits ("for Model 120HC") on a no-family part must name the line ("for UltraTemp® Model
     120HC") or be dropped if the SKU fits other lines too; never leave a bare model number that
     points to the wrong line.
4. **Description.** Prefer the most specific accurate printed description (sizes, material,
   colour, thread). Apply the word-order rules consistently: specs/size first, colour immediately
   before the noun phrase, material/type words that classify the noun stay next to it ("White Vinyl
   Deck Collar"), noun last for hardware ("3/8-16 x 7/8 in SS Hex Head Bolt"); kit contents
   "3 Gaskets" → "3-Gasket Kit"; "Only" dropped unless it states a fit limit that is the only
   difference between siblings.
5. **Canonical spellings** (directory pp. 4–7 is the authority): System:3®, System:2™,
   ThermalFlo®, UltraTemp ETi® Heater, IntelliProXF®, HiFlow™, Mini Vac™, FullFloXF®,
   WhisperFloXF®, IntelliFloXF®, Max-E-ProXF®, Challenger®, IntelliFlo®, IntelliChem®.
   Upper-case MPN suffixes (070387Z, not 070387z): the title uses the upper-case MPN.
6. **Uniqueness.** No two active SKUs may share a derived title (the part after "MPN - "). SKUs
   whose `why` says "derived title shared with …" are in your packet together: tell them apart with
   a printed difference from any of their pages (size, colour, HP, model, material). If nothing
   printed tells them apart, keep the same title and set confidence "review" on all of them.
7. Do not change brand or status. Change `kind` only when the evidence shows it (e.g. the SKU is
   sold on an accessory page). Set `product_line` to the family used in the title ("" if none).

Write /home/user/product-namer/data/work/pentair/harmonize/out/{PACKET}.json:

```json
{"packet": "{PACKET}", "decisions": [
  {"mpn": "070429Z", "title": "Pentair 070429Z - 3/8-16 x 7/8 in 18-8 SS Hex Head Bolt",
   "product_line": "", "kind": "part", "confidence": "high",
   "reason": "shared by IntelliFlo, WhisperFlo, Challenger pages → no family; hardware noun last; '18-8' printed on p433/p440"}
]}
```

One decision for EVERY SKU in the packet (keep `current_title` when it is already right, with
reason "current title correct"). Then run
`python3 scripts/harmonize_check.py {PACKET}` from the repo root and fix every problem it reports.
A duplicate it reports against a SKU in ANOTHER packet: change your own SKU's title only if a
printed difference exists; otherwise note it in your report.

Write only your decision file (scratch files may go in
/home/user/product-namer/data/work/pentair/scratch/harmonize/{PACKET}/). Do not edit reviews,
rules, scripts or packets, and do not commit.

Report back briefly: number of SKUs, how many titles changed, the decisions left at confidence
"review" and why, and any rule that was unclear or wrong for a real case.
