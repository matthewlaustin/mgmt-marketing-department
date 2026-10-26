"""Render the exploded parts diagram of every catalog parts page straight from the PDF (vector art, so it
is sharp at any size), plus every reference chart (pump curves, dimension drawings, sizing charts).

  python3 scripts/diagram_crops.py            # data/raw/pentair/diagrams/pNNN.png, charts/cNNN.png + JSON metadata

The diagram runs from under the page heading to the top of the first parts-table header ("ITEM" / "Part No."),
found from the PDF's word positions. Pages whose table starts at the top (diagram beside the table) use the
whole page body. A chart is cropped from its printed title down to the next title, table header or the
page's bottom margin.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/raw/pentair/pdf/catalog2025/pentair-catalog-2025-2026-digital-1-compressed.pdf"
OUT = ROOT / "data/raw/pentair/diagrams"
CHARTS = ROOT / "data/raw/pentair/charts"
META = ROOT / "data/work/pentair/d3/diagrams.json"
CMETA = ROOT / "data/work/pentair/d3/charts.json"
HEADER = re.compile(r"^(ITEM|Item|PART|Part|P/N|Ref\.?|REF\.?)$")
DPI = 250


def words_of(page):
    return page.extract_words(keep_blank_chars=False, use_text_flow=False)


def diagram_box(page, words) -> tuple[float, float, float, float]:
    w, h = page.width, page.height
    body = [x for x in words if 30 < x["x0"] < w - 30]
    # a parts-table header row has at least two header words side by side (ITEM + PART); a lone "P/N" is the Prop 65 box
    cands = sorted(x["top"] for x in body if HEADER.match(x["text"]) and x["top"] > h * 0.12)
    header_tops = [t for t in cands if sum(1 for u in cands if abs(u - t) <= 3) >= 2]
    bottom = header_tops[0] - 4 if header_tops else h * 0.93
    # the heading and subtitle are centred; the Prop 65 box (right third), side tab and callout digits are not
    head = [x for x in body if x["top"] < h * 0.12 and x["x1"] < w * 0.62 and not x["text"].isdigit()]
    top = (max(x["bottom"] for x in head) + 4) if head else h * 0.08
    if bottom - top < h * 0.15:  # table-first layouts: the whole page body (Matthew 2026-10-26)
        return (w * 0.06, h * 0.08, w * 0.90, h * 0.95)
    return (w * 0.06, top, w * 0.90, bottom)


def render(page, box, path: Path, masks: list[tuple[float, float, float, float]] = ()) -> tuple[int, int]:
    x0, top, x1, bottom = box
    x0, top = max(0, x0), max(0, top)
    x1, bottom = min(page.width, x1), min(page.height, bottom)
    im = page.crop((x0, top, x1, bottom)).to_image(resolution=DPI)
    pil = im.original.convert("RGB")
    k = DPI / 72
    from PIL import ImageDraw
    draw = ImageDraw.Draw(pil)
    for mx0, mtop, mx1, mbottom in masks:  # page coordinates -> crop pixels
        draw.rectangle(((mx0 - x0) * k - 4, (mtop - top) * k - 4, (mx1 - x0) * k + 4, (mbottom - top) * k + 4), fill="white")
    pil.save(str(path), format="PNG")
    return pil.size


def prop65_box(words) -> list[tuple[float, float, float, float]]:
    """The California Proposition 65 warning box, from its first and last words."""
    starts = [x for x in words if x["text"].upper() == "CALIFORNIA"]
    ends = [x for x in words if "p65warnings" in x["text"]]
    out = []
    for a in starts:
        b = next((e for e in ends if 0 < e["top"] - a["top"] < 120), None)
        if b:
            box_words = [x for x in words if a["top"] - 2 <= x["top"] <= b["bottom"] + 2 and x["x0"] >= min(a["x0"], b["x0"]) - 40]
            out.append((min(x["x0"] for x in box_words), a["top"], max(x["x1"] for x in box_words), b["bottom"]))
    return out


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def chart_box(page, words, title: str, other_titles: list[str]) -> tuple[float, float, float, float] | None:
    """Locate a chart by its printed title: the crop runs from the title to the next title/table/bottom."""
    w, h = page.width, page.height
    lines: dict[float, list] = {}
    for x in words:
        lines.setdefault(round(x["top"]), []).append(x)
    line_text = {t: norm(" ".join(x["text"] for x in sorted(ws, key=lambda x: x["x0"]))) for t, ws in lines.items()}
    key = norm(title)
    key3 = " ".join(key.split()[:3])
    hits = sorted(t for t, txt in line_text.items() if key3 and (key3 in txt or key in txt))
    if not hits:
        return None
    top = hits[0] - 2
    # which column: the title's own words (the full key, e.g. "... 3 hp models") set the x-range when two charts share a line
    row = sorted(lines[hits[0]], key=lambda x: x["x0"])
    groups, cur = [], []
    for x in row:
        if cur and x["x0"] - cur[-1]["x1"] > 30:
            groups.append(cur)
            cur = []
        cur.append(x)
    if cur:
        groups.append(cur)
    cx0, cx1 = w * 0.06, w * 0.91
    if len(groups) > 1:
        mine = next((g for g in groups if key in norm(" ".join(x["text"] for x in g))), None) or \
               next((g for g in groups if key3 in norm(" ".join(x["text"] for x in g))), groups[0])
        i = groups.index(mine)
        if i > 0:
            cx0 = (groups[i - 1][-1]["x1"] + mine[0]["x0"]) / 2
        if i < len(groups) - 1:
            cx1 = (mine[-1]["x1"] + groups[i + 1][0]["x0"]) / 2
    stops = []
    for t, txt in line_text.items():
        if t <= top + 8:
            continue
        if any(" ".join(norm(o).split()[:3]) in txt for o in other_titles if o != title and norm(o).split()):
            stops.append(t)
        if any(HEADER.match(x["text"]) for x in lines[t]) and sum(1 for x in lines[t] if HEADER.match(x["text"])) >= 2:
            stops.append(t)
        if re.search(r"^see page \d+ for replacement parts|california proposition 65", txt):
            stops.append(t)
    bottom = min(stops) - 4 if stops else h * 0.94
    if bottom - top < 40:
        return None
    return (cx0, top, cx1, bottom)


def main() -> int:
    con = sqlite3.connect(ROOT / "data/catalog.db")
    pages = sorted({p for (p,) in con.execute("SELECT DISTINCT pdf_page FROM fitment WHERE pdf_page > 0")})
    charts = con.execute("SELECT id, pdf_page, title FROM reference_tables WHERE kind = 'chart' AND pdf_page > 0 ORDER BY pdf_page, id").fetchall()
    by_page: dict[int, list] = {}
    for cid, pg, title in charts:
        by_page.setdefault(pg, []).append((cid, title))
    OUT.mkdir(parents=True, exist_ok=True)
    CHARTS.mkdir(parents=True, exist_ok=True)
    meta, cmeta = {}, {}
    with pdfplumber.open(PDF) as pdf:
        for n in pages:
            page = pdf.pages[n - 1]
            path = OUT / f"p{n:03d}.png"
            words = words_of(page)
            size = render(page, diagram_box(page, words), path, prop65_box(words))
            meta[n] = {"file": str(path.relative_to(ROOT)), "width": size[0], "height": size[1], "bytes": path.stat().st_size}
        for n, items in by_page.items():
            page = pdf.pages[n - 1]
            words = words_of(page)
            titles = [t for _, t in items]
            for cid, title in items:
                box = chart_box(page, words, title, titles)
                located = box is not None
                if not box:  # title not printed as written: the whole page body, so the chart is still reachable
                    box = (page.width * 0.06, page.height * 0.08, page.width * 0.91, page.height * 0.95)
                path = CHARTS / f"c{cid:04d}.png"
                size = render(page, box, path, prop65_box(words))
                cmeta[cid] = {"file": str(path.relative_to(ROOT)), "width": size[0], "height": size[1], "bytes": path.stat().st_size,
                              "page": n, "title": title, "located": located}
    META.write_text(json.dumps(meta, indent=1))
    CMETA.write_text(json.dumps(cmeta, indent=1))
    print(f"{len(meta)} diagrams from {len(pages)} parts pages; {sum(1 for c in cmeta.values() if c['located'])} of {len(charts)} charts located, the rest as page renders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
