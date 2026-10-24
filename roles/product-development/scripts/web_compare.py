"""Phase 2: compare the two blind web passes and queue disagreements.

  python3 scripts/web_compare.py

For every packet reviewed in both passes a and b: full agreement (same recorded and dismissed SKUs;
same brand, kind, status and title per SKU) → pass a is copied to web/final/<packet>.json; otherwise
web/adjudicate/<packet>.json lists the differences. Existing finals are never overwritten.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from product_namer.review import normalize_title  # noqa: E402
from web_check import check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "data/work/pentair/web"
FIELDS = ("brand", "kind", "status", "title")


def main() -> int:
    (WEB / "final").mkdir(parents=True, exist_ok=True)
    (WEB / "adjudicate").mkdir(parents=True, exist_ok=True)
    agreed = queued = kept = 0
    for a_path in sorted((WEB / "a").glob("w*.json")):
        b_path = WEB / "b" / a_path.name
        if not b_path.exists():
            continue
        if (WEB / "final" / a_path.name).exists():
            kept += 1
            continue
        # a pass still being written (or failing its check) is not compared yet
        if check("a", a_path.stem) or check("b", a_path.stem):
            continue
        a, b = json.loads(a_path.read_text()), json.loads(b_path.read_text())
        ra = {r["mpn"]: r for r in a.get("records", [])}
        rb = {r["mpn"]: r for r in b.get("records", [])}
        diffs = []
        for mpn in sorted(set(ra) | set(rb)):
            if mpn not in ra or mpn not in rb:
                diffs.append({"mpn": mpn, "only_recorded_in": "a" if mpn in ra else "b"})
                continue
            for f in FIELDS:
                va, vb = ra[mpn].get(f) or "", rb[mpn].get(f) or ""
                if f == "title":
                    va, vb = normalize_title(va), normalize_title(vb)
                if va != vb:
                    diffs.append({"mpn": mpn, "field": f, "a": va, "b": vb})
        if diffs:
            (WEB / "adjudicate" / a_path.name).write_text(json.dumps({"packet": a_path.stem, "differences": diffs},
                                                                    indent=1, ensure_ascii=False))
            queued += 1
        else:
            a["resolution"] = "both passes agree"
            (WEB / "final" / a_path.name).write_text(json.dumps(a, indent=1, ensure_ascii=False))
            agreed += 1
    print(f"agreed → final: {agreed}; queued for adjudication: {queued}; already final: {kept}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
