"""Cut the catalog into phase-3 data batches (3-4 pages in reading order, never across a section).

  python3 scripts/d3_prep.py      # writes data/work/pentair/d3/batches/dNNN.json

Each batch lists its pages (packet path, page image) and every SKU printed on them, with its
final title, brand and status, so the extraction agent knows what it's attaching data to.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/work/pentair"
OUT = WORK / "d3/batches"
FIRST, LAST = 9, 538  # pages 1-8 are covers, directory and info; 539-540 back matter
MAX_PAGES = 4


def section(tab: str) -> str:
    """Side tabs are sometimes doubled by the PDF text layer; the first word is enough to group."""
    t = tab.upper()
    if len(re.findall(r"(.)\1", t)) > len(t) / 3:  # "PPLLEEAATTCCOO": every letter printed twice
        t = re.sub(r"(.)\1", r"\1", t)
    words = re.findall(r"[A-Z]+", t)
    head = " ".join(words[:2]) if words else ""
    return "PARTS:" + head if "PART" in t else head


def main() -> int:
    con = sqlite3.connect(ROOT / "data/catalog.db")
    titles = {m: (b, t) for m, b, t in con.execute("SELECT mpn, brand, title FROM products")}
    excluded = json.loads((WORK / "excluded_mpns.json").read_text())
    on_page = defaultdict(list)
    for mpn, page, row in con.execute("SELECT mpn, pdf_page, source_row FROM evidence WHERE pdf_page > 0"):
        on_page[page].append((mpn, row))
    # excluded SKUs have no evidence rows left; find them in the page reviews so they can be skipped knowingly
    for p in (WORK / "reviews_final").glob("p*.json"):
        r = json.loads(p.read_text())
        for rec in r.get("records", []):
            if rec["mpn"] in excluded:
                on_page[r["page"]].append((rec["mpn"], rec.get("source_row", "")))

    pages = []
    for n in range(FIRST, LAST + 1):
        pk = WORK / f"packets/p{n:03d}.json"
        if pk.exists():
            pages.append((n, section(json.loads(pk.read_text()).get("side_tab") or "")))
    batches, cur = [], []
    for n, sec in pages:
        if cur and (len(cur) == MAX_PAGES or sec != cur[-1][1]):
            batches.append(cur)
            cur = []
        cur.append((n, sec))
    batches.append(cur)

    OUT.mkdir(parents=True, exist_ok=True)
    for i, b in enumerate(batches, 1):
        doc = {"batch": f"d{i:03d}", "section": b[0][1], "pages": []}
        for n, _ in b:
            skus, seen = [], set()
            for mpn, row in sorted(on_page.get(n, [])):
                if mpn in seen:
                    continue
                seen.add(mpn)
                if mpn in titles:
                    skus.append({"mpn": mpn, "brand": titles[mpn][0], "title": titles[mpn][1], "row": row})
                elif mpn in excluded:
                    skus.append({"mpn": mpn, "excluded": excluded[mpn], "row": row})
            doc["pages"].append({"page": n, "packet": str(WORK / f"packets/p{n:03d}.json"),
                                 "image": str(ROOT / f"data/raw/pentair/pdf/png/p{n:03d}.png"), "skus": skus})
        (OUT / f"{doc['batch']}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    print(len(batches), "batches,", sum(len(b) for b in batches), "pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
