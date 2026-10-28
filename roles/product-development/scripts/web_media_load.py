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
CREATE TABLE documents (id INTEGER PRIMARY KEY, url TEXT NOT NULL UNIQUE, title TEXT NOT NULL, kind TEXT NOT NULL, lang TEXT NOT NULL,
    local_file TEXT, bytes INTEGER, object_key TEXT, public_url TEXT);
CREATE TABLE document_links (document_id INTEGER NOT NULL, family_id TEXT, mpn TEXT, page_url TEXT NOT NULL, via TEXT NOT NULL);
CREATE TABLE images (id INTEGER PRIMARY KEY, url TEXT NOT NULL UNIQUE, alt TEXT, role TEXT NOT NULL, local_file TEXT,
    width INTEGER, height INTEGER, bytes INTEGER, label TEXT, people INTEGER, background TEXT, object_key TEXT, public_url TEXT);
CREATE TABLE image_links (image_id INTEGER NOT NULL, family_id TEXT, mpn TEXT, page_url TEXT NOT NULL, via TEXT NOT NULL);
"""


def image_path(url: str) -> Path:
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from web_media_fetch import image_path as ip
    return ip(url)


def doc_path(url: str) -> Path:
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from web_media_fetch import doc_path as dp
    return dp(url)


def load_charts(con: sqlite3.Connection) -> int:
    """Reference charts (pump curves, dimension drawings, sizing charts) rendered from the catalog PDF."""
    meta_file = ROOT / "data/work/pentair/d3/charts.json"
    if not meta_file.exists():
        return 0
    n = 0
    for cid, m in json.loads(meta_file.read_text()).items():
        fids = con.execute("SELECT family_ids FROM reference_tables WHERE id = ?", (int(cid),)).fetchone()
        cur = con.execute("INSERT INTO images (url, alt, role, local_file, width, height, bytes, label) VALUES (?,?,?,?,?,?,?,?)",
                          (f"catalog://pentair-2025-2026/p{m['page']:03d}/chart/{cid}", m["title"], "chart", m["file"], m["width"], m["height"], m["bytes"], "chart"))
        for f in (json.loads(fids[0]) if fids and fids[0] else []):
            con.execute("INSERT INTO image_links VALUES (?,?,?,?,?)", (cur.lastrowid, f, None, f"catalog p{m['page']}", "chart printed for the line"))
            n += 1
    return n


def apply_r2(con: sqlite3.Connection) -> int:
    """Object keys and public URLs from scripts/r2_upload.py (data/work/pentair/r2_objects.json): our own copy
    of each file in the Cloudflare R2 bucket (Matthew 2026-10-26)."""
    f = ROOT / "data/work/pentair/r2_objects.json"
    if not f.exists():
        return 0
    n = 0
    for local, o in json.loads(f.read_text()).items():
        for t in ("images", "documents"):
            n += con.execute(f"UPDATE {t} SET object_key = ?, public_url = ? WHERE local_file = ?", (o["key"], o.get("url"), local)).rowcount
    return n


def load_diagrams(con: sqlite3.Connection, active: set[str]) -> int:
    """Matthew 2026-10-26: for now a part's picture is the exploded diagram of the parts list it is on.
    diagrams.json: page -> {heading, diagrams: [{file, width, height, bytes, box}], from_page?}; a continuation page
    reuses the drawing of the page it continues (from_page), so one image row serves both pages."""
    meta_file = ROOT / "data/work/pentair/d3/diagrams.json"
    if not meta_file.exists():
        return 0
    meta = {int(k): v for k, v in json.loads(meta_file.read_text()).items()}
    n = 0
    ids: dict[int, list[int]] = {}
    for page, m in sorted(meta.items()):
        src = m.get("from_page", page)
        if src not in ids:
            ids[src] = []
            for k, d in enumerate(m["diagrams"], 1):
                cur = con.execute("INSERT INTO images (url, alt, role, local_file, width, height, bytes) VALUES (?,?,?,?,?,?,?)",
                                  (f"catalog://pentair-2025-2026/p{src:03d}/diagram/{k}",
                                   f"Exploded parts diagram{' ' + str(k) if len(m['diagrams']) > 1 else ''}, catalog page {src - 2}", "diagram",
                                   d["file"], d["width"], d["height"], d["bytes"]))
                ids[src].append(cur.lastrowid)
        for (part,) in con.execute("SELECT DISTINCT part_mpn FROM fitment WHERE pdf_page = ?", (page,)).fetchall():
            if part in active:
                for iid in ids[src]:
                    con.execute("INSERT INTO image_links VALUES (?,?,?,?,?)", (iid, None, part, f"catalog p{page}",
                                "catalog exploded diagram of the part's list" + (f" (drawing on p{src})" if src != page else "")))
                    n += 1
    return n


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
    cls_file = Path("/tmp/claude-0/-home-user-product-namer/28224544-019c-5471-b0e0-39374ec9eedf/scratchpad/images_classified.json")
    cls_repo = WEB / "images_classified.json"
    labels = {}
    for src in (cls_repo, cls_file):
        if src.exists():
            labels = {c["url"]: c for c in json.loads(src.read_text())}
            break
    mentions = json.loads((WEB / "doc_mentions.json").read_text()) if (WEB / "doc_mentions.json").exists() else {}
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover
        Image = None
    for p in pages:
        if "/products/" not in p["url"] and "/pleatco/resources" not in p["url"]:
            continue
        discontinued = bool(p.get("discontinued"))
        # targets this page speaks for
        targets = []  # (family_id, mpn, via)
        skus = [m for m in p["skus"] if m in active]
        fams_from_skus = {f for m in skus for f in fam_of[m]}
        targets += [(f, None, "SKUs printed on the page") for f in sorted(fams_from_skus)]
        targets += [(None, m, "SKU printed on the page") for m in skus]
        m_entry = mapping.get(p["url"], {})
        for f in m_entry.get("family_ids", []):
            if f in fam_ids and f not in fams_from_skus:
                targets.append((f, None, "page name matches the product line"))
        if discontinued:
            # Matthew 2026-10-26: a discontinued line's manuals, parts sheets and photos belong on the parts lists we still sell
            for f in m_entry.get("would_map_to", []):
                if f in fam_ids and all(f != t[0] for t in targets):
                    targets.append((f, None, "discontinued line; attached to its parts list"))
            targets = [(f, m, "discontinued line; " + via if not via.startswith("discontinued") else via) for f, m, via in targets]
        if not targets:
            continue
        for d in p["documents"]:
            if d["kind"] == "form":
                continue
            if d["url"] not in doc_id:
                local = doc_path(d["url"])
                cur = con.execute("INSERT INTO documents (url, title, kind, lang, local_file, bytes) VALUES (?,?,?,?,?,?)",
                                  (d["url"], d["title"], d["kind"], d["lang"],
                                   str(local.relative_to(ROOT)) if local.exists() else None, local.stat().st_size if local.exists() else None))
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
                lab = labels.get(i["url"], {})
                cur = con.execute("INSERT INTO images (url, alt, role, local_file, width, height, bytes, label, people, background) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                  (i["url"], i["alt"], i["role"], str(local.relative_to(ROOT)) if local.exists() else None, w, h, b,
                                   lab.get("label"), int(bool(lab.get("people"))) if lab else None, lab.get("bg")))
                img_id[i["url"]] = cur.lastrowid
            if i["role"] == "marketing":
                continue  # page bands (lifestyle shots, app screens) are kept on file but are not product photos
            # a gallery image whose alt text is one SKU belongs to that SKU alone
            alt_sku = i["alt"].strip().replace("_", " ")
            if alt_sku in active:
                con.execute("INSERT INTO image_links VALUES (?,?,?,?,?)", (img_id[i["url"]], None, alt_sku, p["url"], "image named for the SKU"))
                continue
            for f, m, via in targets:
                con.execute("INSERT INTO image_links VALUES (?,?,?,?,?)", (img_id[i["url"]], f, m, p["url"], via))
    for url, fids in mentions.items():
        if url not in doc_id:
            continue
        linked = {f for (f,) in con.execute("SELECT family_id FROM document_links WHERE document_id = ? AND family_id IS NOT NULL", (doc_id[url],))}
        for f in fids:
            if f in fam_ids and f not in linked:
                con.execute("INSERT INTO document_links VALUES (?,?,?,?,?)", (doc_id[url], f, None, url, "the document's text names the line"))
    load_charts(con)
    load_diagrams(con, active)
    apply_r2(con)
    con.commit()
    out = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("documents", "document_links", "images", "image_links")}
    out["families_with_docs"] = con.execute("SELECT count(DISTINCT family_id) FROM document_links WHERE family_id IS NOT NULL").fetchone()[0]
    out["families_with_photo"] = con.execute("SELECT count(DISTINCT family_id) FROM image_links WHERE family_id IS NOT NULL").fetchone()[0]
    out["images_on_disk"] = con.execute("SELECT count(*) FROM images WHERE local_file IS NOT NULL").fetchone()[0]
    out["docs_on_disk"] = con.execute("SELECT count(*) FROM documents WHERE local_file IS NOT NULL").fetchone()[0]
    out["parts_with_diagram"] = con.execute("SELECT count(DISTINCT mpn) FROM image_links il JOIN images i ON i.id = il.image_id WHERE i.role = 'diagram'").fetchone()[0]
    return out


def main() -> int:
    con = sqlite3.connect(DB)
    print(load(con))
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
