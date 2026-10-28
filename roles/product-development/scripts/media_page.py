"""Build reports/media-review.html: Pentair documents and photos found for the product lines, with questions.

  python3 scripts/media_page.py
"""
import base64
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
con = sqlite3.connect(ROOT / "data/catalog.db")
q = lambda s, *a: con.execute(s, a).fetchall()


def thumb(local_file: str | None) -> str | None:
    """A small JPEG data URI for the page (the full image stays in the cache)."""
    if not local_file:
        return None
    try:
        from PIL import Image
        import io
        with Image.open(ROOT / local_file) as im:
            im = im.convert("RGB")
            im.thumbnail((160, 160))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=70)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


fams = {}
for fid, name, cat in q("SELECT id, name, category FROM families ORDER BY name"):
    fams[fid] = {"id": fid, "name": name, "cat": cat or "", "docs": [], "imgs": [], "models": 0}
for fid, n in q("SELECT family_id, count(DISTINCT mpn) FROM product_families WHERE role='model' AND family_id IS NOT NULL GROUP BY 1"):
    if fid in fams:
        fams[fid]["models"] = n
seen = defaultdict(set)
for fid, did, title, kind, lang, url in q("""SELECT dl.family_id, d.id, d.title, d.kind, d.lang, d.url FROM document_links dl
                                              JOIN documents d ON d.id = dl.document_id WHERE dl.family_id IS NOT NULL ORDER BY d.kind, d.lang, d.title"""):
    if fid in fams and did not in seen[fid]:
        seen[fid].add(did)
        fams[fid]["docs"].append([title, kind, lang, url])
iseen = defaultdict(set)
thumbs = {}
for fid, iid, url, alt, role, local in q("""SELECT il.family_id, i.id, i.url, i.alt, i.role, i.local_file FROM image_links il
                                             JOIN images i ON i.id = il.image_id WHERE il.family_id IS NOT NULL ORDER BY i.role, i.id"""):
    if fid in fams and iid not in iseen[fid]:
        iseen[fid].add(iid)
        if iid not in thumbs and len(thumbs) < 500:
            thumbs[iid] = thumb(local)
        fams[fid]["imgs"].append([iid, alt, role, url])

stats = {
    "families": len(fams),
    "families_models": sum(1 for f in fams.values() if f["models"]),
    "fam_docs": sum(1 for f in fams.values() if f["docs"] and f["models"]),
    "fam_imgs": sum(1 for f in fams.values() if f["imgs"] and f["models"]),
    "models": q("SELECT count(DISTINCT mpn) FROM product_families WHERE role='model'")[0][0],
    "models_with_photo": q("""SELECT count(DISTINCT pf.mpn) FROM product_families pf WHERE pf.role='model' AND (pf.family_id IN
                             (SELECT family_id FROM image_links WHERE family_id IS NOT NULL) OR pf.mpn IN (SELECT mpn FROM image_links WHERE mpn IS NOT NULL))""")[0][0],
    "models_with_docs": q("""SELECT count(DISTINCT pf.mpn) FROM product_families pf WHERE pf.role='model' AND (pf.family_id IN
                             (SELECT family_id FROM document_links WHERE family_id IS NOT NULL) OR pf.mpn IN (SELECT mpn FROM document_links WHERE mpn IS NOT NULL))""")[0][0],
    "parts_with_photo": q("""SELECT count(DISTINCT pf.mpn) FROM product_families pf WHERE pf.role IN ('part','kit','accessory','replacement')
                             AND pf.mpn IN (SELECT mpn FROM image_links WHERE mpn IS NOT NULL)""")[0][0],
    "parts": q("SELECT count(DISTINCT mpn) FROM product_families WHERE role IN ('part','kit','accessory','replacement')")[0][0],
    "docs": q("SELECT count(*) FROM documents")[0][0],
    "docs_linked": q("SELECT count(DISTINCT document_id) FROM document_links WHERE family_id IS NOT NULL OR mpn IS NOT NULL")[0][0],
    "images": q("SELECT count(*) FROM images")[0][0],
    "images_disk": q("SELECT count(*) FROM images WHERE local_file IS NOT NULL")[0][0],
    "kinds": q("SELECT kind, count(*) FROM documents GROUP BY kind ORDER BY 2 DESC"),
    "langs": q("SELECT lang, count(*) FROM documents GROUP BY lang ORDER BY 2 DESC"),
}
new_skus = json.loads((ROOT / "data/work/pentair/web/new_web_skus.json").read_text())
by_page = defaultdict(list)
for m, pages in new_skus.items():
    by_page[pages[0]].append(m)
missing = sorted(by_page.items(), key=lambda kv: -len(kv[1]))
out = {"F": [f for f in fams.values() if f["models"] or f["docs"] or f["imgs"]], "T": thumbs, "S": stats,
       "M": [[name, skus] for name, skus in missing]}
page = (ROOT / "scripts/media_template.html").read_text().replace(
    "/*DATA*/", json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
(ROOT / "reports/media-review.html").write_text(page)
print(stats, f"{len(page) / 1e6:.1f} MB")
