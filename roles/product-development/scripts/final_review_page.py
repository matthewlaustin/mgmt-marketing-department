"""Build reports/v2-final-review.html: the group questions and spot-check after the full v2 retitle."""
import csv
import html
import io
import json
import random
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/work/pentair/v2/final"
BATCHES = ROOT / "data/work/pentair/v2/batches"
V1_COMMIT = "59b39e7"  # last export before the v2 titles were loaded

v2, evidence = {}, {}
for p in sorted(FINAL.glob("b*.json")):
    for r in json.loads(p.read_text()):
        v2[r["mpn"]] = r
for p in sorted(BATCHES.glob("b*.json")):
    for g in json.loads(p.read_text())["groups"]:
        for s in g["skus"]:
            evidence[s["mpn"]] = s["evidence"]
old = {r["mpn"]: r["title"] for r in csv.DictReader(io.StringIO(
    subprocess.check_output(["git", "show", f"{V1_COMMIT}:data/exports/pentair_skus.csv"], cwd=ROOT, text=True)))}


def tail(title: str) -> str:
    return title.split(" - ", 1)[1] if " - " in title else title


unsure = sum(bool(r.get("unsure")) for r in v2.values())
gaps = sum(bool(r.get("gap")) for r in v2.values())
changed = sum(1 for m, r in v2.items() if r["title"] and old.get(m) != r["title"])

