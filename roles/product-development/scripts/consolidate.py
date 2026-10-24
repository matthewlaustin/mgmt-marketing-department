"""Merge validated page reviews into the catalog database and export the sellable SKUs.

  python3 scripts/consolidate.py [review_dir]      # default: reviews_final

Writes data/catalog.db (tables: products, evidence, conflicts) and
data/exports/pentair_skus.csv (status active only: USA, not discontinued).

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
    overrides = load_harmonized()

    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    exported = []
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
            "needs_review": needs_review, "review_notes": " | ".join(notes), "source": SOURCE,
        }
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
    # Derived titles (after "Brand MPN - ") must be unique across the whole catalog, not just within a page.
    dupes = con.execute(
        "SELECT substr(title, instr(title, ' - ') + 3) AS derived, group_concat(mpn) FROM products "
        "WHERE title != '' AND status = 'active' GROUP BY derived HAVING count(*) > 1").fetchall()
    for _derived, mpns in dupes:
        for mpn in mpns.split(","):
            con.execute("UPDATE products SET needs_review = 1, review_notes = trim(review_notes || ' | ' || ?, ' |') "
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

    counts = dict(con.execute("SELECT status, count(*) FROM products GROUP BY status").fetchall())
    conflicts = con.execute("SELECT count(DISTINCT mpn) FROM conflicts").fetchone()[0]
    print(f"products: {sum(counts.values())} {counts}; exported {len(exported)}; MPNs with page conflicts: {conflicts}; "
          f"duplicate titles: {len(dupes)}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
