"""Crop the exploded parts diagram out of every catalog parts page (Matthew 2026-10-26: for now a part's
picture is the diagram of the list it is on).

  python3 scripts/diagram_crops.py        # writes data/raw/pentair/diagrams/pNNN.png + data/work/pentair/d3/diagrams.json

The crop runs from under the page heading to the top of the first parts-table header ("ITEM" / "Part No."),
found from the PDF's word positions (pdfplumber), and is cut from the page PNG. Pages whose parts table
starts at the top (no diagram) are skipped.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pdfplumber
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/raw/pentair/pdf/catalog2025/pentair-catalog-2025-2026-digital-1-compressed.pdf"
PNG = ROOT / "data/raw/pentair/pdf/png"
OUT = ROOT / "data/raw/pentair/diagrams"
META = ROOT / "data/work/pentair/d3/diagrams.json"
HEADER = re.compile(r"^(ITEM|Item|PART|Part|P/N|Ref\.?|REF\.?)$")


def diagram_box(page) -> tuple[float, float, float, float] | None:
    """(x0, top, x1, bottom) in PDF points, or None when the page has no diagram above its table."""
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    w, h = page.width, page.height
    body = [x for x in words if 30 < x["x0"] < w - 30]
    # the first table header row: a line holding "ITEM"/"Part" words below the heading area
    # a parts-table header row has at least two header words side by side (ITEM + PART ...); a lone "P/N"
    # is the Prop 65 box or a footnote
    cands = sorted(x["top"] for x in body if HEADER.match(x["text"]) and x["top"] > h * 0.12)
    header_tops = [t for t in cands if sum(1 for u in cands if abs(u - t) <= 3) >= 2]
    bottom = header_tops[0] - 4 if header_tops else h * 0.93
    # the heading block: large text near the top; take the lowest word above 12% of the page as the top edge
    # the heading and subtitle are centred; the Prop 65 box (right third) and side tab are not part of the heading
    head = [x for x in body if x["top"] < h * 0.12 and x["x1"] < w * 0.62 and not x["text"].isdigit()]  # digits are callouts
    top = (max(x["bottom"] for x in head) + 6) if head else h * 0.08
    if bottom - top < h * 0.15:
        # table-first layouts (cleaner and filter parts pages put the diagram beside or under the table):
        # Matthew 2026-10-26 accepted the whole diagram page as the part's picture for now
        return (w * 0.06, h * 0.08, w * 0.90, h * 0.95)
    return (w * 0.06, top, w * 0.90, bottom)


def main() -> int:
    con = sqlite3.connect(ROOT / "data/catalog.db")
    pages = sorted({p for (p,) in con.execute("SELECT DISTINCT pdf_page FROM fitment WHERE pdf_page > 0")})
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    with pdfplumber.open(PDF) as pdf:
        for n in pages:
            page = pdf.pages[n - 1]
            box = diagram_box(page)
            img = Image.open(PNG / f"p{n:03d}.png")
            sx, sy = img.width / page.width, img.height / page.height
            crop = img.crop((int(box[0] * sx), int(box[1] * sy), int(box[2] * sx), int(box[3] * sy)))
            path = OUT / f"p{n:03d}.png"
            crop.save(path, optimize=True)
            meta[n] = {"file": str(path.relative_to(ROOT)), "width": crop.width, "height": crop.height, "bytes": path.stat().st_size}
    META.write_text(json.dumps(meta, indent=1))
    print(f"{len(meta)} diagrams from {len(pages)} parts pages; skipped {len(pages) - len(meta)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
