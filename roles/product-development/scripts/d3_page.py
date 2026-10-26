"""Print everything phase 3 extracted for one catalog page, for checking against the page image.

  python3 scripts/d3_page.py 431
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data/work/pentair/d3/out"


def main(page: int) -> None:
    for path in sorted(OUT.glob("d*.json")):
        d = json.loads(path.read_text())
        fams = [f for f in d.get("families", []) if f.get("page") == page]
        prods = [p for p in d.get("products", []) if p.get("page") == page]
        fits = {}
        for f in d.get("fitment", []):
            if f.get("page") == page:
                fits.setdefault(f["part"], []).append(f)
        refs = [r for r in d.get("references", []) if r.get("page") == page]
        if not (fams or prods or fits or refs):
            continue
        print(f"== {path.stem} p{page}")
        for f in fams:
            print(f"FAMILY {f['id']} | {f.get('name')} | parent={f.get('parent')} | links={f.get('links')}")
        for p in prods:
            pr = p.get("prices") or {}
            price = f"${pr.get('us_list')}/{pr.get('can_list')}" if pr else (p.get("price_note") or "")
            specs = "; ".join(f"{s['attr']}={s['value']}" for s in p.get("specs", []))
            print(f"{p['mpn']:<14} {p['role']:<11} {price:<18} {specs}")
            for f in fits.pop(p["mpn"], []):
                print(f"   fits {f.get('fits')} item={f.get('item')} qty={f.get('qty')} cond={f.get('condition')}")
        for part, fs in fits.items():
            for f in fs:
                print(f"{part:<14} fits {f.get('fits')} item={f.get('item')} qty={f.get('qty')} cond={f.get('condition')}")
        for r in refs:
            print(f"REF {r['kind']} {r.get('title')} cols={r.get('columns')} rows={len(r.get('rows') or [])}")
        for i in d.get("issues", []):
            if i.get("page") == page:
                print(f"ISSUE {i.get('mpn')}: {i['question']}")


if __name__ == "__main__":
    main(int(sys.argv[1]))
