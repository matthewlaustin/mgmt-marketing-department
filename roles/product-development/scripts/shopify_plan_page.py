"""Plan page for Matthew: how the catalog becomes Shopify-ready data (reports/shopify-plan.html, an Artifact;
answers come back through ArtifactData collections shopify_answers / shopify_followups).

Reads data/catalog.db and the poolgeek.com Shopify crawl (data/raw/shops/www.poolgeek.com) for the counts and
the proposed product-type mapping. The plan text itself lives in scripts/shopify_plan_template.html.
"""
from __future__ import annotations

import glob
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "scripts/shopify_plan_template.html"
OUT = ROOT / "reports/shopify-plan.html"

# our derived product_type -> (poolgeek Product Type, tag family, tag value, confidence note)
TYPE_MAP = {
    "Pump Part": ("Replacement Parts", "Parts Type", "Pump Parts", ""),
    "Pool Pump Part": ("Replacement Parts", "Parts Type", "Pump Parts", ""),
    "Pool Heater Part": ("Replacement Parts", "Parts Type", "Heater Parts", ""),
    "Heater Part": ("Replacement Parts", "Parts Type", "Heater Parts", ""),
    "Filter Part": ("Replacement Parts", "Parts Type", "Filter Parts", ""),
    "Pool Filter Part": ("Replacement Parts", "Parts Type", "Filter Parts", ""),
    "Cartridge Filter Part": ("Replacement Parts", "Parts Type", "Filter Parts", ""),
    "Sand Filter Part": ("Replacement Parts", "Parts Type", "Filter Parts", ""),
    "D.E. Filter Part": ("Replacement Parts", "Parts Type", "Filter Parts", ""),
    "Commercial Filter Part": ("Replacement Parts", "Parts Type", "Filter Parts", ""),
    "Filter Cartridge / Grid Part": ("Filter Cartridges", "Product Type", "Filter Cartridges", "cartridges and grids sold as cartridges, as the store does for Pleatco"),
    "Cleaner Part": ("Replacement Parts", "Parts Type", "Pool Cleaner Parts", ""),
    "Automatic Pool Cleaner Part": ("Replacement Parts", "Parts Type", "Pool Cleaner Parts", ""),
    "Automation Part": ("Replacement Parts", "Parts Type", "Controller Parts", ""),
    "Pool Automation Part": ("Replacement Parts", "Parts Type", "Controller Parts", ""),
    "Valve Part": ("Replacement Parts", "Parts Type", "Plumbing Parts", "the store has no valve-parts tag; new tag Valve Parts is the alternative"),
    "Skimmer / Fitting Part": ("Replacement Parts", "Parts Type", "Plumbing Parts", "skimmer parts could go under Skimmers instead"),
    "Light Part": ("Replacement Parts", "Parts Type", "Light Parts", "new tag"),
    "Pool Light Part": ("Replacement Parts", "Parts Type", "Light Parts", "new tag"),
    "Sanitizer Part": ("Replacement Parts", "Parts Type", "Salt Cell Parts", "IntelliChlor and iChlor parts; Rainbow feeder parts go to Chemical Feeder Parts by family"),
    "Sanitizer / Water Chemistry Part": ("Replacement Parts", "Parts Type", "Chemical Feeder Parts", "split by family as above"),
    "In-Floor Cleaning Part": ("Replacement Parts", "Parts Type", "In-Floor Cleaning Parts", "new tag"),
    "Water Feature Part": ("Replacement Parts", "Parts Type", "Water Feature Parts", "new tag"),
    "Maintenance Part": ("Replacement Parts", "Parts Type", "Maintenance Equipment Parts", "new tag"),
    "Pool Pump": ("Pool Equipment", "Equipment Type", "Pool Pumps", ""),
    "Pool Heater": ("Pool Equipment", "Equipment Type", "Pool Heaters", ""),
    "Cartridge Filter": ("Pool Equipment", "Equipment Type", "Pool Filters", ""),
    "Sand Filter": ("Pool Equipment", "Equipment Type", "Pool Filters", ""),
    "D.E. Filter": ("Pool Equipment", "Equipment Type", "Pool Filters", ""),
    "Commercial Filter": ("Pool Equipment", "Equipment Type", "Pool Filters", "commercial lines get a second tag, Commercial"),
    "Pool Light": ("Pool Equipment", "Equipment Type", "Pool Lights", ""),
    "Pool Automation": ("Pool Equipment", "Equipment Type", "Controllers", ""),
    "Sanitizer / Water Chemistry": ("Pool Equipment", "Equipment Type", "Salt Chlorine Generators", "Rainbow feeders go to Chemical Feeders by family"),
    "Automatic Pool Cleaner": ("Pool Equipment", "Equipment Type", "Automatic Pool Cleaners", ""),
    "Valve": ("Pool Equipment", "Equipment Type", "Valves", ""),
    "In-Floor Cleaning": ("Pool Equipment", "Equipment Type", "In-Floor Cleaning Systems", "new tag"),
    "Water Feature": ("Pool Equipment", "Equipment Type", "Water Features", "new tag"),
    "Maintenance / Safety Equipment": ("Maintenance Equipment", "Maintenance Equipment Type", "by family", "Vacuum Heads, Skimmers, Safety Products, Ladders, Extension Poles... chosen per family"),
    "Pool Fitting / Skimmer": ("Replacement Parts", "Parts Type", "Skimmers or Plumbing Parts", "skimmers to Skimmers, fittings and drains to Plumbing Parts, by family"),
    "Filter Cartridge / Grid": ("Filter Cartridges", "Product Type", "Filter Cartridges", ""),
    "Pool Accessory Part": ("Replacement Parts", "Parts Type", "by family", "decided per family"),
    "Pool Filter": ("Pool Equipment", "Equipment Type", "Pool Filters", ""),
    "Pool Accessory": ("Pool Equipment", "Equipment Type", "by family", "mixed bag; decided per family"),
}


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
    types = q("select d.value, count(*) from derived_specs d join products p on p.mpn=d.mpn where d.attr='product_type' and p.status='active' group by 1")
    s["types"] = [[v, c] + list(TYPE_MAP.get(v, ("?", "?", "?", "no mapping yet"))) for v, c in types]
    s["types"].sort(key=lambda r: (-r[1], r[0]))
    s["unmapped"] = sorted({v for v, _ in types} - set(TYPE_MAP))
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
