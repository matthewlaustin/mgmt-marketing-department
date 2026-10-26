"""Load phase-3 extraction output (data/work/pentair/d3/out/*.json) into data/catalog.db.

  python3 scripts/d3_load.py

Run after consolidate.py (it needs the products table). Rebuilds the phase-3 tables:
families, product_families, specs, prices, fitment, reference_tables, data_issues.
Data for an MPN that isn't an active product (excluded, or never listed) is dropped and counted.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/catalog.db"
OUT = ROOT / "data/work/pentair/d3/out"
PRINTED_OFFSET = 2  # PDF page = printed page + 2 throughout the catalog

SCHEMA = """
DROP TABLE IF EXISTS families;
DROP TABLE IF EXISTS product_families;
DROP TABLE IF EXISTS specs;
DROP TABLE IF EXISTS prices;
DROP TABLE IF EXISTS fitment;
DROP TABLE IF EXISTS reference_tables;
DROP TABLE IF EXISTS data_issues;
DROP TABLE IF EXISTS attributes;
CREATE TABLE attributes (
    key TEXT PRIMARY KEY, unit TEXT, meaning TEXT, controlled INTEGER NOT NULL, spec_count INTEGER NOT NULL
);
CREATE TABLE families (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, brand TEXT, parent TEXT, category TEXT,
    description TEXT, features TEXT NOT NULL, notes TEXT NOT NULL, parts_pages TEXT NOT NULL, pages TEXT NOT NULL
);
CREATE TABLE product_families (
    mpn TEXT NOT NULL, family_id TEXT, role TEXT NOT NULL, band TEXT, pdf_page INTEGER NOT NULL
);
CREATE TABLE specs (
    mpn TEXT NOT NULL, attr TEXT NOT NULL, value TEXT NOT NULL, value_num REAL, unit TEXT,
    raw TEXT, pdf_page INTEGER NOT NULL
);
CREATE TABLE prices (
    mpn TEXT NOT NULL, us_list REAL, can_list REAL, price_note TEXT, pdf_page INTEGER NOT NULL
);
CREATE TABLE fitment (
    part_mpn TEXT NOT NULL, family_ids TEXT NOT NULL, models TEXT NOT NULL, mpns TEXT NOT NULL,
    item TEXT, qty REAL, condition TEXT, raw TEXT, pdf_page INTEGER NOT NULL
);
CREATE TABLE reference_tables (
    id INTEGER PRIMARY KEY, kind TEXT NOT NULL, family_ids TEXT NOT NULL, title TEXT, columns TEXT, rows TEXT, summary TEXT,
    pdf_page INTEGER NOT NULL
);
CREATE TABLE data_issues (
    batch TEXT NOT NULL, pdf_page INTEGER, mpn TEXT, question TEXT NOT NULL
);
"""


def as_list(v) -> list:
    if v in (None, ""):
        return []
    return v if isinstance(v, list) else [v]


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and re.fullmatch(r"-?\d+(\.\d+)?", v.strip()):
        return float(v)
    return None


# x_ keys agents invented that mean a controlled key (or one canonical x_ key)
ALIASES = {
    "x_backwash_valve": "backwash_valve_size", "x_backwash_valve_size": "backwash_valve_size",
    "x_operating_weight": "operating_weight", "x_tank_count": "tank_count", "x_max_water_temp": "max_water_temp",
    "x_de_required": "de_required", "x_breaker_size": "breaker_size", "x_thermal_efficiency": "thermal_efficiency",
    "x_heat_exchanger_material": "heat_exchanger_material", "x_gas_line_size": "gas_line_size", "x_hhp": "hhp",
    "x_min_speed_rpm": "min_speed", "x_max_speed_rpm": "max_speed", "x_conductors": "conductors",
    "x_wire_count": "conductors", "x_option": "options", "x_carton_weight": "weight", "x_wt": "weight",
    "x_application": "pool_type", "x_program": "program", "x_media_weight": "media_weight",
    "x_ultra_replacement": "upgrade", "x_nsf_flow_gpm_per_sqft": "flow_per_sqft",
    "x_flow_rated_per_sqft": "flow_per_sqft",
    "x_epa_registration": "x_epa_number", "x_doe_dppp": "x_doe_dedicated_purpose_pool_pump",
    "x_flow_30_mj_cm2": "x_flow_30mj", "x_flow_40_mj_cm2": "x_flow_40mj", "x_flow_60_mj_cm2": "x_flow_60mj",
    "x_a_dim": "x_dim_a", "x_b_dim": "x_dim_b", "x_inside_diameter": "x_inner_diameter",
    "x_scale_unit": "x_scale_units", "x_language": "x_languages", "x_features": "x_feature",
    "x_compatible_with": "x_compatibility", "x_tablet_capacity_lb": "x_tablet_capacity",
    "x_nozzle_sizes": "x_nozzle_size",
}
DROP = {"x_description", "x_band"}  # copies of the title / band text
TURNOVER = re.compile(r"x_turnover(?:_capacity|_gal)?_(\d+)h")
BOILERPLATE = re.compile(r"proposition 65|p65warnings|cancer and reproductive harm", re.I)


def normalize_spec(s: dict) -> dict | None:
    """Map an extracted spec onto the controlled list; None drops it."""
    attr = s.get("attr", "")
    if attr in DROP:
        return None
    m = TURNOVER.fullmatch(attr)
    if m:
        v = s.get("value")
        n = num(v.replace(",", "")) if isinstance(v, str) else num(v)
        gal = int(n) if n is not None and n == int(n) else (n if n is not None else v)
        return dict(s, attr="turnover_capacity", value={"hours": int(m.group(1)), "gallons": gal}, unit="gal")
    return dict(s, attr=ALIASES.get(attr, attr))


def text(v) -> str:
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def merge_family(fams: dict, f: dict) -> None:
    fid = f["id"]
    parts = [l["printed_page"] + PRINTED_OFFSET for l in f.get("links") or []
             if l.get("kind") == "replacement_parts" and isinstance(l.get("printed_page"), int)]
    cur = fams.get(fid)
    if cur is None:
        fams[fid] = {"id": fid, "name": f["name"], "brand": f.get("brand"), "parent": f.get("parent"),
                     "category": f.get("category"), "description": f.get("description"),
                     "features": list(f.get("features") or []),
                     "notes": [x for x in f.get("notes") or [] if not BOILERPLATE.search(x)], "parts_pages": parts, "pages": [f["page"]]}
        return
    for k in ("brand", "parent", "category", "description"):
        cur[k] = cur[k] or f.get(k)
    cur["features"] += [x for x in f.get("features") or [] if x not in cur["features"]]
    cur["notes"] += [x for x in f.get("notes") or [] if x not in cur["notes"] and not BOILERPLATE.search(x)]
    cur["parts_pages"] += [p for p in parts if p not in cur["parts_pages"]]
    if f["page"] not in cur["pages"]:
        cur["pages"].append(f["page"])


def load(con: sqlite3.Connection, out_dir: Path = OUT) -> dict[str, int]:
    active = {m for (m,) in con.execute("SELECT mpn FROM products WHERE status = 'active'")}
    con.executescript(SCHEMA)
    fams: dict[str, dict] = {}
    dropped = 0
    for path in sorted(out_dir.glob("d*.json")):
        d = json.loads(path.read_text())
        batch = d.get("batch", path.stem)
        for f in d.get("families", []):
            merge_family(fams, f)
        for p in d.get("products", []):
            m, pg = p["mpn"], p["page"]
            if m not in active:
                dropped += 1
                continue
            fam = p.get("family")
            for fid in as_list(fam) or [None]:
                con.execute("INSERT INTO product_families VALUES (?,?,?,?,?)", (m, fid, p["role"], p.get("band"), pg))
            seen = set()
            for s in filter(None, map(normalize_spec, p.get("specs", []))):
                key = (s["attr"], text(s["value"]))
                if key in seen:
                    continue
                seen.add(key)
                con.execute("INSERT INTO specs VALUES (?,?,?,?,?,?,?)",
                            (m, s["attr"], text(s["value"]), num(s["value"]), s.get("unit"), s.get("raw"), pg))
            pr = p.get("prices") or {}
            if pr or p.get("price_note"):
                con.execute("INSERT INTO prices VALUES (?,?,?,?,?)",
                            (m, pr.get("us_list"), pr.get("can_list"), p.get("price_note") or None, pg))
        for f in d.get("fitment", []):
            if f["part"] not in active:
                dropped += 1
                continue
            fits = f.get("fits") or {}
            con.execute("INSERT INTO fitment VALUES (?,?,?,?,?,?,?,?,?)",
                        (f["part"], json.dumps(as_list(fits.get("family"))), json.dumps(as_list(fits.get("models")), ensure_ascii=False),
                         json.dumps(as_list(fits.get("mpns"))), text(f["item"]) if f.get("item") not in (None, "") else None,
                         num(f.get("qty")), f.get("condition") or None, f.get("raw"), f["page"]))
        for r in d.get("references", []):
            con.execute("INSERT INTO reference_tables (kind, family_ids, title, columns, rows, summary, pdf_page) VALUES (?,?,?,?,?,?,?)",
                        (r["kind"], json.dumps(as_list(r.get("family"))), r.get("title"), json.dumps(r.get("columns") or [], ensure_ascii=False),
                         json.dumps(r.get("rows") or [], ensure_ascii=False), r.get("summary") or None, r["page"]))
        for i in d.get("issues", []):
            con.execute("INSERT INTO data_issues VALUES (?,?,?,?)", (batch, i.get("page"), i.get("mpn") or None, i["question"]))
    for f in fams.values():
        con.execute("INSERT INTO families VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (f["id"], f["name"], f["brand"], f["parent"], f["category"], f["description"],
                     json.dumps(f["features"], ensure_ascii=False), json.dumps(f["notes"], ensure_ascii=False), json.dumps(f["parts_pages"]), json.dumps(sorted(f["pages"]))))
    # the catalog sometimes prints different list prices for one SKU on different pages
    for m, pages in con.execute("""SELECT mpn, group_concat(pdf_page || ': ' || us_list || ' / ' || can_list, '; ')
                                   FROM prices WHERE us_list IS NOT NULL GROUP BY mpn
                                   HAVING count(DISTINCT us_list) > 1""").fetchall():
        con.execute("INSERT INTO data_issues VALUES ('price_check', NULL, ?, ?)",
                    (m, f"Different list prices printed on different pages (page: US / Can): {pages}. Which is current?"))
    controlled = {}
    for line in (ROOT / "docs/data-v3-attributes.md").read_text().splitlines():
        m = re.match(r"\| ([a-z_0-9]+) \| ([^|]*) \|([^|]*)\|", line)
        if m and m.group(1) != "key":
            controlled[m.group(1)] = (m.group(2).strip().replace("—", "") or None, m.group(3).strip() or None)
    used = dict(con.execute("SELECT attr, count(*) FROM specs GROUP BY attr"))
    for k in sorted(set(controlled) | set(used)):
        unit, meaning = controlled.get(k, (None, None))
        con.execute("INSERT INTO attributes VALUES (?,?,?,?,?)", (k, unit, meaning, int(k in controlled), used.get(k, 0)))
    con.commit()
    counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
              for t in ("attributes", "families", "product_families", "specs", "prices", "fitment", "reference_tables", "data_issues")}
    counts["dropped_not_active"] = dropped
    return counts


def main() -> int:
    con = sqlite3.connect(DB)
    print(load(con))
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
