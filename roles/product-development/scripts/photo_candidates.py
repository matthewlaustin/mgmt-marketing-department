"""Product-photo candidates for every active SKU (Matthew 2026-10-26): Pentair's own photos first, then Pool
Geek's store, then other stores' catalogs cached by scripts/shopify_fetch.py.

  python3 scripts/photo_candidates.py      # data/work/photos/candidates.json + a summary

A store listing counts for a SKU only when one of its variant SKUs equals our part number (punctuation and case
ignored, a store prefix such as "PEN-" stripped) and the listing is not an aftermarket brand's look-alike part.
Image sizes come from the store's JSON (Shopify records each upload's width and height), so nothing is
downloaded here. Spec: at least 1000 x 1000 ("ok"); a long side of 1000+ is kept as "long" for review.
"""

from __future__ import annotations

import collections
import glob
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/work/photos/candidates.json"
OURS = re.compile(r"pentair|sta-?rite|pleatco|kreepy|letro|rainbow|purex|american products|paragon|pac-?fab|compool", re.I)
AFTERMARKET = re.compile(r"\b(cmp|custom molded|unicel|aladdin|filbur|magic plastics|hayward|zodiac|jandy|polaris|waterway|"
                         r"carvin|smartpool|generic|pool tool|ocean blue|kokido|essential|aftermarket|replacement for|compatible with|fits )", re.I)
PREFIX = re.compile(r"^(PEN|PENT|PNR|STA|STR|SR|PLE|PLT|PAC|P)[-_ .]+", re.I)


def norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def grade(w, h) -> str:
    w, h = w or 0, h or 0
    return "ok" if min(w, h) >= 1000 else "long" if max(w, h) >= 1000 else "small"


def manufacturer(con) -> dict[str, list[dict]]:
    """Pentair's own product photos per SKU (through the SKU or its product line), at their original size."""
    orig = json.loads((ROOT / "data/work/pentair/web/originals.json").read_text()) if (ROOT / "data/work/pentair/web/originals.json").exists() else {}
    fams = collections.defaultdict(set)
    for m, f in con.execute("SELECT mpn, family_id FROM product_families WHERE family_id IS NOT NULL"):
        fams[m].add(f)
    by_f, by_m = collections.defaultdict(list), collections.defaultdict(list)
    for url, w, h, label, f, m, page in con.execute("""SELECT i.url, i.width, i.height, i.label, il.family_id, il.mpn, il.page_url FROM image_links il
            JOIN images i ON i.id = il.image_id WHERE i.role IN ('main', 'gallery') AND coalesce(i.label, 'product') IN ('product', 'detail')"""):
        o = orig.get(url, {})
        cand = {"source": "pentair.com", "image_url": o.get("original", url), "page_url": page, "width": o.get("width", w), "height": o.get("height", h),
                "file": o.get("file"), "label": label, "match": "line photo" if f else "sku"}
        (by_f[f] if f else by_m[m]).append(cand)
    out = {}
    for m in {m for (m,) in con.execute("SELECT mpn FROM products WHERE status = 'active'")}:
        seen, lst = set(), []
        for c in by_m[m] + [c for f in sorted(fams[m]) for c in by_f[f]]:
            if c["image_url"] not in seen:
                seen.add(c["image_url"])
                lst.append(dict(c, grade=grade(c["width"], c["height"])))
        out[m] = lst
    return out


TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-./]{3,}[A-Za-z0-9]")
TAG = re.compile(r"<[^>]+>")


def stores(active: set[str]) -> dict[str, list[dict]]:
    """Store listings per SKU. Match strength: "sku" (a variant's SKU field is our part number), "title" (the part
    number is a word of the listing title or URL handle), "description" (named in the description, which names
    no other of our part numbers). Text matches need the listing to be one of our brands."""
    keys = {norm(m): m for m in active if len(norm(m)) >= 5}
    keys.update({norm(m): m for m in active if len(norm(m)) < 5})  # short numbers: SKU field only (below)
    out = collections.defaultdict(list)

    def found(text: str) -> set[str]:
        return {keys[norm(t)] for t in TOKEN.findall(text or "") if len(norm(t)) >= 5 and norm(t) in keys}

    for d in sorted(glob.glob(str(ROOT / "data/raw/shops/*"))):
        site = Path(d).name
        for f in sorted(glob.glob(d + "/page*.json")):
            for p in json.loads(Path(f).read_text()).get("products", []):
                text = f"{p.get('vendor', '')} {p.get('title', '')}"
                if AFTERMARKET.search(text) and not OURS.search(p.get("vendor", "")):
                    continue
                imgs = {i["id"]: i for i in p.get("images", [])}
                hits: dict[str, tuple[str, dict]] = {}
                for v in p.get("variants", []):
                    sku = v.get("sku") or ""
                    m = next((keys[k] for k in (norm(sku), norm(PREFIX.sub("", sku))) if k in keys), None)
                    if m:
                        hits[m] = ("sku", v)
                if OURS.search(text):
                    for m in found(p.get("title", "") + " " + p.get("handle", "").replace("-", " ")):
                        hits.setdefault(m, ("title", {}))
                    body = found(TAG.sub(" ", p.get("body_html") or ""))
                    if len(body) == 1 and len(p.get("variants", [])) == 1 and not hits:
                        hits[next(iter(body))] = ("description", {})
                for m, (how, v) in hits.items():
                    fi = (v or {}).get("featured_image") or {}
                    first = imgs.get(fi.get("id")) or (p["images"][0] if p.get("images") else None)
                    base = {"source": site, "page_url": f"https://{site}/products/{p['handle']}", "title": p.get("title"),
                            "vendor": p.get("vendor"), "sku": (v or {}).get("sku"), "match": how}
                    if not first:
                        out[m].append(dict(base, image_url=None, grade="none"))
                        continue
                    out[m].append(dict(base, image_url=first["src"].split("?")[0], width=first.get("width"), height=first.get("height"),
                                       grade=grade(first.get("width"), first.get("height"))))
    return out


def main() -> int:
    con = sqlite3.connect(ROOT / "data/catalog.db")
    active = {m for (m,) in con.execute("SELECT mpn FROM products WHERE status = 'active'")}
    man, sto = manufacturer(con), stores(active)
    res = {}
    for m in sorted(active):
        mfr_ok = [c for c in man.get(m, []) if c["grade"] == "ok"]
        res[m] = {"manufacturer": man.get(m, []), "stores": sto.get(m, []), "needs_outside": not mfr_ok}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1))
    need = [m for m, r in res.items() if r["needs_outside"]]
    s = collections.Counter()
    for m in need:
        g = {c["grade"] for c in res[m]["stores"] if c.get("image_url")}
        sites = {c["source"] for c in res[m]["stores"] if c.get("grade") == "ok"}
        s["store ok, 2+ sites" if len(sites) >= 2 else "store ok, 1 site" if sites else "store long side only" if "long" in g
          else "store small only" if g else "listed, no image" if res[m]["stores"] else "not in any store"] += 1
    print(f"{len(active)} SKUs; {len(active) - len(need)} have a Pentair photo at 1000x1000+; {len(need)} need one from outside:")
    for k, v in s.most_common():
        print(f"  {k:24} {v}")
    print("match kinds among ok images:", collections.Counter(c["match"] for m in need for c in res[m]["stores"] if c.get("grade") == "ok").most_common())
    print("by store (SKUs with an ok image):", collections.Counter(c["source"] for m in need for c in {c["source"]: c for c in res[m]["stores"] if c.get("grade") == "ok"}.values()).most_common())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
