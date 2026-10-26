"""Report page for Matthew on the first product-photo run: reports/product-photos.html (Artifact; answers come back
through ArtifactData collections photo_answers / photo_followups).

  python3 scripts/photo_report.py      # after photo_load.py
"""

from __future__ import annotations

import base64
import collections
import io
import json
import random
import sqlite3
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from photo_select import EXCLUDE_SOURCES  # noqa: E402

OUT = ROOT / "reports/product-photos.html"


def thumb(path: Path, size: int = 220) -> str:
    with Image.open(path) as im:
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, "white")
            bg.alpha_composite(im)
            im = bg
        im = im.convert("RGB")
        im.thumbnail((size, size), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=72, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def main() -> int:
    con = sqlite3.connect(ROOT / "data/catalog.db")
    titles = dict(con.execute("SELECT mpn, title FROM products WHERE status = 'active'"))
    rows = con.execute("SELECT mpn, tier, source, sites, width, height, public_url, page_url, local_file FROM product_photos").fetchall()
    chosen = json.loads((ROOT / "data/work/photos/chosen.json").read_text())
    tiers = collections.Counter(r[1].split(" (")[0] for r in rows)
    padded = sum(1 for r in rows if "(padded)" in r[1])
    small500 = sum(1 for r in rows if "(500-999 px)" in r[1])
    near = sum(1 for m, c in chosen.items() if c.get("grade") == "long" and m not in {r[0] for r in rows})
    have = {r[0] for r in rows}
    S = {"skus": len(titles), "with_photo": len(rows), "pentair": tiers["manufacturer"], "poolgeek": tiers["pool geek"],
         "multi": tiers["multi-site"], "single": tiers["single site"], "near": near,
         "to_search": len(titles) - len(rows) - near}
    S["padded"] = padded
    S["small500"] = small500
    S["missing"] = [["with only small images online or none found yet", S["to_search"]]]
    src = collections.Counter(r[2] for r in rows)
    notes = {"pentair.com": "Pentair's own images, full-size originals", "poolgeek.com": "Pool Geek's own store"}
    SRC = [[s, c, notes.get(s, "")] for s, c in src.most_common()]
    EX = [[s.removeprefix("www."), why] for s, why in EXCLUDE_SOURCES.items()]
    random.seed(11)
    by = collections.defaultdict(list)
    for r in rows:
        by[r[1].split(" (")[0] + (" 500" if "(500-999 px)" in r[1] else "")].append(r)
    pick = []
    for t, k in (("manufacturer", 20), ("pool geek", 14), ("multi-site", 30), ("single site", 30), ("multi-site 500", 12), ("single site 500", 14)):
        pick += random.sample(by[t], min(k, len(by[t])))
    W = [[r[0], r[1], r[2], thumb(ROOT / r[8])] for r in pick]
    R = sorted([[r[0], titles.get(r[0], ""), r[1], r[2], len(json.loads(r[3])), r[4], r[5], r[6], r[7]] for r in rows])
    data = {"S": S, "SRC": SRC, "EX": EX, "W": W, "R": R}
    OUT.write_text((ROOT / "scripts/photo_report_template.html").read_text().replace("/*DATA*/", json.dumps(data)))
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1e6:.1f} MB; {S}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
