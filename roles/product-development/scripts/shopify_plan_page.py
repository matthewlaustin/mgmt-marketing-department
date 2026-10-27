"""Plan page for Matthew: how the catalog becomes Shopify-ready data (reports/shopify-plan.html, an Artifact;
answers come back through ArtifactData collections shopify_answers / shopify_followups).

Reads data/catalog.db for the counts and the proposed category tree; the poolgeek.com crawl only for the SKU overlap figure. The plan text itself lives in scripts/shopify_plan_template.html.
"""
from __future__ import annotations

import glob
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "scripts/shopify_plan_template.html"
OUT = ROOT / "reports/shopify-plan.html"

# our derived product_type -> proposed storefront category (designed from the catalog, not from the current store)
CATEGORY = {
    "Pumps": ["Pool Pump", "Pump Part", "Pool Pump Part"],
    "Filters": ["Cartridge Filter", "Sand Filter", "D.E. Filter", "Pool Filter", "Filter Part", "Pool Filter Part",
                "Cartridge Filter Part", "Sand Filter Part", "D.E. Filter Part"],
    "Filter cartridges and grids": ["Filter Cartridge / Grid", "Filter Cartridge / Grid Part"],
    "Heaters and heat pumps": ["Pool Heater", "Pool Heater Part", "Heater Part"],
    "Lighting": ["Pool Light", "Light Part", "Pool Light Part"],
    "Automation and controls": ["Pool Automation", "Automation Part", "Pool Automation Part"],
    "Sanitizers and chemical feeders": ["Sanitizer / Water Chemistry", "Sanitizer Part", "Sanitizer / Water Chemistry Part"],
    "Pool cleaners": ["Automatic Pool Cleaner", "Cleaner Part", "Automatic Pool Cleaner Part"],
    "In-floor cleaning": ["In-Floor Cleaning", "In-Floor Cleaning Part"],
    "Water features": ["Water Feature", "Water Feature Part"],
    "Valves and plumbing": ["Valve", "Valve Part"],
    "Skimmers, drains and fittings": ["Pool Fitting / Skimmer", "Skimmer / Fitting Part"],
    "Maintenance and safety": ["Maintenance / Safety Equipment", "Maintenance Part", "Pool Accessory", "Pool Accessory Part"],
    "Commercial": ["Commercial Filter", "Commercial Filter Part"],
}
TYPE_TO_CAT = {t: c for c, ts in CATEGORY.items() for t in ts}


