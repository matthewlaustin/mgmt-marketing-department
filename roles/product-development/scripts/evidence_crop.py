"""Crop the printed catalog row for a SKU from the rendered page image (for showing evidence to a person).

  python3 scripts/evidence_crop.py OUT_DIR MPN PAGE [MPN PAGE ...]
  FULL_WIDTH=1 python3 scripts/evidence_crop.py ...   # whole page width (model charts)

Finds the MPN in the page's text layer, then crops a band around that line from
data/raw/pentair/pdf/png/pNNN.png (rendered at scale 2). Writes OUT_DIR/<MPN>_p<PAGE>.png and
prints one line per crop; a SKU not found as a word on the page is reported, not guessed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pdfplumber
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/raw/pentair/pdf/catalog2025/pentair-catalog-2025-2026-digital-1-compressed.pdf"
PNG = ROOT / "data/raw/pentair/pdf/png"
SCALE = 2  # fetch_pentair_catalog.sh renders at scale 2
PAD_Y, LEFT, RIGHT = 14, 40, 430  # points around the matched word


def crop(pdf, out_dir: Path, mpn: str, page_no: int) -> str:
    page = pdf.pages[page_no - 1]
    first = mpn.split(" ")[0]
    hits = [w for w in page.extract_words() if w["text"].strip("*¹²³#,;:()").upper() == first.upper()]
    if not hits:
        return f"{mpn} p{page_no}: not found in the text layer"
    w = hits[0]
    # a SKU printed on several nearby rows (one part, many models) is cropped as one band
    rows = [h for h in hits if abs(h["x0"] - w["x0"]) < 20 and h["top"] - w["top"] < 260]
    img = Image.open(PNG / f"p{page_no:03d}.png")
    left, right = (0, page.width) if os.environ.get("FULL_WIDTH") else (max(0, w["x0"] - LEFT), min(page.width, w["x0"] + RIGHT))
    box = (left * SCALE, max(0, w["top"] - PAD_Y) * SCALE, right * SCALE, min(page.height, max(h["bottom"] for h in rows) + PAD_Y) * SCALE)
    name = f"{mpn.replace(' ', '_').replace('/', '-')}_p{page_no}.png"
    img.crop(tuple(int(v) for v in box)).save(out_dir / name)
    return f"{mpn} p{page_no}: {name}"


def main() -> int:
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    args = sys.argv[2:]
    with pdfplumber.open(PDF) as pdf:
        for mpn, page in zip(args[::2], args[1::2]):
            print(crop(pdf, out_dir, mpn, int(page)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
