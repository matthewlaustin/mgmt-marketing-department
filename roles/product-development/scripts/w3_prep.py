"""Batches for the web-only SKUs (Matthew 2026-10-26: gather their data from pentair.com next).

  python3 scripts/w3_prep.py     # writes data/work/pentair/d3/batches/wNN.json + d3/web_text/*.txt

Uses the product pages phase 1 already cached under data/raw/pentair/pages/ (no new downloads).
Each batch lists its pages (URL, the page's readable text, the spec-table rows phase 1 parsed) and
the web-only SKUs on them. Extraction follows docs/data-v3-prompt.md with page 0 = pentair.com.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/work/pentair"
CACHE = ROOT / "data/raw/pentair/pages"
OUT = WORK / "d3/batches"
TEXT = WORK / "d3/web_text"
PER_BATCH = 6


def cache_path(url: str) -> Path:
    # same naming as scripts/pentair_web_specs.py
    return CACHE / (re.sub(r"[^A-Za-z0-9]+", "-", url.split("/en-us/", 1)[-1]).strip("-")[:120]
                    + "-" + hashlib.sha1(url.encode()).hexdigest()[:8] + ".html")


def page_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript", "header", "footer", "nav", "svg"]):
        t.decompose()
    main = soup.select_one("main") or soup.body
    lines = (l.strip() for l in main.get_text("\n").splitlines())
    return "\n".join(l for l in lines if l)


def main() -> int:
    con = sqlite3.connect(ROOT / "data/catalog.db")
    web = {m: (b, t) for m, b, t in con.execute(
        "SELECT mpn, brand, title FROM products WHERE status = 'active' AND pages = '0'")}
    pages = defaultdict(lambda: {"skus": []})
    for path in sorted((WORK / "web/packets").glob("w*.json")):
        for g in json.loads(path.read_text())["pages"]:
            for s in g["skus"]:
                mpn = s["mpn"].replace("_", " ")
                if mpn in web and all(x["mpn"] != mpn for x in pages[g["url"]]["skus"]):
                    pages[g["url"]]["name"] = g.get("page_name", "")
                    pages[g["url"]]["skus"].append({"mpn": mpn, "web_mpn": s["mpn"], "brand": web[mpn][0],
                                                   "title": web[mpn][1], "rows": [r["row_text"] for r in s["rows"]],
                                                   "headers": s["rows"][0]["headers"] if s["rows"] else []})
    TEXT.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    urls = sorted(pages)
    missing = []
    for i in range(0, len(urls), PER_BATCH):
        name = f"w{i // PER_BATCH + 1:02d}"
        doc = {"batch": name, "section": "pentair.com", "pages": []}
        for url in urls[i:i + PER_BATCH]:
            cp = cache_path(url)
            if not cp.exists():
                missing.append(url)
                continue
            tp = TEXT / (cp.stem + ".txt")
            tp.write_text(page_text(cp.read_text()))
            doc["pages"].append({"page": 0, "url": url, "page_name": pages[url]["name"], "text": str(tp),
                                 "skus": pages[url]["skus"]})
        (OUT / f"{name}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    print(len(urls), "pages,", sum(len(p["skus"]) for p in pages.values()), "SKUs,",
          (len(urls) + PER_BATCH - 1) // PER_BATCH, "batches; missing cache:", missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
