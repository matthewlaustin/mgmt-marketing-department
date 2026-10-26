"""Which product lines does each downloaded brochure / sell sheet / data sheet name?

  python3 scripts/doc_mentions.py     # writes data/work/pentair/web/doc_mentions.json {doc url: [family ids]}

A document names a line when the line's distinctive name (its brand-word-free key, e.g. "intellipro3 vsf",
"tagelus", "mastertemp 125") appears in the PDF's text. Family brochures therefore attach to every line
they actually describe, with the PDF text as evidence.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from web_media_fetch import doc_path  # noqa: E402

BRAND = {"pentair", "sta", "rite", "sta-rite", "pleatco", "kreepy", "krauly", "paramount"}
GENERIC = BRAND | {"pool", "pools", "pump", "pumps", "filter", "filters", "heater", "heaters", "heat", "light", "lights", "led", "variable",
                   "speed", "and", "with", "system", "systems", "series", "replacement", "parts", "the", "for", "inground", "aboveground",
                   "top", "side", "mount", "high", "performance", "cartridge", "cartridges", "sand", "de", "d", "e", "commercial",
                   "residential", "white", "color", "spa", "flow", "pressure", "suction", "robotic", "cleaner", "cleaners", "in", "of",
                   "kit", "kits", "accessories", "components", "tools", "valve", "valves", "water", "models", "model", "complete", "plus",
                   "ii", "iii", "iv", "hp", "to", "a", "b", "c", "s", "x", "universal", "internals", "retro", "fit", "heads", "head",
                   "full", "half", "sets", "grids", "grid", "drain", "drains", "skimmer", "skimmers", "lid", "lids", "lighting", "features",
                   "effects", "control", "controller", "controllers", "app", "apps", "pro", "effect", "feeder", "feeders", "poolside"}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower().replace("®", "").replace("™", "")).strip()


def key_of(name: str) -> str | None:
    """The trademarked part of a family name plus its model token: "IntelliPro3® VSF" -> "intellipro3 vsf",
    "MasterTemp® 125" -> "mastertemp 125", "Tagelus®" -> "tagelus". Names without a mark get no key."""
    m = re.search(r"([A-Za-z][A-Za-z0-9'\-]{3,})\s*[®™]\s*([A-Z0-9][A-Z0-9\-]{0,5}\b)?", name)
    if not m:
        return None
    key = norm(m.group(1))
    if key in GENERIC:  # "C Series®", "Pool Pump®": no distinctive name to search for
        return None
    if m.group(2) and norm(m.group(2)) not in GENERIC:
        key += " " + norm(m.group(2))
    return key or None


def main() -> int:
    con = sqlite3.connect(ROOT / "data/catalog.db")
    keys = {f: k for f, n in con.execute("SELECT id, name FROM families") if (k := key_of(n))}
    pages = json.loads((ROOT / "data/work/pentair/web/media.json").read_text())
    docs = {d["url"]: d for p in pages for d in p["documents"]
            if d["kind"] in ("brochure", "data sheet", "quick start") and d["url"].startswith("https://www.pentair.com/")}
    out, n = {}, 0
    for url in docs:
        f = doc_path(url)
        if not f.exists():
            continue
        try:
            with pdfplumber.open(f) as pdf:
                text = norm(" ".join((pg.extract_text() or "") for pg in pdf.pages[:12]))
        except Exception:
            continue
        n += 1
        hit = sorted(fid for fid, k in keys.items() if re.search(r"\b" + re.escape(k) + r"\b", text))
        if hit:
            out[url] = hit
    (ROOT / "data/work/pentair/web/doc_mentions.json").write_text(json.dumps(out, indent=1))
    print(f"{n} documents read; {len(out)} name at least one product line; keys for {len(keys)} families")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
