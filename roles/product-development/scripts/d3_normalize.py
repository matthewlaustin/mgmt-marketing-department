"""Make phase-3 spec values comparable (used by d3_load.py).

Only spellings change; `raw` keeps what Pentair printed. Rules:
- categorical values are lower-cased and mapped through small synonym tables (grey -> gray, 18-8 s/s ->
  stainless steel 18-8, NSF/ANSI Standard 50 -> NSF/ANSI 50); obvious catalog misspellings are
  corrected (Bunan -> buna-n), as the title rules allow
- a value that lists several things (certifications, surfaces, pool types) becomes one row per thing
- sizes keep their text but get a number (value_num) so they can be filtered
- units come from the attribute list when the extractor left them out
"""

from __future__ import annotations

import json
import re

ACRONYMS = {"npt", "fpt", "mpt", "fipt", "mip", "ansi", "abs", "pvc", "cpvc", "epdm", "ss", "uv", "sch", "ppo", "od", "id"}

COLOR = {"grey": "gray", "dark grey": "dark gray", "light grey": "light gray", "white incandescent": "white",
         "blk": "black", "wht": "white", "all gray": "gray"}
MATERIAL = {"ss": "stainless steel", "stainless": "stainless steel", "s/s": "stainless steel", "stl.": "steel",
            "18-8": "stainless steel 18-8", "18-8 s/s": "stainless steel 18-8", "18-8 ss": "stainless steel 18-8",
            "ss 18-8": "stainless steel 18-8", "18-8 stainless steel": "stainless steel 18-8",
            "300 s/s": "stainless steel 300", "ss 316": "stainless steel 316", "stainless steel 304": "stainless steel 304",
            "abs plastic": "abs", "abs thermoplastic": "abs", "bunan": "buna-n", "buna": "buna-n", "buna n 70sh": "buna-n 70",
            "buna-n 70 shore a": "buna-n 70", "buna 70 shore": "buna-n 70", "bunan 70": "buna-n 70", "edpm": "epdm",
            "mitrile": "nitrile", "kratom": "x", "thermoplastic pvc": "pvc (thermoplastic)", "epoxy coated": "epoxy coated cast iron",
            "fiberglass-reinforced": "fiberglass-reinforced polypropylene", "fiberglass reinforced polypropylene tank": "fiberglass-reinforced polypropylene",
            "fiberglass-reinforced polypropylene tank": "fiberglass-reinforced polypropylene", "plated brass": "brass, plated",
            "chrome brass": "brass, chrome", "silicon brass": "silicon bronze"}
SURFACE = {"vinyl liner": "vinyl", "concrete-walled vinyl liner": "vinyl", "gunite/concrete": ["gunite", "concrete"], "plaster": "plaster"}
POOL_TYPE = {"pool and spa": ["pool", "spa"], "pool only": "pool", "inground hot tub": "spa"}
CERT = {"nsf/ansi standard 50": "NSF/ANSI 50", "nsf 50": "NSF/ANSI 50", "nsf": "NSF", "ul": "UL", "csa": "CSA", "etl": "ETL",
        "ahri": "AHRI", "csa c22.2 no. 89": "CSA C22.2 No. 89", "ul 676": "UL 676", "ul 1563/csa c22.2 no. 218-1": "UL 1563/CSA C22.2 No. 218-1",
        "csa/ansi z21.56:19/csa 4.7:19": "CSA/ANSI Z21.56:19 / CSA 4.7:19", "scaqmd rule 1146.2 low nox": "SCAQMD Rule 1146.2 low NOx",
        "ansi/apsp/icc-16 2017; virginia graeme baker pool and spa safety act": "ANSI/APSP/ICC-16 2017 (VGB)"}
PROGRAM = {"energy star": "Energy Star", "tradegrade": "TradeGrade", "tradecertified": "TradeCertified",
           "appliance efficiency database": "Appliance Efficiency Database"}
CONNECTION = {"fipt": "FPT", "mip": "MPT", "pipe thread": "threaded", "npt (threaded)": "NPT", "flanged": "flange",
              "threaded union": "union", "clamp style": "clamp", "slip x slip": "slip"}
SPEED = {"variable speed": "variable", "two-speed": "two", "single-speed": "single"}

