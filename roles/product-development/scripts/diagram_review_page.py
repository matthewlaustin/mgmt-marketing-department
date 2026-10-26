"""Review page for Matthew: what was wrong with the parts diagrams and how they render now, the brochures and
sell sheets found on pentair.com, the storage question. Writes reports/diagram-review.html (published as an
Artifact; answers come back through ArtifactData collections diagram_answers / diagram_followups).

  python3 scripts/diagram_review_page.py
"""

from __future__ import annotations

import base64
import io
import json
import sqlite3
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/catalog.db"
META = ROOT / "data/work/pentair/d3/diagrams.json"
OUT = ROOT / "reports/diagram-review.html"
SCRATCH = Path("/tmp/claude-0/-home-user-product-namer/28224544-019c-5471-b0e0-39374ec9eedf/scratchpad")
FILES = SCRATCH / "diagram-review-files/diagrams"  # published with the page as supporting files, not committed


def jpeg_uri(path: Path, width: int, quality: int = 70) -> str:
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.width > width:
            im = im.resize((width, max(1, round(im.height * width / im.width))), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def main() -> int:
    con = sqlite3.connect(DB)
    q = lambda sql, *a: con.execute(sql, a).fetchall()
    meta = json.loads(META.read_text())
    drawn = {int(k): v for k, v in meta.items() if "from_page" not in v}
    parts = q("SELECT count(DISTINCT mpn) FROM product_families WHERE role IN ('part','kit','replacement')")[0][0]
    S = {
        "images": sum(len(v["diagrams"]) for v in drawn.values()), "pages_drawn": len(drawn), "pages_no_table": 124,
        "parts": parts, "parts_with_diagram": q("SELECT count(DISTINCT il.mpn) FROM image_links il JOIN images i ON i.id = il.image_id WHERE i.role = 'diagram'")[0][0],
        "fbo_docs": q("SELECT count(*) FROM documents WHERE url LIKE 'https://online.flippingbook.com/%'")[0][0],
        "fbo_disk": q("SELECT count(*) FROM documents WHERE url LIKE 'https://online.flippingbook.com/%' AND local_file IS NOT NULL")[0][0],
        "fbo_pages": q("SELECT count(DISTINCT dl.page_url) FROM document_links dl JOIN documents d ON d.id = dl.document_id WHERE d.url LIKE 'https://online.flippingbook.com/%'")[0][0],
        "fbo_kinds": ", ".join(f"{k} {c}" for k, c in q("SELECT kind, count(*) FROM documents WHERE url LIKE 'https://online.flippingbook.com/%' GROUP BY kind ORDER BY 2 DESC")),
        "docs_total": q("SELECT count(*) FROM documents")[0][0], "docs_disk": q("SELECT count(*) FROM documents WHERE local_file IS NOT NULL")[0][0],
        "disk": "about 1.9 GB",
    }
    D = []
    for did, title, kind, lang, url in q("SELECT id, title, kind, lang, url FROM documents WHERE url LIKE 'https://online.flippingbook.com/%' ORDER BY kind, title"):
        lines = q("SELECT DISTINCT f.name FROM document_links dl JOIN families f ON f.id = dl.family_id WHERE dl.document_id = ? ORDER BY f.name", did)
        names = [x[0] for x in lines]
        D.append([title, kind, lang, url, ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")])
    G = []  # thumbnails inline; the full-size views as files published beside the page (FILES / diagrams/pNNN_k.jpg)
    FILES.mkdir(parents=True, exist_ok=True)
    for page in sorted(drawn):
        for k, d in enumerate(drawn[page]["diagrams"], 1):
            f = ROOT / d["file"]
            with Image.open(f) as im:
                im = im.convert("RGB")
                if im.width > 1000:
                    im = im.resize((1000, round(im.height * 1000 / im.width)), Image.LANCZOS)
                im.save(FILES / f"{f.stem}.jpg", format="JPEG", quality=68, optimize=True)
            G.append([f"{page - 2}" + (f" ({k})" if len(drawn[page]["diagrams"]) > 1 else ""), jpeg_uri(f, 240, 55), f"diagrams/{f.stem}.jpg"])
    before = ROOT / "data/work/pentair/d3/p431_diagram_before.png"
    data = {"S": S, "D": D, "G": G, "before": jpeg_uri(before, 900) if before.exists() else "", "after": jpeg_uri(ROOT / drawn[431]["diagrams"][0]["file"], 900)}
    html = (ROOT / "scripts/diagram_review_template.html").read_text().replace("/*DATA*/", json.dumps(data))
    OUT.write_text(html)
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1e6:.1f} MB + {sum(f.stat().st_size for f in FILES.glob('*.jpg')) / 1e6:.1f} MB of files in {FILES}; {len(G)} diagrams, {len(D)} brochures; stats {S}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
