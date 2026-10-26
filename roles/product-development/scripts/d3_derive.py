"""Derived attributes: facts a shopper filters on that the catalog states indirectly (in a category, a title,
a band, a feature bullet or a spec), written as plain yes/no or one-word values with the sentence they come
from as evidence.

  python3 scripts/d3_derive.py       # rebuilds table derived_specs in data/catalog.db

Nothing is inferred beyond what Pentair's text says: "App controlled: yes" needs a feature line naming the
app; "Speed: variable" needs the catalog's speed type, THP/WEF columns or "Variable Speed" in the name.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/catalog.db"

SCHEMA = """
DROP TABLE IF EXISTS derived_specs;
CREATE TABLE derived_specs (mpn TEXT NOT NULL, attr TEXT NOT NULL, value TEXT NOT NULL, basis TEXT NOT NULL, source TEXT NOT NULL);
CREATE INDEX derived_specs_mpn ON derived_specs (mpn);
"""

# catalog section (first part of the family category) -> product type / installation
TYPES = [
    (r"PUMPS? - INGROUND|PUMPS? - ABOVEGROUND|PUMPS? - COMMERCIAL|PUMPS? - SPECIALTY|^PUMPS", "Pool Pump"),
    (r"FILTERS? - CARTRIDGE", "Cartridge Filter"), (r"FILTERS? - SAND", "Sand Filter"), (r"FILTERS? - D\.E\.", "D.E. Filter"),
    (r"FILTERS? - COMMERCIAL", "Commercial Filter"), (r"^FILTERS", "Pool Filter"),
    (r"HEATERS? AND HEAT PUMPS|HEATERS", "Pool Heater"), (r"^LIGHTING|LIGHTS", "Pool Light"),
    (r"AUTOMATIC POOL CLEANERS", "Automatic Pool Cleaner"), (r"^AUTOMATION", "Pool Automation"),
    (r"SANITIZERS? & WATER QUALITY", "Sanitizer / Water Chemistry"), (r"^VALVES", "Valve"),
    (r"WATER FEATURES", "Water Feature"), (r"WHITE GOODS", "Pool Fitting / Skimmer"),
    (r"IN-FLOOR", "In-Floor Cleaning"), (r"MAINTENANCE AND SAFETY", "Maintenance / Safety Equipment"),
    (r"PLEATCO", "Filter Cartridge / Grid"), (r"POOL & SPA", "Pool Accessory"),
]
PART_TYPES = [(r"PUMP PARTS", "Pump Part"), (r"FILTER PARTS", "Filter Part"), (r"HEATER PARTS", "Heater Part"),
              (r"LIGHTING PARTS|LIGHTS - NICHES", "Light Part"), (r"CLEANER PARTS", "Cleaner Part"), (r"AUTOMATION PARTS", "Automation Part"),
              (r"VALVE PARTS", "Valve Part"), (r"SANITIZER & WATER QUALITY PARTS", "Sanitizer Part"), (r"WHITE GOODS", "Skimmer / Fitting Part"),
              (r"WATER FEATURE PARTS|WATER FEATURES PARTS", "Water Feature Part"), (r"MAINTENANCE", "Maintenance Part")]


def category_type(cat: str, role: str) -> tuple[str, str] | None:
    head = (cat or "").split("›")[0].strip().upper()
    table = PART_TYPES if ("PART" in head or role in ("part", "kit", "replacement")) else TYPES
    for pat, t in table:
        if re.search(pat, head):
            return t, head
    for pat, t in TYPES:  # a part catalogued under a whole-goods section
        if re.search(pat, head):
            return (t + " Part" if role in ("part", "kit", "replacement") else t), head
    return None


def main() -> int:
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    fams = {f: (n, cat, json.loads(feat or "[]"), desc or "") for f, n, cat, feat, desc in
            con.execute("SELECT id, name, category, features, description FROM families")}
    prods = {}
    for m, title, fid, role, band in con.execute("""SELECT p.mpn, p.title, pf.family_id, pf.role, pf.band FROM products p
            JOIN product_families pf ON pf.mpn = p.mpn WHERE p.status = 'active' ORDER BY pf.role = 'model' DESC, pf.pdf_page"""):
        prods.setdefault(m, {"title": title, "fams": [], "roles": set(), "bands": []})
        if fid and fid not in prods[m]["fams"]:
            prods[m]["fams"].append(fid)
        prods[m]["roles"].add(role)
        if band:
            prods[m]["bands"].append(band)
    specs = {}
    for m, a, v in con.execute("SELECT mpn, attr, value FROM specs"):
        specs.setdefault(m, {}).setdefault(a, []).append(v)
    rows = []

    def put(m, attr, value, basis, source):
        rows.append((m, attr, str(value), basis, source))

    for m, p in prods.items():
        S = specs.get(m, {})
        role = "model" if "model" in p["roles"] else sorted(p["roles"])[0]
        fam = fams.get(p["fams"][0]) if p["fams"] else None
        name, cat, feats, desc = fam if fam else ("", "", [], "")
        text = " ".join([p["title"], name, desc] + feats + p["bands"])
        low = text.lower()
        ct = category_type(cat, role)
        if ct:
            put(m, "product_type", ct[0], f"catalog section: {ct[1]}", "family category")
        put(m, "sold_as", {"model": "complete product", "kit": "kit", "accessory": "accessory", "part": "replacement part",
                           "replacement": "replacement part"}[role], f"listed as a {role}", "catalog listing")
        if re.search(r"\bcommercial\b", (cat or "").lower()):
            put(m, "installation", "commercial", "catalog section", "family category")
        elif re.search(r"aboveground|above ground", low):
            put(m, "installation", "aboveground", "named as aboveground", "title / family")
        elif re.search(r"\binground\b", (cat or "").lower() + " " + low):
            put(m, "installation", "inground", "catalog section or name says inground", "family category")
        if ct and ct[0] == "Pool Pump" and role == "model":
            st = S.get("speed_type", [None])[0]
            if st:
                put(m, "pump_speed", {"variable speed and flow": "variable speed and flow", "variable": "variable speed", "two": "two-speed", "single": "single-speed"}.get(st, st), f"speed type: {st}", "spec")
            elif "thp" in S or "wef" in S or re.search(r"variable speed", low):
                put(m, "pump_speed", "variable speed", "THP/WEF rated or named Variable Speed", "spec / title")
            elif re.search(r"two[- ]speed", low):
                put(m, "pump_speed", "two-speed", "named Two-Speed", "title")
            elif re.search(r"single[- ]speed", low):
                put(m, "pump_speed", "single-speed", "named Single-Speed", "title")
            put(m, "self_priming", "yes" if re.search(r"self[- ]priming", low) or "NSF" in S.get("certification", []) else "not stated",
                "NSF Standard 50 is for self-priming centrifugal pumps" if "NSF" in S.get("certification", []) else "text", "spec / feature")
        if role == "model":
            app = next((f for f in feats + [desc] if re.search(r"\bapp\b|pentair home|pentair pool app|pentair pro app", f, re.I)), None)
            put(m, "app_controlled", "yes" if app else "not stated", app or "no feature mentions an app", "feature bullet")
            ts = next((f for f in feats if re.search(r"touch ?screen|touchpad|keypad", f, re.I)), None)
            if ts:
                put(m, "touchscreen_or_keypad", "yes", ts, "feature bullet")
            opts = S.get("options", [])
            if opts:
                put(m, "factory_options", ", ".join(json.loads(o) if o.startswith("[") else [o] for o in opts for _ in [0])[0:1][0] if False else ", ".join(
                    x for o in opts for x in (json.loads(o) if o.startswith("[") else [o])), "ordering table", "spec")
            auto = next((f for f in feats if re.search(r"automation|intellicenter|easytouch|intellitouch|screenlogic", f, re.I)), None)
            if auto:
                put(m, "automation_compatible", "yes", auto, "feature bullet")
            if "Energy Star" in S.get("program", []):
                put(m, "energy_star", "yes", "Energy Star logo on the catalog page", "spec")
            if "TradeGrade" in S.get("program", []):
                put(m, "tradegrade", "yes", "TradeGrade logo on the catalog page", "spec")
            for c in S.get("certification", []):
                put(m, "certified", c, "certification mark on the catalog page", "spec")
            ph = S.get("phase", [None])[0]
            if ph:
                put(m, "electrical", f"{ph}-phase", f"phase {ph}", "spec")
            v = S.get("voltage", [None])[0]
            if v and re.fullmatch(r"\d+", v):
                put(m, "voltage_class", f"{v} V", f"voltage {v}", "spec")
            elif v and re.search(r"115|120", v) and re.search(r"208|230|240", v):
                put(m, "voltage_class", "dual voltage (115/230 V)", f"voltage {v}", "spec")
            elif v and re.search(r"208|230|240", v):
                put(m, "voltage_class", "230 V class", f"voltage {v}", "spec")
            if "wef" in S:
                put(m, "doe_rated", "yes", f"WEF {S['wef'][0]} printed", "spec")
            if "low_voltage" in S:
                put(m, "light_voltage", S["low_voltage"][0], "low-voltage column", "spec")
            if "lamp_type" in S:
                put(m, "lamp", S["lamp_type"][0], "lamp type column", "spec")
            if "fuel" in S:
                put(m, "fuel", S["fuel"][0], "fuel column", "spec")
            if "filter_type" in S:
                put(m, "filter_media", S["filter_type"][0], "filter type", "spec")
            for pt in S.get("pool_type", []):
                put(m, "for_pool_type", pt, "application column", "spec")
            for sf in S.get("surface", []):
                put(m, "for_surface", sf, "surface column", "spec")
            if any(re.search(r"\bsalt\b|saltwater", f, re.I) for f in feats + [desc]):
                put(m, "salt_compatible", "yes", next(f for f in feats + [desc] if re.search(r"\bsalt\b|saltwater", f, re.I)), "feature bullet")
            w = next((f for f in feats + [desc] if re.search(r"\bwarranty\b", f, re.I)), None)
            if w:
                put(m, "warranty_note", w, w, "feature bullet")
        else:
            col = S.get("color", [])
            if col:
                put(m, "color", col[0], "colour column or description", "spec")
            if "pack_qty" in S:
                put(m, "pack_quantity", S["pack_qty"][0], "printed count", "spec")
    con.executemany("INSERT INTO derived_specs VALUES (?,?,?,?,?)", rows)
    con.commit()
    n = con.execute("SELECT count(*), count(DISTINCT mpn) FROM derived_specs").fetchone()
    print(f"derived_specs: {n[0]} rows for {n[1]} SKUs;", dict(con.execute("SELECT attr, count(*) FROM derived_specs GROUP BY attr ORDER BY 2 DESC").fetchall()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