# x_ keys promoted to the controlled list (documented in docs/data-v3-attributes.md), or folded into one
PROMOTE = {"x_curve_key": "curve_key", "x_enclosure_rating": "enclosure_rating", "x_motor_class": "motor_class",
           "x_tank_length": "tank_length", "x_total_media": "total_media", "x_open_area": "open_area",
           "x_max_salinity_ppm": "max_salinity", "x_lid_color": "lid_color", "x_body_color": "body_color",
           "x_item_type": "item_type", "x_shape": "shape", "x_packaging": "packaging", "x_epa_number": "epa_number",
           "x_sign_text": "sign_text", "x_doe_dedicated_purpose_pool_pump": "doe_dedicated_purpose_pool_pump",
           "x_heat_exchanger": "heat_exchanger_material", "x_heat_exchanger_efficiency": "heat_exchanger_efficiency",
           "x_strainer": "strainer", "x_pump_system": "pump_system", "x_refrigerant": "refrigerant",
           "x_breaker_size": "breaker_size", "x_light_count": "light_count", "x_number_of_lights": "light_count",
           "x_outside_diameter": "x_outer_diameter", "x_unit_weight": "weight", "x_rated_power": "x_motor_kw",
           "x_dim_a": "dim_a", "x_dim_b": "dim_b", "x_dim_c": "dim_c", "x_dim_d": "dim_d", "x_dim_e": "dim_e",
           "x_fitting_type": "fitting_type", "x_valve_type": "valve_type", "x_installation": "installation",
           "x_lug_variant_of": "variant_of", "x_with_lug_item": "variant_with_lug", "x_upgrade_for_rows": "upgrade_for",
           "x_filter_models": "fits_filter_models", "x_protecta": "protecta", "x_ref_no": "ref_no",
           "x_brightness_levels": "brightness_levels", "x_hole_pattern": "hole_pattern", "x_flange_size": "flange_size",
           "x_vessel_dimensions": "vessel_dimensions", "x_power_enclosure_dimensions": "enclosure_dimensions",
           "x_lens_diameter": "lens_diameter", "x_style": "style", "x_top_style": "top_style", "x_depth": "depth",
           "x_function": "function", "x_resistance": "resistance", "x_ports": "ports", "x_tank_style": "tank_style",
           "x_flow_rate_floor": "flow_rate_floor", "x_flow_rate_wall": "flow_rate_wall"}
DROP = {"x_unlabeled_number", "x_w", "x_media_area"}  # unexplained digits; "Optimized" is a marketing word
RATED_FLOW = re.compile(r"x_flow_(\d+)_gpm_sf")
UV_FLOW = re.compile(r"x_flow_(\d+)mj")
FRACTION = re.compile(r"(\d+)(?:[-\s](\d+)/(\d+)|/(\d+))?(?:\.(\d+))?")


def _num(s: str) -> float | None:
    """'2-1/2' -> 2.5, '1.5' -> 1.5, '3/8' -> 0.375, '2' -> 2."""
    m = re.fullmatch(r"(\d+)-(\d+)/(\d+)", s) or re.fullmatch(r"(\d+) (\d+)/(\d+)", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) / int(m.group(3))
    m = re.fullmatch(r"(\d+)/(\d+)", s)
    if m:
        return int(m.group(1)) / int(m.group(2))
    m = re.fullmatch(r"\d+(?:\.\d+)?", s)
    return float(s) if m else None


def sizes_in(text: str) -> list[float]:
    """Every inch size printed in a text, as numbers."""
    t = re.sub(r"[\"”“]|in\.?|inch(es)?", " ", text)
    out = []
    for m in re.finditer(r"\d+-\d+/\d+|\d+ \d+/\d+|\d+/\d+|\d+(?:\.\d+)?", t):
        n = _num(m.group(0))
        if n is not None:
            out.append(n)
    return out


def _items(v) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            j = json.loads(v)
            if isinstance(j, list):
                return j
        except ValueError:
            pass
    return [v]


def _case(s: str) -> str:
    s = s.strip().lower()
    return " ".join(w.upper() if w in ACRONYMS else w for w in s.split())


def _split(s: str) -> list[str]:
    return [p.strip() for p in re.split(r",|;|\s+and\s+|\s*/\s*(?=[a-z])", s) if p.strip()]


