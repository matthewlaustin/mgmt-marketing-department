"""Compare the two blind v2 passes; agreed batches become final, others are queued for adjudication.

  python3 scripts/v2_compare.py

A batch whose passes agree on every brand and title is copied to v2/final (pass a, with "unsure"
kept if either pass was unsure). Otherwise v2/adjudicate/<batch>.json lists the differences.
Existing finals are never overwritten; a pass still failing its check is skipped.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v2_check import V2, check  # noqa: E402


def main() -> int:
    for d in ("final", "adjudicate"):
        (V2 / d).mkdir(parents=True, exist_ok=True)
    agreed = queued = kept = 0
    for a_path in sorted((V2 / "a").glob("b*.json")):
        name = a_path.name
        if not (V2 / "b" / name).exists() or check("a", a_path.stem) or check("b", a_path.stem):
            continue
        if (V2 / "final" / name).exists():
            kept += 1
            continue
        a = {r["mpn"]: r for r in json.loads(a_path.read_text())}
        b = {r["mpn"]: r for r in json.loads((V2 / "b" / name).read_text())}
        diffs = [{"mpn": m, "a": a[m]["title"], "b": b[m]["title"], "why_a": a[m].get("why", ""),
                  "why_b": b[m].get("why", "")} for m in a if a[m]["title"] != b[m]["title"]]
        if diffs:
            (V2 / "adjudicate" / name).write_text(json.dumps(diffs, indent=1, ensure_ascii=False))
            queued += 1
        else:
            final = [dict(a[m], unsure=bool(a[m].get("unsure") or b[m].get("unsure")),
                          why=a[m].get("why") or b[m].get("why", "")) for m in a]
            (V2 / "final" / name).write_text(json.dumps(final, indent=1, ensure_ascii=False))
            agreed += 1
    print(f"agreed → final: {agreed}; queued for adjudication: {queued}; already final: {kept}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
