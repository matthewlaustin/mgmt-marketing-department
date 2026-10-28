"""Compare two independent reviews of the same pages.

  python3 scripts/compare_reviews.py reviews reviews_b 35 152 200

Prints MPNs found by only one reviewer, and MPNs where brand, title, kind or status differ.
Agreement on every field is the bar for accepting a page without a third look.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from product_namer.review import normalize_title  # noqa: E402

WORK = Path(__file__).resolve().parents[1] / "data/work/pentair"
FIELDS = ("brand", "title", "kind", "status", "replaced_by")


def load(review_dir: str, page: int) -> dict[str, dict]:
    path = WORK / review_dir / f"p{page:03d}.json"
    if not path.exists():
        return {}
    return {r["mpn"]: dict(r, title=normalize_title(r.get("title", "")))
            for r in json.loads(path.read_text()).get("records", [])}


def main() -> int:
    a_dir, b_dir, *pages = sys.argv[1:]
    total = agree = 0
    for page in map(int, pages):
        a, b = load(a_dir, page), load(b_dir, page)
        diffs = []
        for mpn in sorted(set(a) | set(b)):
            total += 1
            if mpn not in a or mpn not in b:
                diffs.append(f"  {mpn}: only in {a_dir if mpn in a else b_dir}")
                continue
            fields = [f for f in FIELDS if (a[mpn].get(f) or "") != (b[mpn].get(f) or "")]
            if not fields:
                agree += 1
                continue
            for f in fields:
                diffs.append(f"  {mpn} {f}:\n      A: {a[mpn].get(f)}\n      B: {b[mpn].get(f)}")
        print(f"p{page:03d}: {len(a)} vs {len(b)} records, {len(diffs)} difference(s)")
        print("\n".join(diffs))
    print(f"\nfull agreement on {agree}/{total} MPNs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
