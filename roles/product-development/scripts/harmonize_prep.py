"""Build work packets for the harmonization pass (one title per SKU across the whole catalog).

  python3 scripts/harmonize_prep.py              # after consolidate.py
  python3 scripts/harmonize_prep.py --leftover    # after all packets: one more packet for duplicates still left

Reads data/catalog.db and writes data/work/pentair/harmonize/packets/hNN.json. A SKU goes into a
packet when:
- its title differs between pages (conflicts table), or
- its derived title is shared with another active SKU (catalog-wide duplicate), or
- it is an active part with no product line (shared across lines: may need the generic noun).
SKUs that share a derived title always land in the same packet. Packets follow catalog page order
so one agent sees one product section.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/work/pentair"
OUT = WORK / "harmonize/packets"
MAX_SKUS = 45


def derived(title: str) -> str:
    return title.split(" - ", 1)[1] if " - " in title else title


def main() -> int:
    con = sqlite3.connect(ROOT / "data/catalog.db")
    con.row_factory = sqlite3.Row
    products = {r["mpn"]: dict(r) for r in con.execute("SELECT * FROM products")}
    conflicted = {r[0] for r in con.execute("SELECT DISTINCT mpn FROM conflicts WHERE field = 'title'")}
    by_derived: dict[str, list[str]] = defaultdict(list)
    for mpn, p in products.items():
        if p["status"] == "active" and p["title"]:
            by_derived[derived(p["title"])].append(mpn)
    dup_groups = [sorted(m) for m in by_derived.values() if len(m) > 1]
    no_line = {m for m, p in products.items()
               if p["status"] == "active" and p["kind"] == "part" and not p["product_line"]}
    wanted = conflicted | no_line | {m for g in dup_groups for m in g}
    leftover = len(sys.argv) > 1 and sys.argv[1] == "--leftover"
    if leftover:
        # duplicates that remain once every decision is applied, including SKUs that were in no packet
        sys.path.insert(0, str(ROOT / "scripts"))
        from harmonize_check import catalog_duplicates
        decided = {}
        for path in sorted((WORK / "harmonize/out").glob("h*.json")):
            for d in json.loads(path.read_text()).get("decisions", []):
                decided[d["mpn"]] = d
        for m, d in decided.items():
            if m in products:
                products[m].update(title=d["title"], product_line=d.get("product_line", products[m]["product_line"]))
        dup_groups = [sorted(ms) for ms, _msg in catalog_duplicates()]
        wanted = {m for g in dup_groups for m in g}
        conflicted, no_line = conflicted & wanted, set()

    # units: a duplicate-title group or a single SKU; ordered by first catalog page
    in_group = {m: g for g in dup_groups for m in g}
    units, seen = [], set()
    for mpn in wanted:
        if mpn in seen:
            continue
        unit = in_group.get(mpn, [mpn])
        seen.update(unit)
        first = min(int(pg) for m in unit for pg in products[m]["pages"].split(","))
        units.append((first, unit))
    units.sort()

    evidence = defaultdict(list)
    for r in con.execute("SELECT * FROM evidence ORDER BY pdf_page"):
        evidence[r["mpn"]].append({k: r[k] for k in ("pdf_page", "page_type", "brand", "title", "kind", "status",
                                                     "source_row", "context", "confidence", "notes")})
    headings = {}
    for path in (WORK / "packets").glob("p*.json"):
        pk = json.loads(path.read_text())
        headings[pk["page"]] = {k: pk.get(k) for k in ("heading", "subtitle", "side_tab")}

    OUT.mkdir(parents=True, exist_ok=True)
    first_number = 1
    if leftover:
        first_number = len(list(OUT.glob("h*.json"))) + 1
    else:
        for old in OUT.glob("h*.json"):
            old.unlink()
    packets, current = [], []
    for _first, unit in units:
        if current and len(current) + len(unit) > MAX_SKUS:
            packets.append(current)
            current = []
        current.extend(unit)
    if current:
        packets.append(current)
    for i, mpns in enumerate(packets, first_number):
        items = []
        for m in mpns:
            p = products[m]
            pages = sorted({e["pdf_page"] for e in evidence[m]})
            items.append({
                "mpn": m, "brand": p["brand"], "current_title": p["title"], "kind": p["kind"],
                "product_line": p["product_line"], "status": p["status"],
                "why": [w for w, cond in (("title differs between pages", m in conflicted),
                                          ("derived title shared with " + ", ".join(x for x in in_group.get(m, []) if x != m),
                                           m in in_group),
                                          ("part with no product line", m in no_line)) if cond],
                "page_headings": {pg: headings.get(pg) for pg in pages},
                "evidence": evidence[m],
            })
        (OUT / f"h{i:02d}.json").write_text(json.dumps({"packet": f"h{i:02d}", "skus": items}, indent=1, ensure_ascii=False))
    print(f"SKUs: {len(wanted)} (conflicts {len(conflicted)}, duplicate-title groups {len(dup_groups)}, "
          f"no-line parts {len(no_line)}); packets: {len(packets)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
