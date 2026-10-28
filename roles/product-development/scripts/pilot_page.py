"""Build reports/v2-pilot.html: rule questions raised by the v2 retitle pilot (batches b01, b45)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q = [
 {"id": "intellicenter", "title": "IntelliCenter® bundles: which title?",
  "detail": "The bundled systems differ by personality kit and by what's included (IntelliChlor® cell, SCG transformer, two IntelliValves). Your rule says every varying column goes in, but the kit code already decides some of them. The two passes wrote 523962 differently.",
  "crops": ["img/p15_table.png"],
  "examples": [["Pass A", "IntelliCenter® i5P System with IntelliChlor® ICPLUS40 Cell and Salt Chlorine Generator Transformer"],
               ["Pass B", "IntelliCenter® System with i5P Personality Kit and IntelliChlor® ICPLUS40 Cell"],
               ["Shortest", "IntelliCenter® i5P System with IntelliChlor® ICPLUS40 Cell"]],
  "choices": ["Pass A", "Pass B", "Shortest", "Something else (note)"]},
 {"id": "lil-shark", "title": "Whole goods: keep a “for …” that is part of Pentair's name?",
  "detail": "Your rule drops fit tails from whole goods. Pentair names this cleaner “'Lil Shark Automatic Pool Cleaner for Aboveground Pools”, and “aboveground” is what sets it apart from the inground cleaners.",
  "crops": ["img/360100_p12.png"],
  "examples": [["Drop it", "Kreepy Krauly® 'Lil Shark™ Automatic Pool Cleaner"], ["Keep it", "Kreepy Krauly® 'Lil Shark™ Automatic Pool Cleaner for Aboveground Pools"]],
  "choices": ["Drop it", "Keep it", "Keep it only for pool type (aboveground, inground, spa)"]},
 {"id": "trademark", "title": "® and ™ on part and accessory titles",
  "detail": "Pentair's order rows usually print names without the mark (“IntelliCenter Indoor Control Panel, White Faceplate”), while headings print “IntelliCenter®”. The passes copied the row, so some titles carry the mark and some don't.",
  "crops": ["img/522035_p17.png"],
  "choices": ["Always add the registered mark", "Exactly as the row prints it", "Never on parts and accessories"]},
 {"id": "unclear-abbrev", "title": "Abbreviations nobody can spell out",
  "detail": "You asked for abbreviations to be spelled out. Some have no printed expansion and no single meaning, such as “Closure, 8-1/2 in. btr.” (154575Z) and “Bulkhead ASY 2 IN TR” (154714Z). The passes left those words out.",
  "crops": ["img/154575Z_p361.png"],
  "choices": ["Leave the unclear word out", "Keep it as printed", "Flag each one for me"]},
 {"id": "shaft-seal", "title": "356210S: Shaft Seal or Mechanical Seal?",
  "detail": "In training you titled it “Shaft Seal”, from the IntelliFlo3® page. Four other parts lists (Challenger®, SuperFlo®, SuperMax®) print “Seal, mechanical (ozone/salt resistant)”. Your newer rule says the wording most pages print wins.",
  "crops": ["img/356210S_p431.png", "img/356210S_p442.png"],
  "choices": ["Shaft Seal", "Mechanical Seal", "Ozone/Salt Resistant Mechanical Seal"]},
]
review = (ROOT / "reports/pentair-review.html").read_text()
css = review[review.index("<style>"): review.index("</style>\n<style>")] + "</style>"
header = '''  <header>
    <div class="eyebrow">Pool Geek · Pentair titles · Pilot</div>
    <h1>Pilot done: five calls before the full run</h1>
    <p class="lede">I retitled 112 SKUs in two catalog sections (IntelliCenter® and cleaners; Triton® and heater parts) with two independent passes under your rules. They agreed on 100. Most of the 12 differences come from the five questions below; I settled the rest with your existing rules. Each one affects many SKUs across the catalog, so I'd like your call before running the other 4,600.</p>
  </header>
'''
html = ((ROOT / "scripts/training_template.html").read_text().replace("/*CSS*/", css)
        .replace("/*ITEMS*/", "[]").replace("/*QUESTIONS*/", json.dumps(Q, ensure_ascii=False, indent=0))
        .replace("/*FOOTER*/", 'Rows are cropped from the Pentair Pool Product Catalog 2025-2026 (Dec 2025 digital edition).').replace("/*HEADER*/", header).replace("/*ITEMS_HEADING*/", "").replace("/*LABELS*/", json.dumps(["", "", ""]))
        .replace("<title>Pentair Title Training</title>", "<title>Pentair Title Pilot</title>"))
(ROOT / "reports/v2-pilot.html").write_text(html)
print(len(Q), "questions")
