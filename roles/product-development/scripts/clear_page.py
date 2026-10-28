"""Build reports/v2-last-ten.html: the last 10 Pentair SKUs that need Matthew (6 questions, 4 gaps)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q = [
 {"id": "c-170040", "title": "170040: manifold or manifold assembly?",
  "detail": "Two filter lines print the same number for different-looking parts at very different prices.",
  "examples": [["p334 Clean & Clear® Plus", "Manifold, bottom · $95.34"], ["p348 Quad D.E.®", "Manifold assy. Bottom · $264.84"]],
  "choices": ["Bottom Manifold Assembly", "Bottom Manifold", "Not sure: leave it out"]},
 {"id": "c-EC110", "title": "EC110: turbine shaft or turbine cover?",
  "detail": "Same number, same price, different part names on two Kreepy Krauly® lists.",
  "examples": [["p311 Platinum™", "Turbine Shaft w/ Elbow - White · $22.04"], ["p313 Legend®", "Turbine Cover w/ Elbows · $22.04"]],
  "choices": ["White Turbine Shaft with Elbow", "Turbine Cover with Elbows", "Not sure: leave it out"]},
 {"id": "c-521057Z", "title": "521057Z: which load center base?",
  "detail": "Same number and price, different ratings. p328 also lists 520656 as the 150A 10-circuit part before the 2011 change date.",
  "examples": [["p327 IntelliTouch®", "New Load Center 150A 10 Circuit Breaker Base · $422.24"], ["p328 EasyTouch®", "Load Center 125A 8 Circuit Breaker (size), after change date 2011 · $422.24"]],
  "choices": ["150A 10 Circuit", "125A 8 Circuit", "Not sure: leave it out"]},
 {"id": "c-472734", "title": "472734: the kit or just the board?",
  "examples": [["p401 UltraTemp®", "BEZEL, CONTRL BOARD & LABEL KIT · $718.68"], ["p403 ThermalFlo™", "Control Board Assembly (no price)"]],
  "choices": ["Bezel, Control Board & Label Kit", "Control Board Assembly"]},
 {"id": "c-drivecovers", "title": "358215 and 358216: drive covers named only in ordering notes",
  "detail": "Neither number has its own row. They appear only inside the notes of drive-cover rows, and the notes point 358215 at two different covers. Both are titled “Drive Cover” for now.",
  "examples": [["p439 WhisperFlo® VST", "Drive Cover (before May 2025 order 358211; May 2025 or later order 358215)"],
               ["p447 SuperFlo® VS", "Drive Cover (RS-485), Almond (before May 2025 order 358211; May 2025 or later order 358215)"],
               ["p447 SuperFlo® VS", "Drive Cover (before May 2025 order 358215; May 2025 or later order 358216)"]],
  "choices": ["Keep both as “Drive Cover”", "Leave both out", "Something else (note)"]},
 {"id": "c-gaps", "title": "Four numbers with no description at all",
  "detail": "Pentair prints nothing that says what these are, so they have no title.",
  "examples": [["152519Z", "p357 Triton® II list: item 6 with a price ($172.36), description blank"],
               ["360269", "p306 Racer® cleaner: a drawing label only, no table row"],
               ["79211600", "pentair.com niches table: number only (the catalog lists 79211600Z, a niche plaster ring)"],
               ["PKG 188", "pentair.com Parts-Paks™: number only (PKG 188Z is a 2 in slip union kit)"]],
  "choices": ["Leave them out", "Keep them, untitled"]},
]
review = (ROOT / "reports/pentair-review.html").read_text()
css = review[review.index("<style>"): review.index("</style>\n<style>")] + "</style>"
header = '''  <header>
    <div class="eyebrow">Pool Geek · Pentair titles · Last items</div>
    <h1>The last ten Pentair SKUs</h1>
    <p class="lede">Everything else is settled. These six questions cover the ten SKUs where the catalog contradicts itself in a way that changes what a buyer would receive, or prints nothing at all. Each row below is copied from Pentair's own pages.</p>
  </header>
'''
html = ((ROOT / "scripts/training_template.html").read_text().replace("/*CSS*/", css)
        .replace("/*ITEMS*/", "[]").replace("/*QUESTIONS*/", json.dumps(Q, ensure_ascii=False, indent=0))
        .replace("/*FOOTER*/", "Rows are from the Pentair Pool Product Catalog 2025-2026 (Dec 2025 digital edition) and pentair.com.")
        .replace("/*HEADER*/", header).replace("/*ITEMS_HEADING*/", "").replace("/*LABELS*/", json.dumps(["", "", ""]))
        .replace(".trow { display: grid; grid-template-columns: 64px", ".trow { display: grid; grid-template-columns: minmax(90px, 30%)")
        .replace("<title>Pentair Title Training</title>", "<title>Pentair Last Ten</title>"))
(ROOT / "reports/v2-last-ten.html").write_text(html)
print(len(Q), "questions")
