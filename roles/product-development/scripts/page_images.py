"""Turn product-page links found by web search into checked photo candidates.

  python3 scripts/page_images.py data/work/photos/search/*.json    # -> data/work/photos/web_candidates.json

Input files map our part number to the product-page URLs a search found, {"460962": ["https://...", ...]}.
For each page (robots.txt obeyed, one request per second per site, pages cached under data/raw/web_pages/):
the page must show the part number in its text; its main product image is read from the page's own
metadata (JSON-LD Product image, og:image, twitter:image), asked for at full size where the site's image
server allows it, downloaded (data/raw/photos/) and measured. Marketplaces whose photos are typically
sellers' own snapshots (eBay, Amazon, AliExpress, Etsy, Facebook) are skipped.
"""

from __future__ import annotations

import collections
import hashlib
import json
import re
import sys
import time
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from product_namer.http import Fetcher  # noqa: E402
from photo_select import cache_path, dhash  # noqa: E402

PAGES = ROOT / "data/raw/web_pages"
OUT = ROOT / "data/work/photos/web_candidates.json"
HASHES = ROOT / "data/work/photos/hashes.json"
UA = "Mozilla/5.0 (compatible; PoolGeekCatalogBot/0.1; +https://poolgeek.com)"
SKIP = re.compile(r"(^|\.)(ebay|amazon|aliexpress|etsy|facebook|pinterest|youtube|reddit|flippingbook|pentair)\.", re.I)


def norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def full_size(url: str) -> str:
    """Ask the site's image server for its largest rendition."""
    u = unescape(url)
    if "demandware.static" in u or "/dw/image/" in u:  # Salesforce Commerce (Leslie's): sw/sh params
        u = re.sub(r"([?&])(sw|sh|sm|q)=[^&]*", r"\1", u).rstrip("?&")
        return u + ("&" if "?" in u else "?") + "sw=2000&sh=2000&sm=fit"
    if "thdstatic.com" in u:  # Home Depot: _100.jpg ... _1000.jpg
        return re.sub(r"_\d{2,4}\.(jpg|png|webp)$", r"_1000.\1", u)
    if "walmartimages.com" in u:
        return u.split("?")[0]
    if "bigcommerce.com" in u:  # legacy ".400.300.jpg" renditions and stencil sizes -> the stored original
        m = re.match(r"(https://cdn\d+\.bigcommerce\.com/s-[^/]+)/products/(\d+)/images/(\d+)/([^?]+?)\.\d+\.\d+\.(\w+)(\?.*)?$", u)
        if m:
            return f"{m[1]}/images/stencil/original/products/{m[2]}/{m[3]}/{m[4]}.{m[5]}"
        return re.sub(r"/images/stencil/[^/]+/", "/images/stencil/original/", u)
    if "amplience.net" in u:  # Leslie's: named size presets -> explicit large size
        return u.split("?")[0] + "?w=6000&upscale=false&fmt=jpg"
    if "/media/catalog/product/cache/" in u:  # Magento: resized cache -> the original upload
        return re.sub(r"/cache/[0-9a-f]{32}/", "/", u)
    if "/wp-content/uploads/" in u:  # WordPress: -300x200 renditions
        return re.sub(r"-\d+x\d+(\.\w+)$", r"\1", u)
    if "cdn.shopify.com" in u or "/cdn/shop/" in u:
        u = u.split("?")[0]
        return re.sub(r"_(\d+x\d*|\d*x\d+|small|medium|large|grande|compact|master)(\.\w+)$", r"\2", u)
    return u


