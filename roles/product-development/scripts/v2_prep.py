"""Build batches for the v2 retitle (docs/title-rules-v2.md).

  python3 scripts/v2_prep.py

Every active SKU in data/catalog.db goes into one batch (data/work/pentair/v2/batches/bNN.json).
Batches are built from whole catalog pages: SKUs are grouped by the page their title came from,
and pentair.com-only SKUs are grouped by product URL. Each SKU carries all of its printed
evidence rows, so a reviewer can see every page that describes it.
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/work/pentair/v2/batches"
MAX = 70


def main() -> int:
    con = sqlite3.connect(ROOT / "data/catalog.db")
    ev = defaultdict(list)
    for mpn, page, ptype, row, ctx in con.execute(
            "SELECT mpn, pdf_page, page_type, source_row, context FROM evidence ORDER BY mpn, pdf_page"):
        ev[mpn].append({"pdf_page": page, "page_type": ptype, "row": row, "context": ctx})
    groups = defaultdict(list)
    for mpn, brand, kind, line, title, page, source in con.execute(
            "SELECT mpn, brand, kind, product_line, title, title_pdf_page, source FROM products ORDER BY title_pdf_page, mpn"):
        key = f"p{page:03d}" if page else source.replace("pentair.com product page ", "")
        groups[key].append({"mpn": mpn, "old_brand": brand, "kind": kind, "product_line": line,
                            "old_title": title, "evidence": ev[mpn]})
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("b*.json"):
        old.unlink()
    batches, cur = [], []
    for key in sorted(groups, key=lambda k: (not k.startswith("p"), k)):
        if cur and sum(len(g["skus"]) for g in cur) + len(groups[key]) > MAX:
            batches.append(cur)
            cur = []
        cur.append({"source": key, "skus": groups[key]})
    if cur:
        batches.append(cur)
    for i, b in enumerate(batches, 1):
        (OUT / f"b{i:02d}.json").write_text(json.dumps({"batch": f"b{i:02d}", "groups": b}, indent=1, ensure_ascii=False))
    print(f"{sum(len(g['skus']) for b in batches for g in b)} SKUs in {len(batches)} batches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
