"""Phase 2: build packets of Pentair website-only SKUs to title from Pentair's own product pages.

  python3 scripts/web_prep.py        # after pentair_web_specs.py and consolidate.py

A website-only SKU is listed on a pentair.com product page but appears nowhere in the 2025-26
catalog (data/catalog.db). Each packet (data/work/pentair/web/packets/wNN.json) groups whole product
pages and carries, per SKU, every spec-table row Pentair publishes for it, plus the catalog titles of
the page's other SKUs as style anchors. SKUs with no spec-table row are listed in
data/work/pentair/web/no_description.json (a gap, not a guess).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/work/pentair"
OUT = WORK / "web/packets"
MAX_SKUS = 45


def unique_rows(rows: list[dict]) -> list[dict]:
    """A page shows its table twice (short and full view); keep each published row once."""
    seen, out = set(), []
    for r in rows:
        key = (r["url"], r["row_text"])
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def main() -> int:
    pages = json.loads((WORK / "web_skus.json").read_text())
    specs = json.loads((WORK / "web_specs.json").read_text())
    con = sqlite3.connect(ROOT / "data/catalog.db")
    catalog = {m: (t, st) for m, t, st in con.execute("SELECT mpn, title, status FROM products")}
    by_page: dict[str, list[str]] = defaultdict(list)
    no_desc = []
    for url, info in sorted(pages.items()):
        for sku in info.get("skus", []):
            if sku in catalog or sku.upper() in catalog:
                continue
            if sku in specs:
                by_page[url].append(sku)
            else:
                no_desc.append({"sku": sku, "url": url, "page_name": info.get("name", "")})
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("w*.json"):
        old.unlink()
    packets, current = [], []
    for url in sorted(by_page, key=lambda u: (u.split("/products/")[-1])):
        skus = by_page[url]
        if current and sum(len(p["skus"]) for p in current) + len(skus) > MAX_SKUS:
            packets.append(current)
            current = []
        anchors = [{"mpn": s, "title": catalog[s][0], "status": catalog[s][1]}
                   for s in pages[url]["skus"] if s in catalog][:25]
        current.append({"url": url, "page_name": pages[url].get("name", ""),
                        "catalog_titles_on_this_page": anchors,
                        "skus": [{"mpn": s, "rows": unique_rows(specs[s])} for s in skus]})
    if current:
        packets.append(current)
    seen = set()
    for i, groups in enumerate(packets, 1):
        name = f"w{i:02d}"
        (OUT / f"{name}.json").write_text(json.dumps({"packet": name, "pages": groups}, indent=1, ensure_ascii=False))
        seen |= {s["mpn"] for g in groups for s in g["skus"]}
    (WORK / "web/no_description.json").write_text(json.dumps(no_desc, indent=1, ensure_ascii=False))
    print(f"website-only SKUs with a Pentair description: {len(seen)} in {len(packets)} packets; "
          f"without one: {len(no_desc)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
