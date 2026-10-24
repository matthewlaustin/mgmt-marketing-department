"""Build review packets for catalog pages and validate finished page reviews.

  python3 scripts/catalog_pages.py packets 35 152 200       # or a range: 7-540
  python3 scripts/catalog_pages.py validate 35 152 200      # or: validate all
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from product_namer.review import build_packet, load_json, page_words, validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/raw/pentair/pdf/catalog2025/pentair-catalog-2025-2026-digital-1-compressed.pdf"
PNG = ROOT / "data/raw/pentair/pdf/png"
WORK = ROOT / "data/work/pentair"
REVIEWS = WORK / os.environ.get("REVIEW_DIR", "reviews")


def parse_pages(args: list[str]) -> list[int]:
    if args == ["all"]:
        return sorted(int(p.stem[1:]) for p in (REVIEWS).glob("p*.json"))
    pages: list[int] = []
    for a in args:
        if "-" in a:
            lo, hi = map(int, a.split("-"))
            pages.extend(range(lo, hi + 1))
        else:
            pages.append(int(a))
    return pages


def main() -> int:
    cmd, *rest = sys.argv[1:]
    pages = parse_pages(rest)
    if cmd == "packets":
        for n in pages:
            packet = build_packet(str(PDF), n, str(PNG))
            (WORK / "packets" / f"p{n:03d}.json").write_text(json.dumps(packet, indent=1, ensure_ascii=False))
            print(f"p{n:03d}: {len(packet['candidate_tokens'])} candidate tokens")
        return 0
    if cmd == "validate":
        failed = 0
        with pdfplumber.open(PDF) as pdf:
            for n in pages:
                path = REVIEWS / f"p{n:03d}.json"
                if not path.exists():
                    print(f"p{n:03d}: MISSING review")
                    failed += 1
                    continue
                errors = validate(load_json(path), page_words(pdf.pages[n - 1]))
                status = "OK" if not errors else f"{len(errors)} problem(s)"
                print(f"p{n:03d}: {status}")
                for e in errors:
                    print(f"    - {e}")
                failed += bool(errors)
        return 1 if failed else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
