"""Validate a phase-3 extraction batch: python3 scripts/d3_check.py dNNN"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D3 = ROOT / "data/work/pentair/d3"
ROLES = {"model", "part", "kit", "accessory", "replacement"}


def attr_keys() -> dict[str, str]:
    keys = {}
    for line in (ROOT / "docs/data-v3-attributes.md").read_text().splitlines():
        m = re.match(r"\| ([a-z_0-9]+) \| ([^|]*) \|", line)
        if m and m.group(1) != "key":
            keys[m.group(1)] = m.group(2).strip()
    return keys


def check(batch: str) -> list[str]:
    src = json.loads((D3 / f"batches/{batch}.json").read_text())
    pages = {p["page"] for p in src["pages"]}
    skus = {s["mpn"] for p in src["pages"] for s in p["skus"] if not s.get("excluded")}
    excluded = {s["mpn"] for p in src["pages"] for s in p["skus"] if s.get("excluded")}
    out = json.loads((D3 / f"out/{batch}.json").read_text())
    keys, errs = attr_keys(), []

    def page_ok(where: str, rec: dict) -> None:
        if rec.get("page") not in pages:
            errs.append(f"{where}: page {rec.get('page')} is not in this batch")

    fam_ids = set()
    for f in out.get("families", []):
        page_ok(f"family {f.get('id')}", f)
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", f.get("id", "")):
            errs.append(f"family id {f.get('id')!r}: lowercase letters, digits and hyphens")
        if not f.get("name"):
            errs.append(f"family {f.get('id')}: needs a name")
        fam_ids.add(f.get("id"))
    for p in out.get("products", []):
        where = f"product {p.get('mpn')} p{p.get('page')}"
        page_ok(where, p)
        if p.get("mpn") in excluded:
            errs.append(f"{where}: excluded SKU gets no data")
        elif p.get("mpn") not in skus:
            errs.append(f"{where}: not a SKU listed in this batch (use issues)")
        if p.get("role") not in ROLES:
            errs.append(f"{where}: role must be one of {sorted(ROLES)}")
        for s in p.get("specs", []):
            a = s.get("attr", "")
            if a not in keys and not a.startswith("x_"):
                errs.append(f"{where}: unknown attr {a!r} (use the list or an x_ key)")
            if "raw" not in s or s.get("value") in (None, ""):
                errs.append(f"{where}: spec {a} needs value and raw")
        for k, v in (p.get("prices") or {}).items():
            if k not in ("us_list", "can_list") or not isinstance(v, (int, float)):
                errs.append(f"{where}: price {k}={v!r} must be us_list/can_list numbers")
    for f in out.get("fitment", []):
        where = f"fitment {f.get('part')} p{f.get('page')}"
        page_ok(where, f)
        if f.get("part") not in skus:
            errs.append(f"{where}: part is not a listed SKU")
        fits = f.get("fits") or {}
        if not (fits.get("family") or fits.get("models") or fits.get("mpns")):
            errs.append(f"{where}: says nothing about what it fits")
    for r in out.get("references", []):
        page_ok(f"reference {r.get('title')}", r)
        if r.get("kind") not in ("table", "chart"):
            errs.append(f"reference {r.get('title')}: kind is table or chart")
    for i in out.get("issues", []):
        page_ok("issue", i)
    covered = {p.get("mpn") for p in out.get("products", [])} | {f.get("part") for f in out.get("fitment", [])}
    missing = sorted(skus - covered - {i.get("mpn") for i in out.get("issues", [])})
    if missing:
        errs.append(f"SKUs with no data and no issue: {', '.join(missing[:20])}{' …' if len(missing) > 20 else ''}")
    return errs


if __name__ == "__main__":
    errors = check(sys.argv[1])
    print("\n".join(errors) if errors else "OK")
    sys.exit(1 if errors else 0)