def stats(con: sqlite3.Connection) -> dict:
    q = lambda s: con.execute(s).fetchall()  # noqa: E731
    s = {
        "skus": q("select count(*) from products where status='active'")[0][0],
        "kinds": q("select kind,count(*) from products where status='active' group by kind order by 2 desc"),
        "brands": q("select brand,count(*) from products where status='active' group by brand order by 2 desc"),
        "with_list": q("select count(*) from product_prices where us_list is not null")[0][0],
        "call": q("select count(*) from product_prices where price_note like '%CALL%'")[0][0],
        "with_photo": q("select count(*) from product_photos")[0][0],
        "small_photo": q("select count(*) from product_photos where tier like '%500-999%'")[0][0],
        "with_specs": q("select count(distinct mpn) from specs")[0][0],
        "spec_rows": q("select count(*) from specs")[0][0],
        "with_docs": q("select count(distinct mpn) from document_links where mpn is not null")[0][0],
        "fam_docs": q("select count(distinct family_id) from document_links where family_id is not null")[0][0],
        "docs": q("select count(*) from documents")[0][0],
        "models_with_parts": q("select count(distinct model_mpn) from model_parts")[0][0],
        "parts_with_models": q("select count(distinct part_mpn) from model_parts")[0][0],
        "with_diagram": q("select count(distinct mpn) from image_links il join images i on i.id=il.image_id where i.role='diagram'")[0][0],
        "families": q("select count(*) from families")[0][0],
        "with_desc": q("select count(distinct pf.mpn) from product_families pf join families f on f.id=pf.family_id where f.description<>''")[0][0],
        "xref": q("select count(distinct mpn) from cross_references")[0][0],
        "replacements": q("select count(*) from replacements")[0][0],
        "weight": q("select count(distinct mpn) from specs where attr='weight'")[0][0],
        "no_price_wg": q("select count(*) from products p where status='active' and kind='whole_good' and not exists(select 1 from product_prices x where x.mpn=p.mpn and x.us_list is not null)")[0][0],
        "no_price": q("select count(*) from products p where status='active' and not exists(select 1 from product_prices x where x.mpn=p.mpn and x.us_list is not null)")[0][0],
        "no_photo": q("select count(*) from products p where status='active' and not exists(select 1 from product_photos x where x.mpn=p.mpn)")[0][0],
        "dual_brand": q("select count(*) from products where status='active' and brand='Pentair/Sta-Rite'")[0][0],
        "service": q("select count(*) from products where status='active' and kind='service'")[0][0],
        "trademark_titles": q("select count(*) from products where status='active' and (title like '%®%' or title like '%™%')")[0][0],
    }
    rows = q("select d.value, p.kind, count(*) from derived_specs d join products p on p.mpn=d.mpn where d.attr='product_type' and p.status='active' group by 1,2")
    cats = {c: {"wg": 0, "parts": 0, "types": set()} for c in CATEGORY}
    s["unmapped"] = sorted({v for v, _, _ in rows} - set(TYPE_TO_CAT))
    for v, kind, c in rows:
        cat = cats.get(TYPE_TO_CAT.get(v))
        if cat is None:
            continue
        cat["wg" if kind == "whole_good" else "parts"] += c
        cat["types"].add(v)
    fam = q("select d.value, count(distinct pf.family_id) from derived_specs d join product_families pf on pf.mpn=d.mpn where d.attr='product_type' group by 1")
    famc = {c: set() for c in CATEGORY}
    for v, k in q("select d.value, pf.family_id from derived_specs d join product_families pf on pf.mpn=d.mpn join families f on f.id=pf.family_id where d.attr='product_type' and (f.parent is null or f.parent='')"):
        if TYPE_TO_CAT.get(v) in famc:
            famc[TYPE_TO_CAT[v]].add(k)
    s["cats"] = [[c, d["wg"], d["parts"], len(famc[c]), sorted(d["types"])] for c, d in cats.items()]
    s["fam_images"] = q("select count(distinct family_id) from image_links il join images i on i.id=il.image_id where i.role in ('main','gallery','marketing') and family_id is not null")[0][0]
    s["charts"] = q("select count(*) from reference_tables where kind='chart'")[0][0]
    s["tables"] = q("select count(*) from reference_tables where kind='table'")[0][0]
    s["top_families"] = q("select count(*) from families where parent is null or parent=''")[0][0]
    return s


def store_stats(con: sqlite3.Connection) -> dict:
    rows = []
    for f in sorted(glob.glob(str(ROOT / "data/raw/shops/www.poolgeek.com/page*.json"))):
        rows += json.load(open(f)).get("products", [])
    ours = {r[0].upper() for r in con.execute("select mpn from products where status='active'")}
    skus = {v["sku"].strip().upper() for p in rows for v in p["variants"] if v.get("sku")}
    vend = [p for p in rows if p["vendor"] in ("Pentair", "Sta-Rite", "Pleatco")]
    vend_skus = {v["sku"].strip().upper() for p in vend for v in p["variants"] if v.get("sku")}
    return {
        "store_products": len(rows),
        "store_brand_products": len(vend),
        "matched": len(skus & ours),
        "store_only": len(vend_skus - ours),
        "multi_variant": sum(1 for p in rows if len(p["variants"]) > 1),
    }


def main() -> int:
    con = sqlite3.connect(ROOT / "data/catalog.db")
    data = {"S": stats(con), "P": store_stats(con)}
    html = TEMPLATE.read_text().replace("/*DATA*/", json.dumps(data, ensure_ascii=False))
    OUT.write_text(html)
    print(OUT, len(html), "bytes; unmapped types:", data["S"]["unmapped"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
