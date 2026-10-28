"""Build reports/title-lookup.html: type a part number, see its title and the rows it came from."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
con = sqlite3.connect(ROOT / "data/catalog.db")
data = {}
for mpn, brand, title, kind, line in con.execute("SELECT mpn, brand, title, kind, product_line FROM products"):
    data[mpn] = {"b": brand, "t": title, "k": kind, "l": line or "", "e": []}
for mpn, page, ptype, row, ctx in con.execute(
        "SELECT mpn, pdf_page, page_type, source_row, context FROM evidence ORDER BY mpn, pdf_page"):
    if mpn in data and row:
        where = f"Catalog p{page}" if page else "pentair.com"
        data[mpn]["e"].append([where, row, ctx or ""])
excluded = json.loads((ROOT / "data/work/pentair/excluded_mpns.json").read_text())
LABEL = {"discontinued": "discontinued", "not_for_sale_usa": "not for sale in the USA",
         "not_sold_separately": "not sold on its own"}
out = {"p": data, "x": {m: LABEL.get(s, s.replace("_", " ")) for m, s in excluded.items()}}

page = (ROOT / "scripts/lookup_template.html").read_text().replace(
    "/*DATA*/", json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
(ROOT / "reports/title-lookup.html").write_text(page)
print(len(data), "titles,", len(excluded), "left out")
