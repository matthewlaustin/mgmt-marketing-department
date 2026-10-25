"""Check one pass of the v2 retitle (docs/title-rules-v2.md) before it is compared or applied.

  python3 scripts/v2_check.py PASS BATCH      # PASS: a | b | final; e.g. v2_check.py a b07

Review file data/work/pentair/v2/<PASS>/<BATCH>.json = [{"mpn", "brand", "title", "unsure", "why"}],
one entry for every SKU in the batch.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from product_namer.review import BANNED_IN_TITLE, normalize_title  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "data/work/pentair/v2"
BRANDS = {"Pentair", "Sta-Rite", "Pentair/Sta-Rite", "Pleatco"}
# Matthew, 2026-10-25: marketing words ("Low Profile" is exempt: it names Pentair's in-floor valve line), packaging words and unexpanded abbreviations stay out of titles.
V2_BANNED = [
    (re.compile(r"\b(High Performance|Variable Speed|Self[- ]Priming|Commercial|DOE Compliant|Heavy Duty)\b", re.I),
     "marketing word"),
    (re.compile(r"\b(display box|bubble pack|bulk pack|carded|blister)\b", re.I), "packaging word"),
    (re.compile(r"\b(Assy|Subassy|Mfg|Approx|Qty)\b\.?", re.I), "abbreviation not spelled out"),
    (re.compile(r"\bHx\.?\s?Hd\b", re.I), "abbreviation not spelled out"),
    (re.compile(r"\bw/"), "'w/' not written as 'with'"),
    (re.compile(r"\b\d+\s*VAC\b"), "voltage is written 'V'"),
    (re.compile(r"\b(Sq\.? Ft|sq\. ft\.?)\b"), "area is written 'sq ft'"),
]


def v2_problems(brand: str, mpn: str, title: str) -> list[str]:
    errors = []
    if brand not in BRANDS:
        errors.append(f"brand must be one of {sorted(BRANDS)}")
    prefix = f"{brand} {mpn} - "
    if not title.startswith(prefix):
        return errors + [f"title must start with {prefix!r}"]
    if title != normalize_title(title):
        errors.append("title not normalized (quotes or spaces)")
    derived = title[len(prefix):]
    if not derived.strip():
        errors.append("empty title")
    for pattern, message in BANNED_IN_TITLE + V2_BANNED:
        if pattern.search(derived):
            errors.append(f"{message}: {derived!r}")
    return errors


def check(pass_name: str, batch: str) -> list[str]:
    b = json.loads((V2 / "batches" / f"{batch}.json").read_text())
    skus = {s["mpn"] for g in b["groups"] for s in g["skus"]}
    path = V2 / pass_name / f"{batch}.json"
    if not path.exists():
        return [f"no review file at {path}"]
    try:
        recs = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [f"{path}: not valid JSON ({e})"]
    errors, seen = [], set()
    for r in recs:
        mpn = r.get("mpn", "")
        if mpn not in skus:
            errors.append(f"{batch} {mpn}: not a SKU of this batch")
            continue
        if mpn in seen:
            errors.append(f"{batch} {mpn}: listed twice")
        seen.add(mpn)
        errors += [f"{batch} {mpn}: {e}" for e in v2_problems(r.get("brand", ""), mpn, r.get("title", ""))]
        if not isinstance(r.get("unsure"), bool):
            errors.append(f"{batch} {mpn}: 'unsure' must be true or false")
        if r.get("unsure") and not r.get("why"):
            errors.append(f"{batch} {mpn}: unsure without a reason in 'why'")
    errors += [f"{batch} {m}: missing" for m in sorted(skus - seen)]
    return errors


def main() -> int:
    errors = check(sys.argv[1], sys.argv[2])
    for e in errors:
        print(e)
    print("OK" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
