"""Render the exploded parts diagram(s) of every catalog parts page straight from the PDF (vector art, so it
is sharp at any size), plus every reference chart (pump curves, dimension drawings, sizing charts).

  python3 scripts/diagram_crops.py            # data/raw/pentair/diagrams/pNNN_k.png, charts/cNNNN.png + JSON metadata

A diagram is found from the drawing itself, not the page layout: the PDF's curve objects (and embedded raster
drawings) are clustered on a coarse grid; each cluster of real size is one drawing. Its box then grows to take
in the callout digits, bracket lines and short captions that touch it. Table rules, row fills, the side tab,
the page heading and the California Proposition 65 box never enter a box, and the Prop 65 box is painted
white where a crop still overlaps it. A page gets a diagram only when it has a parts table (ITEM / PART NO.
header); a continuation page without a drawing reuses the previous page's diagram when the heading matches.
A chart is cropped from its printed title down to the next title, table header or the page's bottom margin.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import numpy as np
import pdfplumber
from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/raw/pentair/pdf/catalog2025/pentair-catalog-2025-2026-digital-1-compressed.pdf"
OUT = ROOT / "data/raw/pentair/diagrams"
CHARTS = ROOT / "data/raw/pentair/charts"
META = ROOT / "data/work/pentair/d3/diagrams.json"
CMETA = ROOT / "data/work/pentair/d3/charts.json"
HEADER = re.compile(r"^(ITEM|Item|PART|Part|P/N|Ref\.?|REF\.?)$")
DPI = 300
CHART_DPI = 250
Box = tuple[float, float, float, float]


def words_of(page):
    return page.extract_words(keep_blank_chars=False, use_text_flow=False)


def header_rows(words, h) -> list[float]:
    """Tops of parts-table header rows: two header words (ITEM + PART NO.) within 10 pt of each other."""
    hw = [x for x in words if HEADER.match(x["text"]) and x["top"] > h * 0.05]
    return sorted({round(a["top"]) for a in hw if any(b is not a and abs(b["top"] - a["top"]) <= 10 for b in hw)})


def prop65_boxes(words, rects) -> list[Box]:
    """The California Proposition 65 warning box: its words, widened to the frame rectangle drawn around them."""
    out = []
    for a in [x for x in words if x["text"].upper() == "CALIFORNIA"]:
        b = next((e for e in words if "p65warnings" in e["text"] and 0 < e["top"] - a["top"] < 120), None)
        if not b:
            continue
        box = [min(a["x0"], b["x0"]) - 6, a["top"] - 6, max(a["x1"], b["x1"]) + 6, b["bottom"] + 6]
        for r in rects:
            if r["x0"] <= a["x0"] + 2 and r["x1"] >= b["x1"] - 2 and r["top"] <= a["top"] + 2 and r["bottom"] >= b["bottom"] - 2 and r["x1"] - r["x0"] < 300:
                box = [min(box[0], r["x0"] - 2), min(box[1], r["top"] - 2), max(box[2], r["x1"] + 2), max(box[3], r["bottom"] + 2)]
        out.append(tuple(box))
    return out




HEADERISH = re.compile(r"^(ITEM|Item|PART|Part|P/N|Ref\.?|REF\.?|No\.|NO\.|Description|DESCRIPTION|US|Can\.|List|LIST|Qty\.?|QTY\.?|Model|MODEL|Price|PRICE)$")


def table_masks(words, rects, lines, w, h) -> list[Box]:
    """Where a drawing's area runs under the parts table (scanned drawings often do): the table cells (every
    row is a filled rectangle, grey or white, that never overlaps a drawing), the rules drawn inside each
    table, the header line, the page heading and the footer, painted white in the crop."""
    cells = [r for r in rects if r.get("fill") and not r.get("stroke") and (r["x1"] - r["x0"]) >= 10 and 8 <= (r["bottom"] - r["top"]) <= 70]
    out = [bbox(c) for c in cells]
    tables: list[Box] = []  # clusters of touching cells
    for c in sorted(cells, key=lambda c: (c["top"], c["x0"])):
        b = bbox(c)
        hit = next((i for i, t in enumerate(tables) if overlaps(t, b, 6)), None)
        if hit is None:
            tables.append(b)
        else:
            tables[hit] = union(tables[hit], b)
    for l in lines:
        if any(inside(l, (t[0] - 3, t[1] - 3, t[2] + 3, t[3] + 3)) for t in tables):
            out.append(bbox(l))
    for T in header_rows(words, h):
        out += [bbox(x) for x in words if T - 6 <= x["top"] <= T + 14 and HEADERISH.match(x["text"])]
    for x in words:
        if x["top"] < h * 0.09 or x["bottom"] > h * 0.965:
            out.append(bbox(x))
    return out


def inside(o, box: Box) -> bool:
    return o["x0"] >= box[0] - 1 and o["x1"] <= box[2] + 1 and o["top"] >= box[1] - 1 and o["bottom"] <= box[3] + 1


def overlaps(a: Box, b: Box, pad: float = 0) -> bool:
    return a[0] < b[2] + pad and b[0] < a[2] + pad and a[1] < b[3] + pad and b[1] < a[3] + pad


def union(a: Box, b: Box) -> Box:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def bbox(o) -> Box:
    return (o["x0"], o["top"], o["x1"], o["bottom"])


def heading(words, w, h, p65: list[Box] = ()) -> str:
    """The page heading (top band, side tab and Prop 65 box left out), for matching continuation pages."""
    head = [x for x in words if x["top"] < h * 0.09 and x["x0"] > 28 and x["x1"] < w - 28 and not any(inside(x, b) for b in p65)]
    return " ".join(x["text"].lower() for x in sorted(head, key=lambda x: (round(x["top"] / 4), x["x0"])))


def same_line(a: str, b: str) -> bool:
    strip = lambda s: re.sub(r"\(cont.?d\)", " ", s).split()[:2]
    return bool(strip(a)) and strip(a) == strip(b)


def find_diagrams(page, words, p65: list[Box]) -> list[Box]:
    """Boxes of the drawings on the page, top to bottom then left to right."""
    w, h = page.width, page.height

    def ok(o):  # not in the margins (side tab, folios), the footer or the Prop 65 box
        return o["x1"] > 28 and o["x0"] < w - 28 and o["bottom"] > h * 0.03 and o["top"] < h * 0.965 and not any(inside(o, b) for b in p65)

    narrow = lambda o: (o["x1"] - o["x0"]) < 0.3 * w  # table rules, header bars and section rules are wider
    seeds = [o for o in page.curves if narrow(o) and ok(o)]
    seeds += [o for o in page.images if (o["x1"] - o["x0"]) >= 40 and (o["bottom"] - o["top"]) >= 40 and ok(o)]
    is_diag = lambda o: abs(o["x1"] - o["x0"]) > 1.5 and abs(o["bottom"] - o["top"]) > 1.5
    lines = [o for o in page.lines if narrow(o) and ok(o)]
    seeds += [o for o in lines if is_diag(o)]  # callout leader lines
    straight = [o for o in lines if not is_diag(o)]  # brackets, dimension lines, but also table rules
    straight += [o for o in page.rects if narrow(o) and (o["bottom"] - o["top"]) < 0.5 * h and o.get("stroke") and ok(o)]
    cell, dil = 6, 3  # 6 pt grid cells, drawings within 18 pt of each other join
    gw, gh = int(w / cell) + 1, int(h / cell) + 1
    grid = np.zeros((gh, gw), dtype=bool)
    for o in seeds:
        x0, x1 = max(0, int(o["x0"] / cell) - dil), min(gw - 1, int(o["x1"] / cell) + dil)
        y0, y1 = max(0, int(o["top"] / cell) - dil), min(gh - 1, int(o["bottom"] / cell) + dil)
        grid[y0:y1 + 1, x0:x1 + 1] = True
    lab = np.zeros_like(grid, dtype=int)
    n = 0
    for sy in range(gh):
        for sx in range(gw):
            if grid[sy, sx] and not lab[sy, sx]:
                n += 1
                lab[sy, sx] = n
                stack = [(sy, sx)]
                while stack:
                    y, x = stack.pop()
                    for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                        if 0 <= yy < gh and 0 <= xx < gw and grid[yy, xx] and not lab[yy, xx]:
                            lab[yy, xx] = n
                            stack.append((yy, xx))
    comps: dict[int, dict] = {}
    for o in seeds:
        i = lab[min(gh - 1, int((o["top"] + o["bottom"]) / 2 / cell)), min(gw - 1, int((o["x0"] + o["x1"]) / 2 / cell))]
        c = comps.setdefault(i, {"n": 0, "img": False, "box": None})
        c["n"] += 1
        c["img"] |= "srcsize" in o
        c["box"] = bbox(o) if c["box"] is None else union(c["box"], bbox(o))
    big = [c for c in comps.values() if (c["n"] >= 12 or c["img"]) and c["box"][2] - c["box"][0] >= 50 and c["box"][3] - c["box"][1] >= 50]
    tmask = table_masks(words, page.rects, page.lines, w, h)
    free = [x for x in words if not any(inside(x, m) for m in tmask)]  # not a table row, the heading or the footer
    straight = [o for o in straight if not any(inside(o, m) for m in tmask)]  # not a table rule
    for c in big:  # grow: straight lines / stroked rects and words touching the drawing (callouts, brackets, captions)
        for _ in range(3):
            b = c["box"]
            for o in straight:
                if overlaps(b, bbox(o), 2):
                    b = union(b, bbox(o))
            for x in free:
                cx, cy = (x["x0"] + x["x1"]) / 2, (x["top"] + x["bottom"]) / 2
                if b[0] <= cx <= b[2] and b[1] <= cy <= b[3]:
                    b = union(b, bbox(x))
                elif overlaps(b, bbox(x), 8) and len([y for y in free if abs(y["top"] - x["top"]) < 3]) <= 8 and not any(inside(x, p) for p in p65):
                    b = union(b, bbox(x))  # a short caption line beside or below, never a table row
            c["box"] = b
    merged = True
    while merged:
        merged = False
        for i in range(len(big)):
            for j in range(i + 1, len(big)):
                if overlaps(big[i]["box"], big[j]["box"], 4):
                    big[i]["box"] = union(big[i]["box"], big[j]["box"])
                    del big[j]
                    merged = True
                    break
            if merged:
                break
    big.sort(key=lambda c: (round(c["box"][1] / 40), c["box"][0]))
    return [c["box"] for c in big]


def render(page, box: Box, path: Path, masks: list[Box] = (), dpi: int = DPI, pad: float = 6, trim: bool = True) -> tuple[int, int]:
    x0, top, x1, bottom = box
    x0, top = max(0, x0 - pad), max(0, top - pad)
    x1, bottom = min(page.width, x1 + pad), min(page.height, bottom + pad)
    im = page.crop((x0, top, x1, bottom)).to_image(resolution=dpi)
    pil = im.original.convert("RGB")
    k = dpi / 72
    draw = ImageDraw.Draw(pil)
    for mx0, mtop, mx1, mbottom in masks:  # page coordinates -> crop pixels
        if overlaps((x0, top, x1, bottom), (mx0, mtop, mx1, mbottom)):
            draw.rectangle(((mx0 - x0) * k - 2, (mtop - top) * k - 2, (mx1 - x0) * k + 2, (mbottom - top) * k + 2), fill="white")
    if trim:  # white margins off, a 12 px border kept
        bg = Image.new("RGB", pil.size, "white")
        diff = ImageChops.difference(pil, bg).convert("L").point(lambda v: 255 if v > 48 else 0)
        bb = diff.getbbox()
        if bb:
            pil = pil.crop((max(0, bb[0] - 12), max(0, bb[1] - 12), min(pil.width, bb[2] + 12), min(pil.height, bb[3] + 12)))
    pil.save(str(path), format="PNG", optimize=True)
    return pil.size


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def chart_box(page, words, title: str, other_titles: list[str]) -> Box | None:
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
    cx0, cx1 = w * 0.08, w * 0.91
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
        if sum(1 for x in lines[t] if HEADER.match(x["text"])) >= 2:
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
    for old in OUT.glob("p*.png"):
        old.unlink()
    meta: dict[int, dict] = {}
    cmeta = {}
    no_table, no_drawing, reused = [], [], []
    with pdfplumber.open(PDF) as pdf:
        for n in pages:
            page = pdf.pages[n - 1]
            words = words_of(page)
            p65 = prop65_boxes(words, page.rects)
            head = heading(words, page.width, page.height, p65)
            if not header_rows(words, page.height):  # accessory tables on a whole-goods page: no exploded view
                no_table.append(n)
                continue
            boxes = find_diagrams(page, words, p65)
            masks = p65 + table_masks(words, page.rects, page.lines, page.width, page.height)
            if not boxes:
                prev = next((meta[k] for k in (n - 1, n - 2) if k in meta and same_line(meta[k]["heading"], head)), None)
                if prev and "cont" in head:  # "(CONT'D)" of the drawing's own page or its facing page
                    meta[n] = {"heading": head, "diagrams": prev["diagrams"], "from_page": prev.get("from_page", n - 1 if meta.get(n - 1) is prev else n - 2)}
                    reused.append(n)
                else:
                    no_drawing.append(n)
                continue
            entries = []
            for k, box in enumerate(boxes, 1):
                path = OUT / f"p{n:03d}_{k}.png"
                size = render(page, box, path, masks)
                entries.append({"file": str(path.relative_to(ROOT)), "width": size[0], "height": size[1], "bytes": path.stat().st_size,
                                "box": [round(v, 1) for v in box]})
            meta[n] = {"heading": head, "diagrams": entries}
        for n, items in by_page.items():
            page = pdf.pages[n - 1]
            words = words_of(page)
            p65 = prop65_boxes(words, page.rects)
            titles = [t for _, t in items]
            for cid, title in items:
                box = chart_box(page, words, title, titles)
                located = box is not None
                if not box:  # title not printed as written: the whole page body, so the chart is still reachable
                    box = (page.width * 0.08, page.height * 0.08, page.width * 0.91, page.height * 0.95)
                path = CHARTS / f"c{cid:04d}.png"
                size = render(page, box, path, p65, dpi=CHART_DPI, pad=0)
                cmeta[cid] = {"file": str(path.relative_to(ROOT)), "width": size[0], "height": size[1], "bytes": path.stat().st_size,
                              "page": n, "title": title, "located": located}
    META.write_text(json.dumps(meta, indent=1))
    CMETA.write_text(json.dumps(cmeta, indent=1))
    n_img = sum(len(m["diagrams"]) for m in meta.values() if "from_page" not in m)
    print(f"{len(pages)} pages carry parts rows: {len(no_table)} have no parts table (accessory lists), {len(no_drawing)} have a table but no drawing, "
          f"{len(reused)} continuation pages reuse the previous drawing, {len(meta) - len(reused)} pages rendered as {n_img} diagram images")
    print("no drawing:", no_drawing)
    print(f"{sum(1 for c in cmeta.values() if c['located'])} of {len(charts)} charts located, the rest as page renders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
