"""Documents and product photos from the cached pentair.com pages (data/raw/pentair/pages/).

  python3 scripts/web_media.py     # writes data/work/pentair/web/media.json

For every pool-spa page: its name, the SKUs printed in its spec tables, every PDF it links (manuals, guides,
brochures, data sheets, parts sheets; language from the label or file name) and its product images (the main
image and the gallery under "product information"; icons, logos and marketing banners are skipped).
Nothing is downloaded here; the pages were cached by phase 1 and scripts/web_media_fetch.py.
"""

from __future__ import annotations

import glob
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/raw/pentair/pages"
OUT = ROOT / "data/work/pentair/web/media.json"
BASE = "https://www.pentair.com"
KINDS = [  # first match wins
    (r"parts? (sheet|list|diagram|breakdown)|replacement parts", "parts sheet"),
    (r"install(ation)?.*(user|owner|operat)|user.*install|owner.*install", "installation and user guide"),
    (r"install", "installation guide"),
    (r"user'?s? guide|user manual|owner'?s? manual|operation|operating", "user guide"),
    (r"quick (start|reference|guide)", "quick start"),
    (r"brochure|flyer|sell sheet|catalog|portfolio|lookbook", "brochure"),
    (r"data ?sheet|spec(ification)? sheet|tech(nical)? (sheet|data|bulletin)|cut sheet|submittal", "data sheet"),
    (r"warranty", "warranty"),
    (r"wiring|diagram|drawing|dimension", "drawing"),
    (r"manual", "user guide"),
    (r"guide|instruction", "guide"),
]
LANG = {"english": "en", "spanish": "es", "french": "fr", "french canadian": "fr", "portuguese": "pt"}


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def classify(title: str, url: str) -> tuple[str, str]:
    t = title.lower()
    lang = "en"
    m = re.search(r"[-–(]\s*(english|spanish|french canadian|french|portuguese)\s*\)?$", t)
    if m:
        lang = LANG[m.group(1)]
    elif re.search(r"[-_](sp|es|spanish)\.pdf$", url, re.I):
        lang = "es"
    elif re.search(r"[-_](fr|fc|french)\.pdf$", url, re.I):
        lang = "fr"
    path = url.lower()
    if "parts-sheet" in path or "replacement-parts" in path:
        return "parts sheet", lang
    if re.search(r"registration|rebate|checklist", path + " " + t):
        return "form", lang
    for pat, kind in KINDS:
        if re.search(pat, t):
            return kind, lang
    for pat, kind in KINDS:  # the file name often says what a bare "Download" link is
        if re.search(pat, path.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ")):
            return kind, lang
    if "/manual" in path:
        return "user guide", lang
    if "brochure" in path:
        return "brochure", lang
    return "document", lang


def page_url(path: Path, soup: BeautifulSoup) -> str:
    can = soup.find("link", rel="canonical")
    if can and can.get("href"):
        return can["href"]
    og = soup.find("meta", property="og:url")
    return og["content"] if og and og.get("content") else path.name


def parse(path: Path) -> dict:
    soup = BeautifulSoup(path.read_text(), "lxml")
    url = page_url(path, soup)
    h1 = soup.find("h1")
    name = clean(h1.get_text(" ")) if h1 else clean(soup.title.get_text()) if soup.title else path.stem
    skus = []
    for view in soup.select(".full-sku-view, .specs-tables"):
        for tr in view.select("table tbody tr"):
            cells = [clean(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
            if cells and re.fullmatch(r"[A-Z0-9][A-Z0-9_\-./ ]{2,20}", cells[0]):
                skus.append(cells[0].replace("_", " "))
    docs, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = urljoin(BASE, a["href"].strip())
        if not re.search(r"\.pdf(\?.*)?$", href, re.I) or href in seen:
            continue
        if "/catalogs/" in href:  # the product catalog itself, which we already have
            continue
        seen.add(href)
        title = clean(a.get_text(" ")) or clean(a.get("title") or a.get("aria-label") or "") or href.rsplit("/", 1)[-1]
        kind, lang = classify(title, href)
        docs.append({"title": title, "url": href, "kind": kind, "lang": lang})
    images, iseen = [], set()
    for im in soup.find_all("img"):
        src = im.get("src") or im.get("data-src") or ""
        if not src or src.startswith("data:"):
            continue
        src = urljoin(BASE, src)
        is_main = ".thumb.1280" in src or "mainimage" in src.lower()
        is_gallery = "product-information/additional-media" in src
        if not (is_main or is_gallery) or re.search(r"icon|logo", src, re.I) or src in iseen:
            continue
        iseen.add(src)
        images.append({"url": src, "alt": clean(im.get("alt") or ""), "role": "main" if is_main else "gallery"})
    return {"url": url, "file": path.name, "name": name, "skus": sorted(set(skus)), "documents": docs, "images": images}


def main() -> int:
    pages = [parse(Path(p)) for p in sorted(glob.glob(str(CACHE / "pool-spa-*.html")))]
    OUT.write_text(json.dumps(pages, indent=1, ensure_ascii=False))
    nd = sum(len(p["documents"]) for p in pages)
    ud = len({d["url"] for p in pages for d in p["documents"]})
    ni = len({i["url"] for p in pages for i in p["images"]})
    print(f"{len(pages)} pages; {nd} document links ({ud} unique PDFs); {ni} unique product images; "
          f"{sum(1 for p in pages if p['images'])} pages with a photo; {sum(1 for p in pages if p['documents'])} with documents")
    from collections import Counter
    print(Counter(d["kind"] for p in pages for d in p["documents"]).most_common())
    print(Counter(d["lang"] for p in pages for d in p["documents"]).most_common())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