Q = [
 {"id": "f-bare", "title": "Short part titles: add the product line in front?",
  "detail": "Following your “Pump Volute” example, part titles name the part and leave out what it fits. 639 titles are two words or less. The old titles often led with the product line.",
  "examples": [["Now", "Pentair R172400 - Inlet Screen"], ["With line", "Pentair R172400 - Dynamic® Chlorine/Bromine Dispenser Inlet Screen"],
               ["Now", "Pentair LLU6 - White Feed Mast with O-Ring"], ["With line", "Pentair LLU6 - Kreepy Krauly® White Feed Mast with O-Ring"]],
  "choices": ["Keep them short", "Add the line when the title is 1–3 words", "Always add the line on parts"]},
 {"id": "f-wordorder", "title": "Colour or pool type first?",
  "detail": "You approved “Set of 5 IntelliVibe Mezzo Fiberglass/Gunite Black Trim Rings” (pool type, then colour). The rule I wrote puts colour first: “White PVC Gunite Skimmer”. About 60 titles follow one or the other.",
  "examples": [["Rule as written", "Bermuda™ 2 in Slip Ports White PVC Gunite Skimmer"],
               ["Your trim rings, full", "Set of 5 IntelliVibe™ Mezzo Fiberglass/Gunite Black Trim Rings"], ["Colour first", "QuikSkim Tan Fiberglass Square Frame"]],
  "choices": ["Colour first (White PVC …)", "Pool type or material first (Fiberglass/Gunite Black …)"]},
 {"id": "f-zpairs", "title": "Numbers with and without a Z",
  "detail": "You told me a number and its Z version are the same part. In 32 of 55 pairs the catalog prints them as different parts, so each title follows its own printed row.",
  "examples": [["400100", "Keypad Cover"], ["400100Z", "Almond Drive Control Cover Assembly Kit for Pumps Made After 12/23/13"],
               ["154512", "1-1/2 in Flanged Valve Wrench"], ["154512Z", "6-1/2 in Across Flats Wrench"]],
  "choices": ["Keep each one's printed wording", "Make the Z match the plain number", "List the 32 pairs for me"]},
 {"id": "f-ec", "title": "EC- (e-commerce) numbers",
  "detail": "pentair.com sells 47 “EC-” numbers that match a dealer number except for the sales channel (“Products beginning with EC- are exclusive to e-commerce sales”). They now share the dealer number's title.",
  "examples": [["Dealer", "Pentair 160316 - Clean & Clear® CC 100 Filter"], ["Online", "Pentair EC-160316 - Clean & Clear® CC 100 Filter"]],
  "choices": ["Same title is fine", "Add “Online” at the end", "Leave EC- numbers out"]},
 {"id": "f-notsold", "title": "Parts Pentair says aren't sold on their own",
  "detail": "350082 is printed “not sold individually – order assy. kit”, 274440Z “may not be purchased separately”, and 272415Z only appears as kit contents. None is marked discontinued.",
  "choices": ["Keep them", "Leave them out like discontinued items"]},
 {"id": "f-ecdisc", "title": "Online numbers for discontinued IntelliChlor® cells",
  "detail": "The catalog marks 520554, 520555, 520888 and 521105 discontinued, but pentair.com sells EC-520554, EC-520555, EC-520888 and EC-521105 (“A familiar favorite is back”).",
  "choices": ["Keep the EC- numbers", "Leave them out"]},
 {"id": "f-stark", "title": "Stark™ and AQ numbers that need an option letter",
  "detail": "94 Stark and 5S/AQ rows print a base number that is ordered with an option letter. They are titled but marked unsure.",
  "examples": [["Example", "Pentair RS1-60-04 - Stark™ SS Series 1-Tank 36 in x 60 in Sand Filtration System"]],
  "choices": ["Keep the base numbers", "Leave them out"]},
 {"id": "f-commercial", "title": "“Commercial” in line names",
  "detail": "Pentair prints “Commercial IntelliChlor®”, “Commercial IntelliChem®” and BioShield® CLP/CVP systems. I left “Commercial” out as a sales word and marked about 40 SKUs unsure.",
  "examples": [["Without", "IntelliChlor® Salt Chlorine Generator System"], ["With", "Commercial IntelliChlor® Salt Chlorine Generator System"]],
  "choices": ["Leave it out", "Keep it (it's part of the line name)"]},
 {"id": "f-identical", "title": "Rows Pentair prints identically",
  "detail": "Some numbers share a row word for word, such as three “O-Ring” rows on p508 or twelve Amerlite® lights whose web rows leave out cord length. They share one title.",
  "examples": [["35505-1116Z / -1246Z / -1318Z", "O-Ring"], ["78441100 / 78449100 / 78949100", "Amerlite® Incandescent 400W Light with Stainless Steel Face Ring"]],
  "choices": ["Sharing a title is fine", "Leave them untitled until Pentair prints a difference"]},
 {"id": "f-counts", "title": "Counts on pump parts lists",
  "detail": "Pump parts lists print counts like “(X4)” or “2 req.”: how many one pump uses. I left them out, assuming each number is one piece.",
  "examples": [["Printed", "Motor bolts (X4)"], ["Title", "Pentair/Sta-Rite 074165Z - Motor Bolts"]],
  "choices": ["Right, sold one at a time", "They are packs: write “Set of 4”"]},
 {"id": "f-abbrev", "title": "Abbreviations no page spells out",
  "detail": "PCBA, HMI, ACC, PH MS, SIF, CS, HD, “Standard E” and the HP in “Control/HP Panel” stay as printed because no Pentair page spells them out.",
  "examples": [["Example", "Pentair 350107Z - 10-24 x 3-1/4 in PH MS 18-8 Stainless Steel Screw"]],
  "choices": ["Keep as printed", "Spell out my best reading", "Leave the word out"]},
 {"id": "f-misspell", "title": "Misspellings in Pentair's rows",
  "detail": "Where the catalog spells the word right somewhere else I corrected it (Bunan → Buna-N, IntelliVavle → IntelliValve®, Assemby → Assembly). “Mitrile” and “Kratom” stay as printed because the right word appears nowhere.",
  "examples": [["Kept", "Sta-Rite 14971-SM20E12 - 2 in Valve Kratom Spider Gasket"]],
  "choices": ["Correct obvious ones, even if not printed elsewhere", "Correct only from Pentair's own spelling (as now)", "Always keep as printed"]},
 {"id": "f-words", "title": "Words that might be marketing",
  "detail": "Pick the ones to keep in titles. Today “Super-Duty” and “Professional Grade” are dropped; “Efficient” (355011S motor) and “High Powered” (520639 kit) are kept because they tell two parts apart; “Variable Speed” is shortened to the model name “VS”.",
  "multi": True, "choices": ["Super-Duty", "Professional Grade", "Efficient", "High Powered", "Variable Speed (spelled out)"]},
 {"id": "f-calls", "title": "The other 120 calls I made during the run",
  "detail": "They are listed above under “Calls made during the run”. Most settle how a printed row turns into a title (brackets, footnotes, dates, models, ties between pages).",
  "choices": ["Accept them all", "Accept, with the changes in my note"]},
]

