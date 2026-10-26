"""Load the approved product photos: table product_photos in data/catalog.db, each image copied to the R2 bucket.

  python3 scripts/photo_load.py            # needs R2_* in the environment for the upload; then load_neon.py

One row per SKU (Matthew 2026-10-26: one good image per product for the first run). A photo is approved when it
is at least 1000 x 1000 and either Pentair's own or passed the visual review (scripts/photo_review.py). A reviewed
photo whose long side is 1000+ but short side is not is centred on a white square as wide as its long side
(Matthew 2026-10-26: "Pad them to a square"); nothing is enlarged. Padded copies: data/raw/photos/padded/. Columns:
tier (manufacturer / pool geek / multi-site / single site), source (site), page_url (the listing it came from),
image_url (as found), sites (JSON list of sites showing the same picture), match (how the listing was tied to the
SKU), width, height, object_key and public_url (our copy in R2).
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHOSEN = ROOT / "data/work/photos/chosen.json"
REVIEWED = ROOT / "data/work/photos/reviewed.json"
OBJ = ROOT / "data/work/photos/r2_photos.json"

PAD = ROOT / "data/raw/photos/padded"


def pad(path: Path) -> dict:
    from PIL import Image
    out = PAD / (path.stem + ".jpg")
    with Image.open(path) as im:
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, "white")
            bg.alpha_composite(im)
            im = bg
        im = im.convert("RGB")
        side = max(im.size)
        sq = Image.new("RGB", (side, side), "white")
        sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
        if not out.exists():
            sq.save(out, format="JPEG", quality=92, optimize=True)
    return {"file": str(out.relative_to(ROOT)), "width": side, "height": side, "grade": "ok"}


SCHEMA = """
DROP TABLE IF EXISTS product_photos;
CREATE TABLE product_photos (mpn TEXT PRIMARY KEY, tier TEXT NOT NULL, source TEXT NOT NULL, page_url TEXT, image_url TEXT NOT NULL,
    sites TEXT NOT NULL, match TEXT, width INTEGER NOT NULL, height INTEGER NOT NULL, local_file TEXT, object_key TEXT, public_url TEXT);
"""


def main() -> int:
    chosen = json.loads(CHOSEN.read_text())
    reviewed = json.loads(REVIEWED.read_text()) if REVIEWED.exists() else {}
    objs = json.loads(OBJ.read_text()) if OBJ.exists() else {}
    rows = []
    PAD.mkdir(parents=True, exist_ok=True)
    for m, c in sorted(chosen.items()):
        if c.get("grade") not in ("ok", "long"):
            continue
        if c.get("grade") == "long":
            if reviewed.get(c["image_url"]) != "pass" or not c.get("file"):
                continue
            c = dict(c, **pad(ROOT / c["file"]), tier=c["tier"].replace(", below 1000x1000", "") + " (padded)")
        if c["tier"] != "manufacturer" and reviewed.get(c["image_url"]) != "pass":
            continue
        if not c.get("file") or not (ROOT / c["file"]).exists():
            continue
        rows.append((m, c))
    s3 = None
    if all(os.environ.get(k) for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")):
        import boto3
        s3 = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                          aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"], aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
        bucket, public = os.environ["R2_BUCKET"], os.environ.get("R2_PUBLIC_URL", "").rstrip("/")
    up = 0
    for m, c in rows:
        f = ROOT / c["file"]
        if c["file"] in objs or not s3:
            continue
        data = f.read_bytes()
        key = f"product-photos/{hashlib.sha1(data).hexdigest()[:20]}{f.suffix.lower() or '.jpg'}"
        s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=mimetypes.guess_type(f.name)[0] or "image/jpeg",
                      CacheControl="public, max-age=31536000, immutable")
        objs[c["file"]] = {"key": key, "url": f"{public}/{key}" if public else None}
        up += 1
        if up % 100 == 0:
            OBJ.write_text(json.dumps(objs, indent=1))
            print(f"  {up} uploaded", flush=True)
    OBJ.write_text(json.dumps(objs, indent=1))
    con = sqlite3.connect(ROOT / "data/catalog.db")
    con.executescript(SCHEMA)
    for m, c in rows:
        o = objs.get(c["file"], {})
        con.execute("INSERT INTO product_photos VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (m, c["tier"], c["source"].removeprefix("www."), c.get("page_url"), c["image_url"], json.dumps([x.removeprefix("www.") for x in c.get("sites", [])]),
                     c.get("match"), c["width"], c["height"], c["file"], o.get("key"), o.get("url")))
    con.commit()
    print(f"product_photos: {len(rows)} SKUs ({up} newly uploaded);",
          dict(con.execute("SELECT tier, count(*) FROM product_photos GROUP BY tier ORDER BY 2 DESC").fetchall()),
          f"{con.execute('SELECT count(*) FROM product_photos WHERE public_url IS NOT NULL').fetchone()[0]} in R2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
