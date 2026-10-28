"""Contact sheets of the chosen outside photos, for checking by eye (watermarks, diagram cards, logos, wrong part).

  python3 scripts/photo_review.py sheets      # data/work/photos/review/sheet_NNN.png + index.json
  python3 scripts/photo_review.py apply F...   # verdict files {"<tile code>": "reason", ...} -> rejected.json

Each tile shows a code (sheet-position, e.g. 012-07), the part number and the title. Reviewers list only the
tiles that fail. apply() records each failed image in data/work/photos/rejected.json, so photo_select.py choose
falls back to the SKU's next candidate; sheets are then rebuilt for the replacements only.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CHOSEN = ROOT / "data/work/photos/chosen.json"
REVIEW = ROOT / "data/work/photos/review"
REJECT = ROOT / "data/work/photos/rejected.json"
REVIEWED = ROOT / "data/work/photos/reviewed.json"  # image_url -> "pass" | reason
TILE, COLS, ROWS = 440, 4, 3


def font(size: int):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def flat(im: Image.Image) -> Image.Image:
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, "white")
        bg.alpha_composite(im)
        return bg.convert("RGB")
    return im.convert("RGB")


def sheets() -> int:
    chosen = json.loads(CHOSEN.read_text())
    reviewed = json.loads(REVIEWED.read_text()) if REVIEWED.exists() else {}
    titles = dict(sqlite3.connect(ROOT / "data/catalog.db").execute("SELECT mpn, title FROM products"))
    todo = [(m, c) for m, c in sorted(chosen.items()) if c["tier"] != "manufacturer" and c.get("grade") in ("ok", "long", "mid") and c["image_url"] not in reviewed]
    REVIEW.mkdir(parents=True, exist_ok=True)
    for old in REVIEW.glob("sheet_*.png"):
        old.unlink()
    f1, f2 = font(17), font(14)
    index, per = {}, COLS * ROWS
    for s in range(0, len(todo), per):
        sheet = Image.new("RGB", (COLS * TILE, ROWS * (TILE + 64)), "#9aa3a8")
        d = ImageDraw.Draw(sheet)
        for i, (m, c) in enumerate(todo[s:s + per]):
            code = f"{s // per:03d}-{i + 1:02d}"
            index[code] = {"mpn": m, "image_url": c["image_url"], "source": c["source"], "title": titles.get(m, "")}
            x, y = (i % COLS) * TILE, (i // COLS) * (TILE + 64)
            with Image.open(ROOT / c["file"]) as im:
                im = flat(im)
                im.thumbnail((TILE - 8, TILE - 8), Image.LANCZOS)
                sheet.paste(Image.new("RGB", (TILE - 4, TILE - 4), "white"), (x + 2, y + 62))
                sheet.paste(im, (x + 2 + (TILE - 4 - im.width) // 2, y + 62 + (TILE - 4 - im.height) // 2))
            d.text((x + 6, y + 4), f"{code}  {m}", fill="black", font=f1)
            d.text((x + 6, y + 26), "\n".join(textwrap.wrap(titles.get(m, ""), 52)[:2]), fill="black", font=f2)
        sheet.save(REVIEW / f"sheet_{s // per:03d}.png")
    (REVIEW / "index.json").write_text(json.dumps(index, indent=1))
    print(f"{len(todo)} photos on {(len(todo) + per - 1) // per} sheets in {REVIEW.relative_to(ROOT)}")
    return 0


def apply(files: list[str]) -> int:
    index = json.loads((REVIEW / "index.json").read_text())
    rejected = json.loads(REJECT.read_text()) if REJECT.exists() else {}
    reviewed = json.loads(REVIEWED.read_text()) if REVIEWED.exists() else {}
    verdicts = {}
    for f in files:
        verdicts.update(json.loads(Path(f).read_text()))
    sheets_seen = {Path(f).stem.split("_")[-1] for f in files}  # verdict_NNN-MMM.json covers sheets NNN..MMM
    covered = set()
    for f in files:
        a, _, b = Path(f).stem.split("_")[-1].partition("-")
        covered.update(f"{n:03d}" for n in range(int(a), int(b or a) + 1))
    n_bad = 0
    for code, e in index.items():
        if code.split("-")[0] not in covered:
            continue
        if code in verdicts:
            rejected[e["image_url"]] = verdicts[code]
            reviewed[e["image_url"]] = verdicts[code]
            n_bad += 1
        else:
            reviewed[e["image_url"]] = "pass"
    REJECT.write_text(json.dumps(rejected, indent=1))
    REVIEWED.write_text(json.dumps(reviewed, indent=1))
    print(f"{len(covered)} sheets applied: {n_bad} photos rejected, {len(rejected)} rejected in all, {len(reviewed)} reviewed")
    return 0


if __name__ == "__main__":
    raise SystemExit(sheets() if sys.argv[1] == "sheets" else apply(sys.argv[2:]))
