"""Fetch the full-size original of every Pentair product photo. pentair.com serves resized copies
(".thumb.1280.1280.jpg"); the same DAM path without that suffix is the original upload, often far larger.

  python3 scripts/pentair_originals.py    # data/raw/pentair/images_orig/ + data/work/pentair/web/originals.json
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import sqlite3
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from product_namer.http import Fetcher  # noqa: E402

OUT = ROOT / "data/raw/pentair/images_orig"
META = ROOT / "data/work/pentair/web/originals.json"
UA = "Mozilla/5.0 (compatible; PoolGeekCatalogBot/0.1; +https://poolgeek.com)"


def original_url(url: str) -> str:
    return re.sub(r"\.thumb\.\d+\.\d+\.(jpe?g|png)$", "", url, flags=re.I)


def main() -> int:
    con = sqlite3.connect(ROOT / "data/catalog.db")
    urls = [u for (u,) in con.execute("SELECT url FROM images WHERE role IN ('main', 'gallery') ORDER BY id")]
    meta = json.loads(META.read_text()) if META.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)
    f = Fetcher("https://www.pentair.com", delay=1.0, user_agent=UA)
    for u in urls:
        if u in meta:
            continue
        o = original_url(u)
        resp = f.get(o)
        if resp is None or resp.status_code != 200:
            meta[u] = {"original": o, "error": getattr(resp, "status_code", None)}
            continue
        try:
            with Image.open(io.BytesIO(resp.content)) as im:
                w, h = im.size
                ext = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp", "GIF": ".gif"}.get(im.format, ".img")
        except Exception as e:  # noqa: BLE001
            meta[u] = {"original": o, "error": f"not an image: {type(e).__name__}"}
            continue
        path = OUT / f"{hashlib.sha1(o.encode()).hexdigest()[:12]}{ext}"
        path.write_bytes(resp.content)
        meta[u] = {"original": o, "file": str(path.relative_to(ROOT)), "width": w, "height": h, "bytes": len(resp.content)}
        if len(meta) % 25 == 0:
            META.write_text(json.dumps(meta, indent=1))
    META.write_text(json.dumps(meta, indent=1))
    ok = [m for m in meta.values() if "file" in m]
    print(f"{len(ok)} originals of {len(urls)}; {sum(1 for m in ok if min(m['width'], m['height']) >= 1000)} at least 1000x1000, "
          f"{sum(1 for m in ok if max(m['width'], m['height']) >= 1000)} with a long side of 1000+")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