def normalize(s: dict) -> list[dict]:
    """One extracted spec -> zero or more normalized specs."""
    attr, v = s.get("attr", ""), s.get("value")
    if attr in DROP:
        return []
    m = RATED_FLOW.fullmatch(attr)
    if m:  # filter flow at a filtration rate, like turnover_capacity
        n = _num(str(v).replace(",", ""))
        return [dict(s, attr="rated_flow", value={"gpm_per_sqft": int(m.group(1)), "gpm": n if n is not None else v}, unit="gpm")]
    m = UV_FLOW.fullmatch(attr)
    if m:
        n = _num(str(v).replace(",", ""))
        return [dict(s, attr="uv_rated_flow", value={"mj_per_cm2": int(m.group(1)), "gpm": n if n is not None else v}, unit="gpm")]
    if attr == "x_motor_kw" or (attr == "x_rated_power" and _num(str(v)) is not None):
        return [dict(s, attr="watts", value=_num(str(v)) * 1000, unit="W")]
    attr = PROMOTE.get(attr, attr)
    if attr in ("color", "lid_color", "body_color") and isinstance(v, str):
        c = v.strip().lower()
        return [dict(s, attr=attr, value=COLOR.get(c, c))]
    if attr == "material":
        out = []
        for x in _items(v):
            c = str(x).strip().lower()
            c = MATERIAL.get(c, c)
            if c != "x":
                out.append(dict(s, attr=attr, value=_case(c)))
        return out
    if attr == "surface":
        out = []
        for x in _items(v):
            for part in _split(str(x).lower()):
                mapped = SURFACE.get(part, part)
                out += [dict(s, attr=attr, value=p) for p in (mapped if isinstance(mapped, list) else [mapped])]
        return out
    if attr == "pool_type":
        out = []
        for x in _items(v):
            c = str(x).strip()
            if len(c) > 24 or c.lower() in ("bromine", "solar"):  # a sentence copied into the wrong column
                out.append(dict(s, attr="x_use", value=c))
                continue
            for part in _split(c.lower()):
                mapped = POOL_TYPE.get(part, part)
                out += [dict(s, attr=attr, value=p) for p in (mapped if isinstance(mapped, list) else [mapped])]
        return out
    if attr == "certification":
        out = []
        for x in _items(v):
            for part in re.split(r",\s*(?![^()]*\))", str(x)):
                p = part.strip()
                if p:
                    out.append(dict(s, attr=attr, value=CERT.get(p.lower(), p)))
        return out
    if attr == "program":
        return [dict(s, attr=attr, value=PROGRAM.get(p.strip().lower(), p.strip())) for x in _items(v) for p in str(x).split(",") if p.strip()]
    if attr == "connection_type":
        return [dict(s, attr=attr, value=_case(CONNECTION.get(str(x).strip().lower(), str(x)))) for x in _items(v)]
    if attr == "speed_type" and isinstance(v, str):
        c = v.strip().lower()
        return [dict(s, attr=attr, value=SPEED.get(c, c))]
    if attr in ("filter_type", "fuel", "lamp_type", "motor_enclosure", "efficiency_class", "mount", "media_type") and isinstance(v, str):
        return [dict(s, attr=attr, value=_case(v) if attr != "filter_type" else v.strip().lower().replace("d.e.", "D.E."))]
    if attr == "voltage" and isinstance(v, str):
        c = re.sub(r"(?<=\d)\s*v(ac)?\b", "", v.strip(), flags=re.I).replace(" to ", "/").replace(" or ", "/")
        return [dict(s, attr=attr, value=c, unit="V")]
    if attr == "amps" and isinstance(v, str):
        return [dict(s, attr=attr, value=v.replace("–", "-").replace(" amps", "").strip(), unit="A")]
    if attr == "port_size":
        parts = []
        for x in _items(v):
            t = str(x).replace("(optional)", "").replace("”", '"')
            for alt in re.split(r"\s+or\s+|,", t):
                ns = sizes_in(alt)
                if ns:
                    parts.append(" x ".join(f"{n:g}" for n in ns))
        if parts:
            return [dict(s, attr=attr, value=parts if len(parts) > 1 else parts[0], unit="in", value_num=sizes_in(parts[0])[0])]
        return [dict(s, attr=attr, value=v)]
    if attr in ("size", "pipe_size", "thread_size", "top_hole", "bottom_hole") and isinstance(v, str):
        ns = sizes_in(v) if attr != "thread_size" else []
        return [dict(s, attr=attr, value=v.strip(), value_num=ns[0] if ns else None)]
    return [dict(s, attr=attr)]


def canonical_key(mpn: str, s: dict) -> tuple:
    """Two rows that say the same thing after normalization are one row."""
    return (mpn, s["attr"], json.dumps(s["value"], sort_keys=True) if not isinstance(s["value"], str) else s["value"].lower())
