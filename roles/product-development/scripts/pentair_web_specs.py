"""Read the ordering tables ("Item # | Description …") on Pentair's pool product pages.

  python3 scripts/pentair_web_specs.py

For every page in data/work/pentair/web_skus.json, fetch it (cached under data/raw/pentair/pages/,
~1 request/second, robots.txt obeyed) and parse the specifications tables in the page's full-SKU
view. Writes data/work/pentair/web_specs.json:
  {sku: [{"url", "page_name", "headers": [...], "cells": [...], "row_text"}]}
Each row is Pentair's own published text for that SKU: the evidence for Phase 2 titles.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from product_namer.http import Fetcher  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/work/pentair"
CACHE = ROOT / "data/raw/pentair/pages"
UA = "Mozilla/5.0 (compatible; PoolGeekCatalogBot/0.1; +https://poolgeek.com)"


def cached_page(f: Fetcher, url: str) -> str | None:
    path = CACHE / (re.sub(r"[^A-Za-z0-9]+", "-", url.split("/en-us/", 1)[-1]).strip("-")[:120]
                    + "-" + hashlib.sha1(url.encode()).hexdigest()[:8] + ".html")
    if path.exists():
        return path.read_text()
    text = f.get_text(url)
    if text is not None:
        path.write_text(text)
    return text


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def spec_rows(html_text: str) -> list[tuple[list[str], list[str]]]:
    soup = BeautifulSoup(html_text, "lxml")
    views = soup.select(".full-sku-view") or soup.select(".specs-tables")
    rows = []
    for view in views:
        for table in view.find_all("table"):
            headers = [clean(th.get_text(" ")) for th in table.select("thead th")]
            for tr in table.select("tbody tr"):
                cells = [clean(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
                if cells and any(cells):
                    rows.append((headers, cells))
    return rows


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    pages = json.loads((WORK / "web_skus.json").read_text())
    f = Fetcher("https://www.pentair.com", delay=1.0, user_agent=UA)
    out: dict[str, list[dict]] = {}
    for i, (url, info) in enumerate(sorted(pages.items()), 1):
        if not info.get("skus"):
            continue
        text = cached_page(f, url)
        if text is None:
            print(f"fetch failed: {url}", flush=True)
            continue
        listed = set(info["skus"])
        for headers, cells in spec_rows(text):
            sku_col = next((j for j, h in enumerate(headers) if re.search(r"item|part|sku|model", h, re.I)), 0)
            sku = cells[sku_col] if sku_col < len(cells) else ""
            if sku not in listed:
                continue
            out.setdefault(sku, []).append({
                "url": url, "page_name": info.get("name", ""), "headers": headers, "cells": cells,
                "row_text": " | ".join(cells),
            })
        if i % 25 == 0:
            print(f"{i}/{len(pages)} pages", flush=True)
    (WORK / "web_specs.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    listed_all = {s for v in pages.values() for s in v.get("skus", [])}
    print(f"SKUs listed on pages: {len(listed_all)}; with a spec-table row: {len(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
