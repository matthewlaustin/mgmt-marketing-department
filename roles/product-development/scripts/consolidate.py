"""Merge validated page reviews into the catalog database and export the sellable SKUs.

  python3 scripts/consolidate.py [review_dir]      # default: reviews_final

Titles come from the v2 retitle (v2/final) where it covers the SKU.

Writes data/catalog.db (tables: products, evidence, conflicts) and
data/exports/pentair_skus.csv. Discontinued and not-for-USA SKUs are left out of both; their
numbers are listed in data/work/pentair/excluded_mpns.json.

One product per MPN. When an MPN appears on several pages, the title comes from the most
authoritative page type (see PRIORITY); disagreements between pages are recorded in
`conflicts` rather than silently resolved.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from product_namer.review import normalize_title  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/work/pentair"
DB = ROOT / "data/catalog.db"
EXPORT = ROOT / "data/exports/pentair_skus.csv"
EXCLUDED = WORK / "excluded_mpns.json"  # discontinued / not for USA: number and status only
SOURCE = "Pentair Pool Product Catalog 2025-2026 (Dec 2025 digital edition)"

# Lower number wins the title.
PRIORITY = {
    "pleatco_measurement": 0,  # Pleatco titles need the measurement table's dimensions
    "whole_goods": 1,
    "parts": 3,
    "cross_reference": 4,
    "discontinued_list": 5,
    "directory": 9,
    "other": 6,
    "web": 10,  # Phase 2: pentair.com product pages, used only for SKUs the catalog doesn't list
}
# Canonical trademark spellings (directory pp. 4-7), applied to every title and product line. Only marked
# forms are rewritten, so "System 2 Pumps" (IntelliChem) and "System 2.5 in" are left alone.
CANONICAL = [
    (re.compile(r"System[ :]3[®™]|System 3(?= Mod)"), "System:3®"),
    (re.compile(r"System[ :]2[®™]"), "System:2™"),
    (re.compile(r"Hi-Flow™"), "HiFlow™"),
    (re.compile(r"ThermalFlo™"), "ThermalFlo®"),
    (re.compile(r"IntelliProXF(?![®™])"), "IntelliProXF®"),
    (re.compile(r"\bS/S\b"), "SS"),  # stainless steel: "SS" is the catalog's majority form
]


PLEATCO_LINES = {"Advanced": "Pleatco Advanced™", "Ultra": "Pleatco Ultra™"}


def canonical(text: str) -> str:
    for pattern, repl in CANONICAL:
        text = pattern.sub(repl, text)
    return text


KIND_PRIORITY = {"whole_good": 0, "accessory": 1, "part": 2}
STATUS_PRIORITY = {"not_for_sale_usa": 0, "discontinued": 1, "active": 2}  # most restrictive wins

SCHEMA = """
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS evidence;
DROP TABLE IF EXISTS conflicts;
CREATE TABLE products (
    mpn TEXT PRIMARY KEY,
    brand TEXT NOT NULL,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    replaced_by TEXT,
    product_line TEXT,
    parent_product TEXT,
    fits TEXT,
    title_pdf_page INTEGER NOT NULL,
    pages TEXT NOT NULL,
    needs_review INTEGER NOT NULL,
    review_notes TEXT,
    source TEXT NOT NULL
);
CREATE TABLE evidence (
    mpn TEXT NOT NULL,
    pdf_page INTEGER NOT NULL,
    printed_page TEXT,
    page_type TEXT,
    brand TEXT,
    title TEXT,
    kind TEXT,
    status TEXT,
    source_row TEXT,
    context TEXT,
    confidence TEXT,
    notes TEXT
);
CREATE TABLE conflicts (
    mpn TEXT NOT NULL,
    field TEXT NOT NULL,
    values_by_page TEXT NOT NULL
);
"""


def load_harmonized() -> dict[str, dict]:
    """Cross-page title decisions from the harmonization pass (data/work/pentair/harmonize/out/*.json)."""
    out: dict[str, dict] = {}
    for path in sorted((WORK / "harmonize/out").glob("*.json")):  # hNN, then sNN audit decisions win
        for d in json.loads(path.read_text()).get("decisions", []):
            out[d["mpn"].upper()] = d
    return out


def load_web_records() -> list[dict]:
    """Phase 2: final reviews of website-only SKUs (data/work/pentair/web/final/*.json), as evidence rows."""
    urls = {}
    for path in (WORK / "web/packets").glob("w*.json"):
        for g in json.loads(path.read_text())["pages"]:
            for s in g["skus"]:
                urls[s["mpn"]] = g["url"]
    out = []
    for path in sorted((WORK / "web/final").glob("w*.json")):
        for r in json.loads(path.read_text()).get("records", []):
            # pentair.com writes "PKG_56" where the catalog prints "PKG 56": use the catalog form
            web_mpn = r["mpn"]
            mpn = web_mpn.replace("_", " ")
            title = normalize_title(r.get("title", "")).replace(f" {web_mpn} - ", f" {mpn} - ", 1)
            r = dict(r, mpn=mpn, notes=(f"published as {web_mpn}; " if mpn != web_mpn else "") + (r.get("notes") or ""))
            out.append(dict(r, title=title, pdf_page=0, printed_page="",
                            page_type="web", context=urls.get(web_mpn, ""),
                            source_url=f"pentair.com product page {urls.get(web_mpn, '')}"))
    return out


def load_v2_titles() -> dict[str, dict]:
    """The v2 retitle (data/work/pentair/v2/final/*.json): brand and title under docs/title-rules-v2.md."""
    out: dict[str, dict] = {}
    for path in sorted((WORK / "v2/final").glob("b*.json")):
        for r in json.loads(path.read_text()):
            out[r["mpn"]] = r
    return out


def apply_v2(best: dict, v2: dict | None, notes: list[str]) -> dict:
    """v2 titles replace page-review and harmonized titles; gaps and unsure titles are flagged for review."""
    if not v2:
        return best
    if v2.get("gap"):
        if v2.get("unsure"):
            notes.append(f"title gap: {v2.get('why', '')}")
        return dict(best, brand=v2["brand"], title=v2.get("title", ""))
    if v2.get("unsure"):
        notes.append(f"title unsure: {v2.get('why', '')}")
    return dict(best, brand=v2["brand"], title=v2["title"])


def load_owner_decisions() -> dict[str, dict]:
    """Matthew's answers (data/work/pentair/owner_decisions.json): status, brand and replacement calls."""
    path = WORK / "owner_decisions.json"
    if not path.exists():
        return {}
    return {d["mpn"]: d for d in json.loads(path.read_text())["decisions"]}


def apply_owner_decision(row: dict, d: dict | None) -> None:
    """Applied last: the owner's call wins over page reviews and harmonization."""
    if not d:
        return
    if d.get("brand") and d["brand"] != row["brand"] and " - " in row["title"]:
        derived = row["title"].split(" - ", 1)[1]
        row["brand"] = d["brand"]
        row["title"] = f"{d['brand']} {row['mpn']} - {derived}"
    if d.get("status"):
        row["status"] = d["status"]
    if d.get("replaced_by"):
        row["replaced_by"] = d["replaced_by"]
    row["needs_review"] = 0
    row["review_notes"] = f"decided: {d['reason']}"


def main() -> int:
    review_dir = WORK / (sys.argv[1] if len(sys.argv) > 1 else "reviews_final")
    by_mpn: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(review_dir.glob("p*.json")):
        review = json.loads(path.read_text())
        for rec in review.get("records", []):
            rec = dict(rec, title=normalize_title(rec.get("title", "")), pdf_page=review["page"], printed_page=review.get("printed_page"),
                       page_type=review.get("page_type", "other"))
            # "070387z" and "070387Z" are the same SKU printed in different case: one product, upper-case MPN
            printed = rec["mpn"]
            canon = printed.upper()
            if canon != printed:
                prefix = f"{rec.get('brand')} {printed} - "
                if rec["title"].startswith(prefix):
                    rec["title"] = f"{rec.get('brand')} {canon} - " + rec["title"][len(prefix):]
                rec["notes"] = f"printed as {printed}; " + (rec.get("notes") or "")
            by_mpn[canon].append(rec)
    for rec in load_web_records():
        if rec["mpn"] not in by_mpn:
            by_mpn[rec["mpn"]].append(rec)
    overrides = load_harmonized()
    owner = load_owner_decisions()
    v2_titles = load_v2_titles()

    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    exported = []
    excluded: dict[str, str] = {}
    for mpn, recs in sorted(by_mpn.items()):
        recs.sort(key=lambda r: (not r.get("title"), PRIORITY.get(r["page_type"], 6),
                                 KIND_PRIORITY.get(r["kind"], 3), r["pdf_page"]))
        best = recs[0]
        status = min((r.get("status", "active") for r in recs), key=lambda s: STATUS_PRIORITY.get(s, 2))
        notes = [f"p{r['pdf_page']}: {r['notes']}" for r in recs if r.get("confidence") == "review" and r.get("notes")]
        if not best.get("title"):
            notes.append("no page gives this SKU a descriptive title")
        if best["page_type"] == "cross_reference":
            notes.append("title is provisional (cross-reference page only)")
        for field in ("brand", "title"):
            values = {r["pdf_page"]: r.get(field) for r in recs
                      if r.get(field) and r["page_type"] not in ("cross_reference", "discontinued_list")}
            if len(set(values.values())) > 1:
                con.execute("INSERT INTO conflicts VALUES (?,?,?)", (mpn, field, json.dumps(values, ensure_ascii=False)))
                if field == "brand":
                    notes.append(f"brand differs between pages: {values}")
        h = overrides.get(mpn)
        if h:
            best = dict(best, title=h["title"], product_line=h.get("product_line", best.get("product_line", "")),
                        kind=h.get("kind", best["kind"]))
            if h.get("confidence") == "review":
                notes.append(f"harmonized: {h.get('reason', '')}")
        if mpn in v2_titles:
            notes = []  # the v2 retitle settled the page-review notes; only its own open questions remain
        best = apply_v2(best, v2_titles.get(mpn), notes)
        line = canonical(best.get("product_line") or "")
        if best["brand"] == "Pleatco" and line in PLEATCO_LINES:
            line = PLEATCO_LINES[line]
        best = dict(best, title=canonical(best["title"]), product_line=line)
        replaced_by = next((r.get("replaced_by") for r in recs if r.get("replaced_by")), "")
        fits = next((r.get("fits") for r in recs if r.get("fits")), "")
        needs_review = int(bool(notes))
        row = {
            "mpn": mpn, "brand": best["brand"], "title": best["title"], "kind": best["kind"],
            "status": status, "replaced_by": replaced_by, "product_line": best.get("product_line", ""),
            "parent_product": best.get("parent_product", ""), "fits": fits,
            "title_pdf_page": best["pdf_page"], "pages": ",".join(str(r["pdf_page"]) for r in recs),
            "needs_review": needs_review, "review_notes": " | ".join(notes),
            "source": best.get("source_url") or SOURCE,
        }
        apply_owner_decision(row, owner.get(mpn))
        if row["status"] != "active":
            # Discontinued and not-for-USA items get no product data (Matthew, 2026-10-25); only the
            # number is kept, so later runs know it was seen and left out on purpose.
            excluded[mpn] = row["status"]
            continue
        con.execute(f"INSERT INTO products ({','.join(row)}) VALUES ({','.join('?' * len(row))})", list(row.values()))
        for r in recs:
            con.execute(
                "INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (mpn, r["pdf_page"], r.get("printed_page"), r["page_type"], r.get("brand"), r.get("title"),
                 r.get("kind"), r.get("status"), r.get("source_row"), r.get("context"), r.get("confidence"),
                 r.get("notes")),
            )
        if status == "active":
            exported.append(row)
    # Shared derived titles are noted, not flagged: Matthew accepted shared titles where nothing printed
    # tells SKUs apart, and short part titles that repeat across lines (final review, 2026-10-25).
    dupes = con.execute(
        "SELECT substr(title, instr(title, ' - ') + 3) AS derived, group_concat(mpn) FROM products "
        "WHERE title != '' AND status = 'active' GROUP BY derived HAVING count(*) > 1").fetchall()
    for _derived, mpns in dupes:
        for mpn in mpns.split(","):
            con.execute("UPDATE products SET review_notes = trim(review_notes || ' | ' || ?, ' |') "
                        "WHERE mpn = ?", (f"title shared with {mpns}", mpn))
    exported = [dict(zip([c[0] for c in con.execute("SELECT * FROM products").description], row))
                for row in con.execute("SELECT * FROM products WHERE status = 'active' ORDER BY mpn")]
    con.commit()

    EXPORT.parent.mkdir(parents=True, exist_ok=True)
    cols = ["mpn", "brand", "title", "kind", "product_line", "parent_product", "title_pdf_page", "pages",
            "needs_review", "review_notes"]
    with EXPORT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(exported)

    con.executemany("DELETE FROM conflicts WHERE mpn = ?", [(m,) for m in excluded])
    con.commit()
    EXCLUDED.write_text(json.dumps(excluded, indent=0, sort_keys=True))
    counts = dict(con.execute("SELECT status, count(*) FROM products GROUP BY status").fetchall())
    conflicts = con.execute("SELECT count(DISTINCT mpn) FROM conflicts").fetchone()[0]
    print(f"products: {sum(counts.values())} {counts}; left out (discontinued / not for USA): {len(excluded)}; exported {len(exported)}; MPNs with page conflicts: {conflicts}; "
          f"duplicate titles: {len(dupes)}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