random.seed(25)
sure = sorted(m for m, r in v2.items() if r["title"] and not r.get("unsure") and m in evidence)
items = []
for m in random.sample(sure, 10):
    r = v2[m]
    rows = [f"p{e['pdf_page']}: {e['row']}" if e.get("pdf_page") else f"pentair.com: {e['row']}" for e in evidence[m][:3]]
    items.append({"id": "s-" + re.sub(r"[^A-Za-z0-9]", "", m), "group": r["brand"], "mpn": m, "brand": r["brand"],
                  "now": tail(old.get(m, "")) or "(none)", "draft": tail(r["title"]), "web": "\n".join(rows), "url": ""})

calls = []
text = (ROOT / "docs/title-rules-v2.md").read_text()
for line in text[text.index("## Interim calls"):].splitlines():
    if line.startswith("- "):
        calls.append(line[2:])
    elif line.startswith("  ") and calls:
        calls[-1] += " " + line.strip()
calls_html = "".join(f"<li>{html.escape(c).replace('**', '')}</li>" for c in calls)

review = (ROOT / "reports/pentair-review.html").read_text()
css = review[review.index("<style>"): review.index("</style>\n<style>")] + "</style>"
header = f'''  <header>
    <div class="eyebrow">Pool Geek · Pentair titles · Final review</div>
    <h1>All {len(v2):,} Pentair titles are done</h1>
    <p class="lede">Every active Pentair SKU now has a title under your rules: two independent passes per batch, a third look where they disagreed, then a consistency check across the catalog. {changed:,} titles changed from the first version. {gaps} SKUs have no printed description, so they stay untitled.</p>
    <p class="lede">{unsure} titles are marked unsure. Most of them hang on the {len(Q) - 1} questions below, so one answer settles many SKUs. The ten titles at the bottom are a random spot-check.</p>
    <details class="rule"><summary>Calls made during the run ({len(calls)})</summary><ul>{calls_html}</ul></details>
  </header>
'''
html_out = ((ROOT / "scripts/training_template.html").read_text().replace("/*CSS*/", css)
            .replace("/*ITEMS*/", json.dumps(items, ensure_ascii=False))
            .replace("/*QUESTIONS*/", json.dumps(Q, ensure_ascii=False, indent=0))
            .replace("/*FOOTER*/", "Rows are from the Pentair Pool Product Catalog 2025-2026 (Dec 2025 digital edition) and pentair.com.")
            .replace("/*HEADER*/", header).replace("/*ITEMS_HEADING*/", "Spot-check: 10 random titles")
            .replace("/*LABELS*/", json.dumps(["Before", "Now", "Looks right"]))
            .replace("ev.append(w, a);", "ev.append(w); if (d.url) ev.append(a);")
            .replace(".webrow { ", ".webrow { white-space: pre-wrap; ")
            .replace("<title>Pentair Title Training</title>", "<title>Pentair Final Review</title>"))
(ROOT / "reports/v2-final-review.html").write_text(html_out)
print(len(Q), "questions,", len(items), "spot-checks,", len(calls), "calls")