def page_images(html: str, base: str) -> list[str]:
    urls = []
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            data = json.loads(block.strip())
        except Exception:  # noqa: BLE001
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                if str(d.get("@type", "")).lower() == "product" and d.get("image"):
                    im = d["image"]
                    for x in (im if isinstance(im, list) else [im]):
                        urls.append(x.get("url") if isinstance(x, dict) else x)
                stack.extend(v for v in d.values() if isinstance(v, (dict, list)))
            elif isinstance(d, list):
                stack.extend(d)
    for prop in ("og:image:secure_url", "og:image", "twitter:image"):
        urls += re.findall(rf'<meta[^>]+(?:property|name)=["\']{prop}["\'][^>]+content=["\']([^"\']+)', html, re.I)
        urls += re.findall(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{prop}["\']', html, re.I)
    seen, out = set(), []
    for u in urls:
        if not u or not isinstance(u, str):
            continue
        u = urljoin(base, unescape(u.strip()))
        if re.search(r"logo|placeholder|no[-_]?image|default", u, re.I) or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out[:3]


def main(files: list[str]) -> int:
    wanted: dict[str, set[str]] = collections.defaultdict(set)
    for f in files:
        for m, urls in json.loads(Path(f).read_text()).items():
            wanted[m].update(u for u in urls if u.startswith("http") and not SKIP.search(urlparse(u).netloc))
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    hashes = json.loads(HASHES.read_text()) if HASHES.exists() else {}
    fetchers: dict[str, Fetcher] = {}
    PAGES.mkdir(parents=True, exist_ok=True)
    done = {(m, c["page_url"]) for m, cs in out.items() if m != "_checked" for c in cs} | {(m, u) for m, us in out.get("_checked", {}).items() for u in us}
    checked = out.setdefault("_checked", {})
    n = 0
    for m, urls in sorted(wanted.items()):
        for page_url in sorted(urls):
            if (m, page_url) in done:
                continue
            checked.setdefault(m, []).append(page_url)
            t0 = time.time()
            host = urlparse(page_url).netloc
            f = fetchers.setdefault(host, Fetcher(f"https://{host}", delay=1.0, timeout=15, retries=0, user_agent=UA))
            cp = PAGES / (hashlib.sha1(page_url.encode()).hexdigest()[:16] + ".html")
            if cp.exists():
                html = cp.read_text(errors="ignore")
            else:
                if not f.allowed(page_url):
                    continue
                r = f.get(page_url)
                if r is None or r.status_code != 200 or "html" not in r.headers.get("Content-Type", ""):
                    continue
                html = r.text
                cp.write_text(html)
            text = norm(re.sub(r"<[^>]+>", " ", html))
            if norm(m) not in text:
                continue  # the page never names this part number
            for img in page_images(html, page_url):
                u = full_size(img)
                h = hashes.get(u)
                if not h:
                    p = cache_path(u)
                    try:
                        if not p.exists():
                            host2 = urlparse(u).netloc
                            f2 = fetchers.setdefault(host2, Fetcher(f"https://{host2}", delay=0.5, timeout=15, retries=0, user_agent=UA))
                            r = f2.get(u)
                            if (r is None or r.status_code != 200) and u != img:  # full-size request refused: the page's own size
                                u = img
                                r = f2.get(u)
                            if r is None or r.status_code != 200:
                                continue
                            p = cache_path(u)
                            p.write_bytes(r.content)
                        with Image.open(p) as im:
                            h = {"file": str(p.relative_to(ROOT)), "width": im.width, "height": im.height, "dhash": dhash(im), "bytes": p.stat().st_size}
                        hashes[u] = h
                    except Exception:  # noqa: BLE001
                        continue
                g = ("ok" if min(h["width"], h["height"]) >= 1000 else "long" if max(h["width"], h["height"]) >= 1000
                     else "mid" if max(h["width"], h["height"]) >= 500 else "small")
                out.setdefault(m, []).append({"source": host.removeprefix("www."), "page_url": page_url, "image_url": u, "width": h["width"],
                                              "height": h["height"], "grade": g, "match": "web page names the part number"})
                break  # the page's main image is enough
            n += 1
            if time.time() - t0 > 10:
                print(f"  slow {time.time() - t0:.0f}s {page_url}", flush=True)
            if n % 50 == 0:
                OUT.write_text(json.dumps(out, indent=1))
                HASHES.write_text(json.dumps(hashes))
                print(f"  {n} pages checked", flush=True)
    OUT.write_text(json.dumps(out, indent=1))
    HASHES.write_text(json.dumps(hashes))
    got = {m: cs for m, cs in out.items() if m != "_checked"}
    print(f"{len(wanted)} SKUs searched; {sum(1 for cs in got.values() if any(c['grade'] == 'ok' for c in cs))} have a 1000x1000+ web image, "
          f"{sum(1 for cs in got.values() if cs)} any web image")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
