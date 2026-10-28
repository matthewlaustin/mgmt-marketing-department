"""Collect the SKU lists Pentair publishes on its pool product pages (data-product-sku).

  python3 scripts/pentair_web_skus.py

Reads URLs from the site's sitemap, keeps pool & spa / Pleatco product pages, and writes
data/work/pentair/web_skus.json: {url: {"name": page product name, "skus": [...]}}.
This is a completeness cross-check for the catalog extraction, not a title source.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from product_namer.http import Fetcher  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/work/pentair/web_skus.json"
KEEP = re.compile(r"/en-us/(pool-spa/products/|pool-spa/pleatco/products/|products/residential/pool-spa-equipment/)")
UA = "Mozilla/5.0 (compatible; PoolGeekCatalogBot/0.1; +https://poolgeek.com)"


def main() -> int:
    f = Fetcher("https://www.pentair.com", delay=1.0, user_agent=UA)
    index = f.get_text("/sitemap.xml") or ""
    urls: list[str] = []
    for sm in re.findall(r"<loc>([^<]+)</loc>", index):
        urls += re.findall(r"<loc>([^<]+)</loc>", f.get_text(sm) or "")
    urls = sorted({u for u in urls if KEEP.search(u)})
    result = json.loads(OUT.read_text()) if OUT.exists() else {}
    for i, url in enumerate(urls, 1):
        if url in result:
            continue
        page = f.get_text(url)
        if page is None:
            result[url] = {"error": "fetch failed"}
            continue
        skus = re.search(r'data-product-sku="([^"]*)"', page)
        name = re.search(r'"@type":\s*"Product",.*?"name":\s*"([^"]+)"', page, re.S)
        result[url] = {
            "name": html.unescape(name.group(1)) if name else "",
            "skus": [s.strip() for s in html.unescape(skus.group(1)).split(",") if s.strip()] if skus else [],
        }
        if i % 25 == 0:
            OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False))
            print(f"{i}/{len(urls)}", flush=True)
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    total = {s for v in result.values() for s in v.get("skus", [])}
    print(f"{len(result)} pages, {len(total)} distinct SKUs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
