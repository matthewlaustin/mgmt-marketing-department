"""Build sibling-consistency audit packets (sNN): every active SKU, grouped by catalog section.

  python3 scripts/audit_prep.py          # after consolidate.py with all harmonization decisions applied

Writes data/work/pentair/harmonize/packets/sNN.json. Unlike hNN packets, an audit agent records
decisions only for the SKUs it changes; its decisions are applied after the hNN ones.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/work/pentair"
OUT = WORK / "harmonize/packets"
TARGET = 260


def main() -> int:
    con = sqlite3.connect(ROOT / "data/catalog.db")
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT mpn, brand, title, kind, product_line, pages, title_pdf_page, needs_review FROM products "
        "WHERE status = 'active' ORDER BY title_pdf_page, mpn")]
    tabs = {}
    for path in (WORK / "packets").glob("p*.json"):
        pk = json.loads(path.read_text())
        tabs[pk["page"]] = (pk.get("side_tab") or "", pk.get("heading") or "")
    for old in OUT.glob("s*.json"):
        old.unlink()
    packets, current = [], []
    for r in rows:
        # cut only between pages, so a page's siblings stay together
        if len(current) >= TARGET and r["title_pdf_page"] != current[-1]["title_pdf_page"]:
            packets.append(current)
            current = []
        r["section"], r["heading"] = tabs.get(r["title_pdf_page"], ("", ""))
        current.append(r)
    if current:
        packets.append(current)
    for i, skus in enumerate(packets, 1):
        name = f"s{i:02d}"
        pages = f"{skus[0]['title_pdf_page']}-{skus[-1]['title_pdf_page']}"
        (OUT / f"{name}.json").write_text(json.dumps({"packet": name, "pages": pages, "skus": skus},
                                                     indent=1, ensure_ascii=False))
        print(name, pages, len(skus))
    return 0


if __name__ == "__main__":
    sys.exit(main())
