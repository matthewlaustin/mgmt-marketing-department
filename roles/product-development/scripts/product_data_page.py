"""Build reports/product-data.html: phase-3 summary, questions for Matthew, and a part-number lookup
showing every spec, price and fitment attached to a SKU."""
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
con = sqlite3.connect(ROOT / "data/catalog.db")

fams, fidx = [], {}
for fid, name, cat in con.execute("SELECT id, name, category FROM families ORDER BY id"):
    fidx[fid] = len(fams)
    fams.append([fid, name, cat or ""])

P = {}
for mpn, brand, title in con.execute("SELECT mpn, brand, title FROM products WHERE status = 'active'"):
    P[mpn] = {"t": title, "b": brand, "f": [], "r": "", "s": [], "p": [], "x": []}
for mpn, fid, role in con.execute("SELECT DISTINCT mpn, family_id, role FROM product_families"):
    if mpn in P:
        P[mpn]["r"] = P[mpn]["r"] or role
        if fid in fidx and fidx[fid] not in P[mpn]["f"]:
            P[mpn]["f"].append(fidx[fid])
for mpn, attr, value, unit, page in con.execute("SELECT mpn, attr, value, unit, pdf_page FROM specs ORDER BY mpn, attr, pdf_page"):
    P[mpn]["s"].append([attr, value, unit or "", page])
for mpn, us, can, note, page in con.execute("SELECT mpn, us_list, can_list, price_note, pdf_page FROM prices ORDER BY mpn, pdf_page"):
    P[mpn]["p"].append([us, can, note or "", page])
for part, fids, models, mpns, item, qty, cond, page in con.execute(
        "SELECT part_mpn, family_ids, models, mpns, item, qty, condition, pdf_page FROM fitment ORDER BY part_mpn, pdf_page"):
    fl = [fidx[f] for f in json.loads(fids) if f in fidx]
    P[part]["x"].append([fl, json.loads(models) + json.loads(mpns), item or "", qty, cond or "", page])

issues = defaultdict(list)
for mpn, page, q in con.execute("SELECT mpn, pdf_page, question FROM data_issues WHERE mpn IS NOT NULL"):
    if mpn in P:
        issues[mpn].append([page, q])
for m, lst in issues.items():
    P[m]["i"] = lst

q = lambda s: con.execute(s).fetchone()[0]
stats = {
    "active": len(P),
    "with_data": q("SELECT count(DISTINCT mpn) FROM (SELECT mpn FROM product_families UNION SELECT part_mpn FROM fitment)"),
    "specs": q("SELECT count(*) FROM specs"),
    "priced": q("SELECT count(DISTINCT mpn) FROM prices WHERE us_list IS NOT NULL"),
    "fitment": q("SELECT count(*) FROM fitment"),
    "parts_fitted": q("SELECT count(DISTINCT part_mpn) FROM fitment"),
    "families": q("SELECT count(*) FROM families"),
    "tables": q("SELECT count(*) FROM reference_tables"),
    "issues": q("SELECT count(*) FROM data_issues"),
    "price_conflicts": q("SELECT count(*) FROM data_issues WHERE batch = 'price_check'"),
    "web_only": q("SELECT count(*) FROM products WHERE status = 'active' AND pages = '0'"),
    "no_data": q("""SELECT count(*) FROM products WHERE status = 'active' AND mpn NOT IN (SELECT mpn FROM product_families)
                    AND mpn NOT IN (SELECT part_mpn FROM fitment)"""),
}
PC = []
for mpn, us, can, basis in con.execute(
        "SELECT mpn, us_list, can_list, basis FROM product_prices WHERE basis LIKE 'most common%' OR basis LIKE 'tie%' ORDER BY basis DESC, mpn"):
    opts = {}
    for u, c, pg in con.execute("SELECT us_list, can_list, pdf_page FROM prices WHERE mpn = ? AND us_list IS NOT NULL ORDER BY pdf_page", (mpn,)):
        opts.setdefault((u, c), []).append(pg)
    PC.append({"m": mpn, "tie": basis.startswith("tie"), "pick": [us, can], "opts": [[u, c, pgs] for (u, c), pgs in opts.items()]})
out = {"P": P, "F": fams, "S": stats, "PC": PC}
page = (ROOT / "scripts/product_data_template.html").read_text().replace(
    "/*DATA*/", json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
(ROOT / "reports/product-data.html").write_text(page)
print(stats, f"{len(page) / 1e6:.1f} MB")
