"""Build reports/title-check-v2.html: 40 SKUs retitled under docs/title-rules-v2.md for Matthew to check."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data/work/pentair/v2_sample"
sample = json.loads((D / "sample.json").read_text())["sample"]
a = {r["mpn"]: r for r in json.loads((D / "a.json").read_text())}
b = {r["mpn"]: r for r in json.loads((D / "b.json").read_text())}
# Where the two passes differed: the pick, and a question when Matthew has to decide.
PICK = {
 "AD075X-5753-N12": ("a", "Pentair prints the voltage as “525-600 VAC”. I wrote “525-600V” to match “120V” elsewhere. Keep VAC?"),
 "230163": ("b", ""),
 "011077": ("b", ""),
 "R161180": ("Pentair R161180 - No. 2 pH Test Solution 1 oz, Display Box", "“Display box” is the only printed difference from R161178 (same solution, no display box), so I kept it at the end. Right?"),
 "PFS2448": ("a", ""),
 "219300": ("a", ""),
 "356788": ("a", ""),
 "580202": ("b", ""),
 "154512Z": ("b", "Pentair describes this wrench two ways: “Wrench, 6-1/2 in. across flats” (Tagelus® parts, p356) and “Wrench, 6 in. closure” (Triton® II parts, p358). Which wording should win when pages differ?"),
 "470161": ("Pentair 470161 - #10 x 1 in Almond Button Head Torx Screw", "Pentair contradicts itself: pp401 and 403 print “Screw #10 x 1 in. Button Head Torx, Almond Head”, but p399 prints “Lid Bracket Screws, Square Drive, Almond”. I went with the two pages that agree (Torx). Right?"),
 "RCS1": ("a", "The accessories table (p19) calls it “Additional Spa Jets Switch”. Three parts lists (pp327, 328, 330) call it “Spa Jets Switch, Wall Mount, Single Gang Plate”. I used the parts-list wording."),
 "475002": ("Sta-Rite 475002 - Air Intake Kit", "The Max-E-Therm® page (p102) prints “Air Intake Kit”; the shared heater accessories table (p104) prints “Direct Air Intake Duct Kit (Max-E-Therm)”. I used the product page's wording."),
 "619113": ("b", ""),
}
ASK_SAME = {
 "79206600": "Printed “Small PVC niche, concrete”. I put “Concrete” just before the noun. Should it lead instead (“Concrete Small PVC Niche”)?",
 "261173": "Whole-good fit tails are dropped, but “for Triton & Quad D.E. Filters” is the only printed difference from 261177 (the 1-1/2 in kit for FNS filters), so it stays.",
 "ULTRA-B10": "No sq ft is printed (“Optimized”). ULTRA-B2 and ULTRA-B3 have the same dimensions, so the printed “Upgrade for PWWCT200” stays to tell them apart.",
 "075142": "Pentair abbreviates “Subassy” and never spells it out, so it stays as printed. Expand to “Subassembly”?",
 "270067": "“Assy” is printed and never spelled out on these pages, so it stays. Expand to “Assembly”?",
 "155702": "Printed “Kit-THS3461, single tank manifold, with butterfly valve kit”. I dropped the first “Kit” so the title doesn't say Kit twice.",
 "523525Z": "Two rows on this page print “Controller Circuit Board” under different bands, so “Title-22” from the band tells them apart.",
}
items = []
for mpn, brand, kind, page, line, old in sample:
    pick, ask = PICK.get(mpn, ("a", ASK_SAME.get(mpn, "")))
    new = {"a": a[mpn]["title"], "b": b[mpn]["title"]}.get(pick, pick)
    nb, nt = new.split(" ", 1)[0], new.split(" - ", 1)[1]
    group = {"whole_good": "Whole good", "part": "Part", "accessory": "Accessory"}[kind] + (f" · brand now {nb}" if nb != brand else "")
    items.append({"id": mpn.replace(" ", "_"), "mpn": mpn, "group": group, "brand": nb,
                  "now": old.split(" - ", 1)[1], "draft": nt, "fields": "", "ask": ask, "oldbrand": brand,
                  "crop": f"img/{mpn.replace(' ', '_')}_p{page}.png", "page": f"pages/page{page:03d}.jpg", "pno": page})
items.sort(key=lambda x: (not x["ask"],))
review = (ROOT / "reports/pentair-review.html").read_text()
css = review[review.index("<style>"): review.index("</style>\n<style>")] + "</style>"
header = '''  <header>
    <div class="eyebrow">Pool Geek · Pentair titles · Check v2</div>
    <h1>40 titles under your new rules</h1>
    <p class="lede">I wrote down the rules from both training rounds, then had two independent passes retitle 40 SKUs you haven't seen. They agreed on 27; I settled the rest. The first 13 cards carry a note where I made a call you may disagree with. Tap “New title is right”, or type your version. “Show full PDF page” opens the whole catalog page; swipe sideways on a phone.</p>
  </header>

  <div class="rule">
    <h3>What changed since your last answers</h3>
    <ul>
      <li>Discontinued and not-for-USA SKUs are out of the database (1,106 numbers); 4,735 remain.</li>
      <li>Parts and accessories now follow their line's brand. In this sample: C2-66 (D Series™ page carries the Sta-Rite logo) and 475002 (Max-E-Therm®) are Sta-Rite; 351089Z and 354545S are listed under both Pentair and Sta-Rite pumps, so they are Pentair/Sta-Rite.</li>
      <li>The rules are written up in docs/title-rules-v2.md.</li>
    </ul>
  </div>
'''
html = ((ROOT / "scripts/training_template.html").read_text().replace("/*CSS*/", css)
        .replace("/*ITEMS*/", json.dumps(items, ensure_ascii=False, indent=0)).replace("/*QUESTIONS*/", "[]")
        .replace("/*HEADER*/", header).replace("/*ITEMS_HEADING*/", "The 40 titles")
        .replace("/*LABELS*/", json.dumps(["Old", "New", "New title is right"]))
        .replace("<title>Pentair Title Training</title>", "<title>Pentair Title Check</title>"))
html = html.replace('d.brand + " " + d.mpn + " - " + d.now', '(d.oldbrand || d.brand) + " " + d.mpn + " - " + d.now')
(ROOT / "reports/title-check-v2.html").write_text(html)
print(len(items), "items;", sum(1 for i in items if i["ask"]), "with notes")
