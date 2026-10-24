"""Check harmonization decisions before consolidation applies them.

  python3 scripts/harmonize_check.py h03        # one packet's decisions
  python3 scripts/harmonize_check.py all        # every decision file, plus catalog-wide uniqueness

A decision file data/work/pentair/harmonize/out/hNN.json is
  {"packet": "hNN", "decisions": [{"mpn", "title", "product_line"?, "kind"?, "confidence", "reason"}]}
with one decision for every SKU in the packet (audit packets sNN: only the SKUs they change). Checks: the SKU is in the packet, title shape rules,
a reason for every decision, and that no two active SKUs end up with the same derived title.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from product_namer.review import KINDS, normalize_title, title_problems  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HARM = ROOT / "data/work/pentair/harmonize"


def derived(title: str) -> str:
    return title.split(" - ", 1)[1] if " - " in title else title


def check_packet(name: str) -> list[str]:
    packet = json.loads((HARM / "packets" / f"{name}.json").read_text())
    out_path = HARM / "out" / f"{name}.json"
    if not out_path.exists():
        return [f"{name}: no decision file at {out_path}"]
    decisions = json.loads(out_path.read_text()).get("decisions", [])
    skus = {s["mpn"]: s for s in packet["skus"]}
    errors, seen = [], set()
    for d in decisions:
        mpn = d.get("mpn", "")
        where = f"{name} {mpn}"
        if mpn not in skus:
            errors.append(f"{where}: not in this packet")
            continue
        if mpn in seen:
            errors.append(f"{where}: decided twice")
        seen.add(mpn)
        title = d.get("title", "")
        if title != normalize_title(title):
            errors.append(f"{where}: title not normalized (curly quotes or double spaces)")
        kind = d.get("kind", skus[mpn]["kind"])
        if kind not in KINDS:
            errors.append(f"{where}: bad kind {kind!r}")
        errors.extend(f"{where}: {e}" for e in title_problems(skus[mpn]["brand"], mpn, title, kind))
        if not d.get("reason"):
            errors.append(f"{where}: every decision needs a reason")
        if d.get("confidence") not in ("high", "review"):
            errors.append(f"{where}: confidence must be 'high' or 'review'")
    if not name.startswith("s"):  # audit packets (sNN) record only the SKUs they change
        for mpn in sorted(set(skus) - seen):
            errors.append(f"{name} {mpn}: no decision")
    return errors


def catalog_duplicates() -> list[str]:
    """Derived titles shared by two active SKUs once every decision is applied."""
    con = sqlite3.connect(ROOT / "data/catalog.db")
    titles = {m: t for m, t in con.execute("SELECT mpn, title FROM products WHERE status = 'active' AND title != ''")}
    flagged = set()
    for path in sorted((HARM / "out").glob("*.json")):  # hNN first, then sNN audits override
        for d in json.loads(path.read_text()).get("decisions", []):
            if d["mpn"] in titles:
                titles[d["mpn"]] = d["title"]
            if d.get("confidence") == "review":
                flagged.add(d["mpn"])
    by_derived: dict[str, list[str]] = {}
    for m, t in titles.items():
        by_derived.setdefault(derived(t), []).append(m)
    return [(set(ms), f"derived title {t!r} shared by {', '.join(sorted(ms))}") for t, ms in sorted(by_derived.items())
            if len(ms) > 1 and not set(ms) <= flagged]


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = sorted(p.stem for p in (HARM / "out").glob("*.json")) if arg == "all" else [arg]
    errors = [e for n in names for e in check_packet(n)]
    if arg == "all":
        errors += [msg for _ms, msg in catalog_duplicates()]
    else:
        mine = {d["mpn"] for d in json.loads((HARM / "out" / f"{arg}.json").read_text()).get("decisions", [])} \
            if (HARM / "out" / f"{arg}.json").exists() else set()
        errors += [msg for ms, msg in catalog_duplicates() if ms & mine]
    for e in errors:
        print(e)
    print("OK" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
