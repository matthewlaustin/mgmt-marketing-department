"""Cache a Shopify storefront's whole product catalog from its public /products.json (250 products per page,
one request per second, robots.txt obeyed). Used for product photos: Pool Geek's own store first, then pool
retailers whose robots.txt allows it (Matthew 2026-10-26: manufacturer first, then the web).

  python3 scripts/shopify_fetch.py www.poolgeek.com       # data/raw/shops/www.poolgeek.com/pageNNN.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from product_namer.http import Fetcher  # noqa: E402

UA = "Mozilla/5.0 (compatible; PoolGeekCatalogBot/0.1; +https://poolgeek.com)"


def fetch(domain: str) -> int:
    out = ROOT / "data/raw/shops" / domain
    out.mkdir(parents=True, exist_ok=True)
    f = Fetcher(f"https://{domain}", delay=1.0, user_agent=UA)
    total = 0
    for page in range(1, 2000):
        path = out / f"page{page:03d}.json"
        if path.exists():
            data = json.loads(path.read_text())
        else:
            url = f"https://{domain}/products.json?limit=250&page={page}"
            if not f.allowed(url):
                print(domain, "robots.txt disallows", url)
                return 1
            data = f.get_json(url)
            if data is None:
                print(domain, "failed at page", page)
                return 1
            path.write_text(json.dumps(data))
        n = len(data.get("products", []))
        total += n
        if n == 0:
            break
    print(f"{domain}: {total} products in {page - 1} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(max(fetch(d) for d in sys.argv[1:]))
