"""Load Pentair's documents and product photos into data/catalog.db (run after d3_load.py).

  python3 scripts/web_media_load.py

Tables: documents (one row per PDF link), document_links (document -> family / SKU), images (one row per
product photo, with the local cache file when downloaded) and image_links (image -> family / SKU).
A page links to families two ways: through the active SKUs printed in its spec tables (product_families),
and through data/work/pentair/web/media_map.json (pages matched by name, reviewed). Every link keeps the
page URL it came from as evidence.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/catalog.db"
WEB = ROOT / "data/work/pentair/web"
IMG = ROOT / "data/raw/pentair/images"

SCHEMA = """
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS document_links;
DROP TABLE IF EXISTS images;
DROP TABLE IF EXISTS image_links;
CREATE TABLE documents (id INTEGER PRIMARY KEY, url TEXT NOT NULL UNIQUE, title TEXT NOT NULL, kind TEXT NOT NULL, lang TEXT NOT NULL);
CREATE TABLE document_links (document_id INTEGER NOT NULL, family_id TEXT, mpn TEXT, page_url TEXT NOT NULL, via TEXT NOT NULL);
CREATE TABLE images (id INTEGER PRIMARY KEY, url TEXT NOT NULL UNIQUE, alt TEXT, role TEXT NOT NULL, local_file TEXT,
    width INTEGER, height INTEGER, bytes INTEGER);
CREATE TABLE image_links (image_id INTEGER NOT NULL, family_id TEXT, mpn TEXT, page_url TEXT NOT NULL, via TEXT NOT NULL);
"""


def image_path(url: str) -> Path:
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from web_media_fetch import image_path as ip
    return ip(url)


def load(con: sqlite3.Connection) -> dict[str, int]:
    pages = json.loads((WEB / "media.json").read_text())
    mapping = {m["url"]: m for m in json.loads((WEB / "media_map.json").read_text())} if (WEB / "media_map.json").exists() else {}
    active = {m for (m,) in con.execute("SELECT mpn FROM products WHERE status = 'active'")}
    fam_of = defaultdict(set)
    for m, f in con.execute("SELECT mpn, family_id FROM product_families WHERE family_id IS NOT NULL"):
        fam_of[m].add(f)
    fam_ids = {f for (f,) in con.execute("SELECT id FROM families")}
    con.executescript(SCHEMA)
    doc_id, img_id = {}, {}
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover
        Image = None
    for p in pages:
        if "/products/" not in p["url"] and "/pleatco/resources" not in p["url"]:
            continue
        # targets this page speaks for
        targets = []  # (family_id, mpn, via)
        skus = [m for m in p["skus"] if m in active]
        fams_from_skus = {f for m in skus for f in fam_of[m]}
        targets += [(f, None, "SKUs printed on the page") for f in sorted(fams_from_skus)]
        targets += [(None, m, "SKU printed on the page") for m in skus]
        for f in mapping.get(p["url"], {}).get("family_ids", []):
            if f in fam_ids and f not in fams_from_skus:
                targets.append((f, None, "page name matches the product line"))
        if not targets:
            continue
        for d in p["documents"]:
            if d["kind"] == "form":
                continue
            if d["url"] not in doc_id:
                cur = con.execute("INSERT INTO documents (url, title, kind, lang) VALUES (?,?,?,?)", (d["url"], d["title"], d["kind"], d["lang"]))
                doc_id[d["url"]] = cur.lastrowid
            for f, m, via in targets:
                con.execute("INSERT INTO document_links VALUES (?,?,?,?,?)", (doc_id[d["url"]], f, m, p["url"], via))
        for i in p["images"]:
            if i["url"] not in img_id:
                w = h = b = None
                local = image_path(i["url"])
                if local.exists():
                    b = local.stat().st_size
                    if Image:
                        try:
                            with Image.open(local) as im:
                                w, h = im.size
                        except Exception:
                            pass
                cur = con.execute("INSERT INTO images (url, alt, role, local_file, width, height, bytes) VALUES (?,?,?,?,?,?,?)",
                                  (i["url"], i["alt"], i["role"], str(local.relative_to(ROOT)) if local.exists() else None, w, h, b))
                img_id[i["url"]] = cur.lastrowid
            # a gallery image whose alt text is one SKU belongs to that SKU alone
            alt_sku = i["alt"].strip().replace("_", " ")
            if alt_sku in active:
                con.execute("INSERT INTO image_links VALUES (?,?,?,?,?)", (img_id[i["url"]], None, alt_sku, p["url"], "image named for the SKU"))
                continue
            for f, m, via in targets:
                con.execute("INSERT INTO image_links VALUES (?,?,?,?,?)", (img_id[i["url"]], f, m, p["url"], via))
    con.commit()
    out = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("documents", "document_links", "images", "image_links")}
    out["families_with_docs"] = con.execute("SELECT count(DISTINCT family_id) FROM document_links WHERE family_id IS NOT NULL").fetchone()[0]
    out["families_with_photo"] = con.execute("SELECT count(DISTINCT family_id) FROM image_links WHERE family_id IS NOT NULL").fetchone()[0]
    out["images_on_disk"] = con.execute("SELECT count(*) FROM images WHERE local_file IS NOT NULL").fetchone()[0]
    return out


def main() -> int:
    con = sqlite3.connect(DB)
    print(load(con))
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
