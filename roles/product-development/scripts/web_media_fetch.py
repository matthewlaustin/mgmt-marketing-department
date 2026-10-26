"""Download the product images listed in data/work/pentair/web/media.json into data/raw/pentair/images/
(gitignored, cached, ~1 request/second, robots.txt obeyed). Re-runs skip files already present.

  python3 scripts/web_media_fetch.py images
  python3 scripts/web_media_fetch.py docs      # the PDFs, into data/raw/pentair/docs/
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from product_namer.http import Fetcher  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "data/work/pentair/web/media.json"
IMG = ROOT / "data/raw/pentair/images"
UA = "Mozilla/5.0 (compatible; PoolGeekCatalogBot/0.1; +https://poolgeek.com)"


def image_path(url: str) -> Path:
    ext = ".png" if url.lower().endswith(".png") else ".jpg"
    stem = re.sub(r"[^A-Za-z0-9]+", "-", url.rsplit("/", 2)[-2][:40]).strip("-")
    return IMG / f"{stem}-{hashlib.sha1(url.encode()).hexdigest()[:10]}{ext}"


DOCS = ROOT / "data/raw/pentair/docs"


def doc_path(url: str) -> Path:
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", url.rsplit("/", 1)[-1])[:80]
    return DOCS / f"{hashlib.sha1(url.encode()).hexdigest()[:10]}-{name}"


def fetch_docs() -> int:
    """Matthew 2026-10-26: keep our own copies of every manual and brochure (all languages)."""
    urls = sorted({d["url"] for p in json.loads(MEDIA.read_text()) for d in p["documents"]
                   if d["kind"] != "form" and d["url"].startswith("https://www.pentair.com/")})  # manufacturer-hosted only
    DOCS.mkdir(parents=True, exist_ok=True)
    f = Fetcher("https://www.pentair.com", delay=1.0, user_agent=UA)
    done = fail = total = 0
    for u in urls:
        path = doc_path(u)
        if path.exists():
            continue
        if not f.allowed(u):
            print("robots disallows", u)
            continue
        resp = f.get(u)
        ctype = resp.headers.get("Content-Type", "") if resp is not None else ""
        if resp is not None and resp.status_code == 200 and ("pdf" in ctype or resp.content[:5] == b"%PDF-"):
            path.write_bytes(resp.content)
            done += 1
            total += len(resp.content)
        else:
            fail += 1
            print("failed", getattr(resp, "status_code", None), ctype[:30], u)
    print(f"docs: {done} downloaded ({total / 1e6:.0f} MB), {fail} failed, {sum(1 for u in urls if doc_path(u).exists())} of {len(urls)} on disk")
    return 0


def main() -> int:
    if sys.argv[1:] == ["docs"]:
        return fetch_docs()
    urls = sorted({i["url"] for p in json.loads(MEDIA.read_text()) for i in p["images"]})
    IMG.mkdir(parents=True, exist_ok=True)
    f = Fetcher("https://www.pentair.com", delay=1.0, user_agent=UA)
    done = fail = 0
    for u in urls:
        path = image_path(u)
        if path.exists():
            continue
        if not f.allowed(u):
            print("robots disallows", u)
            continue
        resp = f.get(u)
        if resp is not None and resp.status_code == 200 and resp.headers.get("Content-Type", "").startswith("image/"):
            path.write_bytes(resp.content)
            done += 1
        else:
            fail += 1
            print("failed", getattr(resp, "status_code", None), u)
    print(f"images: {done} downloaded, {fail} failed, {sum(1 for u in urls if image_path(u).exists())} of {len(urls)} on disk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
