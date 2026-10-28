# Sibling-consistency audit prompt (final title pass)

Run after every hNN harmonization packet is decided: `consolidate.py` → `audit_prep.py` → one agent
per packet (`{PACKET}` = s01 … s17) → `harmonize_check.py all` → `consolidate.py`.

---

You are doing the final consistency audit of Pentair SKU titles in one section of the Pentair Pool
2025-2026 catalog. Repo: /home/user/product-namer. Every title has already been reviewed twice,
adjudicated and harmonized across pages. Different agents titled neighbouring SKUs, so siblings can
still differ in style. Your job is to find and fix those inconsistencies, and anything clearly
misleading. Do NOT re-title SKUs that are already consistent and correct. Precision is the top
priority: change a title only when you are sure the new one is better and every word is printed.

Read first:
- /home/user/product-namer/docs/pentair-title-rules.md
- your packet: /home/user/product-namer/data/work/pentair/harmonize/packets/{PACKET}.json (every
  active SKU in its catalog pages, current title, kind, product_line, pages, needs_review)
- the lines of /home/user/product-namer/data/work/pentair/rule_issues.md that mention your SKUs or
  say "sibling audit"

Evidence for any SKU (every page's printed row) is in the SQLite table `evidence` of
/home/user/product-namer/data/catalog.db (`SELECT pdf_page, title, source_row, context, notes FROM
evidence WHERE mpn = ?`). Page images: /home/user/product-namer/data/raw/pentair/pdf/png/pNNN.png.

Catalog-wide conventions (apply them; they settle questions earlier agents raised):
1. **Generic noun prefix** (parts with no trademark family): the product noun shared by every line
   that lists the SKU goes first, then specs, colour, noun: "Pump 1.5 HP Almond Seal Plate Kit",
   "Filter Lid O-Ring", "Multiport Valve 2 in Cover O-Ring". Plain hardware (bolts, screws, nuts,
   washers, studs, keys, pins, plugs) never takes the prefix and keeps the noun last
   ("3/8-16 x 7/8 in 18-8 SS Hex Head Bolt"). O-rings, gaskets, seals and every other part do.
   Drop the prefix when the title already names the noun in a fit ("… for Pumps Made Before …").
2. **Heat pumps vs heaters:** parts listed only on heat-pump pages (UltraTemp®, ThermalFlo®,
   UltraTemp ETi® hybrid) use "Heat Pump"; parts listed only on gas-heater pages use "Heater";
   parts on both use no prefix.
3. **Date fits:** "for {Noun}s Made Before/After {date as printed}" ("Made", never "Mfg." or
   "Manufactured").
4. **Counts:** pack sizes ", Set of N"; kit contents "N-Screw Kit" / "3-Gasket Kit".
5. **Spec wording within a section is uniform:** pick the form printed most often in the section for
   the same spec ("1 Phase" vs "1PH", "1-Speed" vs "1SP", "SS" vs "S/S", "in" units) and apply it to
   every sibling. Expanding an abbreviation is allowed when the full form is printed in the section.
6. **Trademarks:** the line's directory spelling with its mark wherever a Pentair line is named,
   including inside "for …" fits; third-party names (Hayward®, Jacuzzi®) as printed with their mark.
7. **Misleading breadth:** a no-family title whose spec implies a broader fit than printed (e.g.
   "Pump 3.0 HP Impeller" listed only for IntelliFlo3®/IntelliPro3®) adds "for {lines}" when the SKU
   is listed under at most three lines.
8. **Sibling sets** (same table, same page, colour/size variants, pool/spa pairs, almond/black twins)
   must share one pattern: the same family/prefix form, word order and spec style.
9. Never invent a word; never change brand or status; never merge or drop a SKU.

Write ONLY the SKUs you change to /home/user/product-namer/data/work/pentair/harmonize/out/{PACKET}.json:

```json
{"packet": "{PACKET}", "decisions": [
  {"mpn": "354808S", "title": "Pentair 354808S - Pump 3 HP 1-Speed 3 Phase TEFC 208-230/460V Motor",
   "product_line": "", "kind": "part", "confidence": "high",
   "reason": "sibling motors on p440-p444 use '1-Speed 3 Phase'; '3 Ph' expanded (printed on p442)"}
]}
```

(An empty `decisions` list is fine if nothing needs changing.) Then run
`python3 scripts/harmonize_check.py {PACKET}` from the repo root and fix every problem it reports,
including duplicate titles it finds against other SKUs.

Write only your decision file (scratch files may go in
/home/user/product-namer/data/work/pentair/scratch/audit/{PACKET}/). Do not edit anything else and
do not commit.

Report back briefly: SKUs in the packet, titles changed and the main patterns fixed, any decision at
confidence "review" and why, and anything that looked wrong but you left alone.
