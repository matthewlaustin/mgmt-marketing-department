"""Merge validated page reviews into the catalog database and export the sellable SKUs.

  python3 scripts/consolidate.py [review_dir]      # default: reviews

Writes data/catalog.db (tables: products, evidence, conflicts) and
data/exports/pentair_skus.csv (status active only: USA, not discontinued).

One product per MPN. When an MPN appears on several pages, the title comes from the most
authoritative page type (see PRIORITY); disagreements between pages are recorded in
`conflicts` rather than silently resolved.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

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


def main() -> int:
    review_dir = WORK / (sys.argv[1] if len(sys.argv) > 1 else "reviews")
    by_mpn: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(review_dir.glob("p*.json")):
        review = json.loads(path.read_text())
        for rec in review.get("records", []):
            rec = dict(rec, pdf_page=review["page"], printed_page=review.get("printed_page"),
                       page_type=review.get("page_type", "other"))
            by_mpn[rec["mpn"]].append(rec)

    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    exported = []
    for mpn, recs in sorted(by_mpn.items()):
        recs.sort(key=lambda r: (PRIORITY.get(r["page_type"], 6), KIND_PRIORITY.get(r["kind"], 3), r["pdf_page"]))
        best = recs[0]
        status = min((r.get("status", "active") for r in recs), key=lambda s: STATUS_PRIORITY.get(s, 2))
        notes = [f"p{r['pdf_page']}: {r['notes']}" for r in recs if r.get("confidence") == "review" and r.get("notes")]
        for field in ("brand", "title"):
            values = {r["pdf_page"]: r.get(field) for r in recs}
            if len(set(values.values())) > 1:
                con.execute("INSERT INTO conflicts VALUES (?,?,?)", (mpn, field, json.dumps(values, ensure_ascii=False)))
                if field == "brand":
                    notes.append(f"brand differs between pages: {values}")
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
    print(f"products: {sum(counts.values())} {counts}; exported {len(exported)}; MPNs with page conflicts: {conflicts}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
