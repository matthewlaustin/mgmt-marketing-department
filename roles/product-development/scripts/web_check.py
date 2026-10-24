"""Check a Phase 2 web review (one pass of one packet) before it is compared or applied.

  python3 scripts/web_check.py PASS PACKET      # PASS: a | b | final; e.g. web_check.py a w03

Review file: data/work/pentair/web/<PASS>/<PACKET>.json =
  {"packet", "records": [{"mpn", "brand", "title", "kind", "status", "product_line", "confidence",
                          "source_row", "notes"}],
   "dismissed": [{"mpn", "reason"}]}
Every SKU in the packet is either a record or dismissed with a reason. Records: the MPN is a packet
SKU, `source_row` is one of Pentair's published rows for it, the title passes the shared title rules,
and its derived title is unique within the packet and against active catalog titles.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from product_namer.review import KINDS, normalize_title, title_problems  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "data/work/pentair/web"
STATUSES = {"active", "discontinued", "not_for_sale_usa"}
BRANDS = {"Pentair", "Sta-Rite", "Pleatco"}


def derived(title: str) -> str:
    return title.split(" - ", 1)[1] if " - " in title else title


def is_z_twin(a: str, b: str) -> bool:
    """Same product sold through another channel: a trailing Z is the retail/service pack
    (Matthew, 2026-10-24); an "EC-" prefix is Pentair's e-commerce-exclusive number (printed on
    pentair.com: "Products beginning with EC- are exclusive to e-commerce sales")."""
    a, b = a.upper(), b.upper()
    return (a + "Z" == b or b + "Z" == a or a == "EC-" + b or b == "EC-" + a
            or a == b + "-EC" or b == a + "-EC")


def check(pass_name: str, packet: str) -> list[str]:
    pk = json.loads((WEB / "packets" / f"{packet}.json").read_text())
    skus = {s["mpn"]: s for g in pk["pages"] for s in g["skus"]}
    path = WEB / pass_name / f"{packet}.json"
    if not path.exists():
        return [f"no review file at {path}"]
    review = json.loads(path.read_text())
    con = sqlite3.connect(ROOT / "data/catalog.db")
    catalog_titles = {derived(t): m for m, t in con.execute(
        "SELECT mpn, title FROM products WHERE status = 'active' AND title != ''")}
    errors, seen, titles = [], set(), {}
    for r in review.get("records", []):
        mpn = r.get("mpn", "")
        where = f"{packet} {mpn}"
        if mpn not in skus:
            errors.append(f"{where}: not a website-only SKU of this packet")
            continue
        if mpn in seen:
            errors.append(f"{where}: recorded twice")
        seen.add(mpn)
        if r.get("brand") not in BRANDS:
            errors.append(f"{where}: brand must be one of {sorted(BRANDS)}")
        if r.get("kind") not in KINDS:
            errors.append(f"{where}: bad kind {r.get('kind')!r}")
        if r.get("status") not in STATUSES:
            errors.append(f"{where}: bad status {r.get('status')!r}")
        if r.get("confidence") not in ("high", "review"):
            errors.append(f"{where}: confidence must be 'high' or 'review'")
        if r.get("source_row") not in {row["row_text"] for row in skus[mpn]["rows"]}:
            errors.append(f"{where}: source_row must be copied exactly from one of the SKU's published rows")
        title = r.get("title", "")
        if title != normalize_title(title):
            errors.append(f"{where}: title not normalized")
        errors.extend(f"{where}: {e}" for e in title_problems(r.get("brand", ""), mpn, title, r.get("kind")))
        d = derived(title)
        if d in titles and not (r.get("confidence") == "review" and titles[d][1] == "review"):
            errors.append(f"{where}: derived title identical to {titles[d][0]}'s")
        titles.setdefault(d, (mpn, r.get("confidence")))
        twin = catalog_titles.get(d)
        named = re.findall(r"channel twin of ([A-Za-z0-9\-./]+)", r.get("notes") or "")
        if twin and not is_z_twin(mpn, twin) and twin not in named:
            errors.append(f"{where}: derived title identical to catalog SKU {twin}'s")
    dismissed = {d.get("mpn") for d in review.get("dismissed", []) if d.get("reason")}
    for mpn in sorted(set(skus) - seen - dismissed):
        errors.append(f"{packet} {mpn}: neither recorded nor dismissed with a reason")
    return errors


def main() -> int:
    pass_name, packet = sys.argv[1], sys.argv[2]
    errors = check(pass_name, packet)
    for e in errors:
        print(e)
    print("OK" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
