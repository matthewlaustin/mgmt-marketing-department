"""Demo of a shop product page built from data/catalog.db: one pump page and its parts page.

  python3 scripts/pump_page_demo.py 013075   # writes reports/pump-demo/index.html and parts.html

Everything shown comes from the phase-3 tables (specs, families, model_parts, product_prices, reference
tables); the images are crops of the catalog pages the data came from.
"""

from __future__ import annotations

import base64
import html
import json
import re
import sqlite3
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/pump-demo"
SCRATCH = Path("/tmp/claude-0/-home-user-product-namer/28224544-019c-5471-b0e0-39374ec9eedf/scratchpad")
PRINTED = lambda pdf: pdf - 2  # PDF page -> printed catalog page

con = sqlite3.connect(ROOT / "data/catalog.db")
q = lambda s, *a: con.execute(s, a).fetchall()
e = html.escape


def money(v):
    return f"${v:,.2f}" if v is not None else ""


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def spec_map(mpn: str) -> OrderedDict:
    m = OrderedDict()
    for attr, value, unit, raw, pg in q("SELECT attr, value, unit, raw, pdf_page FROM specs WHERE mpn=? ORDER BY attr, pdf_page", mpn):
        try:
            v = json.loads(value)
        except ValueError:
            v = value
        m.setdefault(attr, []).append((v, unit, raw, pg))
    return m


def main(mpn: str) -> None:
    title, brand = q("SELECT title, brand FROM products WHERE mpn=?", mpn)[0]
    short = title.split(" - ", 1)[1]
    fam_id, page = q("SELECT family_id, pdf_page FROM product_families WHERE mpn=? AND role='model' LIMIT 1", mpn)[0]
    fam = q("SELECT name, category, description, features, notes, parts_pages FROM families WHERE id=?", fam_id)[0]
    fname, category, desc, features, notes, parts_pages = fam
    features, notes, parts_pages = json.loads(features), json.loads(notes), json.loads(parts_pages)
    S = spec_map(mpn)
    price = q("SELECT us_list, can_list, price_note FROM product_prices WHERE mpn=?", mpn)
    siblings = q("""SELECT p.mpn, p.title FROM product_families pf JOIN products p ON p.mpn=pf.mpn
                    WHERE pf.family_id=? AND pf.role='model' GROUP BY p.mpn ORDER BY p.mpn""", fam_id)
    sib = []
    for m, t in siblings:
        sm = spec_map(m)
        opts = sm.get("options", [([], None, "", 0)])[0][0]
        sib.append((m, sm.get("thp", [("", "", "", 0)])[0][0], sm.get("voltage", [("", "", "", 0)])[0][0],
                    ", ".join(opts) if isinstance(opts, list) else (opts or "none"), m == mpn))
    charts = q("""SELECT title, summary, pdf_page FROM reference_tables r, json_each(r.family_ids) j
                  WHERE j.value=? AND kind='chart' ORDER BY pdf_page""", fam_id)
    parts = q("""SELECT mp.part_mpn, mp.item, mp.qty, mp.condition, mp.pdf_page, p.title, pp.us_list, pp.can_list, pp.price_note,
                 (SELECT group_concat(DISTINCT value) FROM specs s WHERE s.mpn=mp.part_mpn AND s.attr='color')
                 FROM model_parts mp JOIN products p ON p.mpn=mp.part_mpn LEFT JOIN product_prices pp ON pp.mpn=mp.part_mpn
                 WHERE mp.model_mpn=? ORDER BY mp.pdf_page, CAST(mp.item AS INTEGER), mp.part_mpn""", mpn)
    key = re.sub(r"[®™].*", "", fname).split()[0].lower()  # "IntelliPro3"
    photos = q("""SELECT i.local_file, i.alt, i.role, i.url FROM image_links il JOIN images i ON i.id = il.image_id
                  WHERE il.family_id = ? AND i.role IN ('main', 'gallery') AND i.local_file IS NOT NULL
                    AND (i.label IS NULL OR i.label IN ('product', 'product_in_setting', 'detail')) AND coalesce(i.people, 0) = 0
                  GROUP BY i.id ORDER BY max(lower(il.page_url) LIKE ?) DESC, i.role = 'main' DESC, i.id""", fam_id, f"%{key}%")
    photos = [(f, (a if a and a.lower() not in ("true", "false", "image", "png") else short + " product image"), r, u) for f, a, r, u in photos]
    derived = q("SELECT attr, value, basis FROM derived_specs WHERE mpn = ? ORDER BY rowid", mpn)
    chart_imgs = q("""SELECT i.local_file, i.alt FROM image_links il JOIN images i ON i.id = il.image_id
                      WHERE il.family_id = ? AND i.role = 'chart' AND i.local_file IS NOT NULL GROUP BY i.id ORDER BY i.id""", fam_id)
    docs = q("""SELECT d.title, d.kind, d.lang, d.url FROM document_links dl JOIN documents d ON d.id = dl.document_id
                WHERE dl.family_id = ? AND d.kind <> 'form' GROUP BY d.id ORDER BY d.kind, d.lang, d.title""", fam_id)
    diagram_files = [f for (f,) in q("SELECT local_file FROM images WHERE role='diagram' AND url LIKE ? ORDER BY url", f"%/p{431:03d}/%")]
    thp = S["thp"][0][0]
    hp_tag = f"{float(thp):g} HP"  # the parts list splits rows by HP ("1.5 HP" / "3.0 HP")
    this_hp = {f"{float(thp):.1f} HP", f"{float(thp):g} HP"}

    # ---------- shared style ----------
    style = """
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@100,500;100,700;112,800&family=Source+Sans+3:wght@400;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Layout: a shop product page. Photo + buy box on top, spec table, then variants and accessories; parts on a second page. */
:root {
  --bg: #f6f8f7; --surface: #ffffff; --ink: #14201f; --muted: #5d6f6b; --line: #d6dedb; --soft: #e7eeec;
  --accent: #0d6e8a; --accent-ink: #ffffff; --accent-soft: #dcecf1; --mark: #b4531a; --mark-soft: #f7e6dc;
  --display: "Archivo", "Helvetica Neue", Arial, sans-serif; --body: "Source Sans 3", "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0f1716; --surface: #182221; --ink: #e8efed; --muted: #9fb2ad; --line: #2b3a37; --soft: #202d2b;
  --accent: #4fb3d1; --accent-ink: #0b1516; --accent-soft: #163640; --mark: #e8905a; --mark-soft: #3a2518; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #0f1716; --surface: #182221; --ink: #e8efed; --muted: #9fb2ad; --line: #2b3a37; --soft: #202d2b;
  --accent: #4fb3d1; --accent-ink: #0b1516; --accent-soft: #163640; --mark: #e8905a; --mark-soft: #3a2518; color-scheme: dark; }
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--ink); font-family: var(--body); font-size: 16px; line-height: 1.5; }
.wrap { max-width: 1040px; margin: 0 auto; padding-block: 20px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 28px; }
.crumbs { font-size: 13px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 6px; }
.crumbs a { color: var(--accent); text-decoration: none; } .crumbs a:hover { text-decoration: underline; }
.brandbar { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; border-bottom: 2px solid var(--ink); padding-bottom: 8px; }
.brandbar .logo { font-family: var(--display); font-weight: 800; font-stretch: 112%; font-size: 22px; letter-spacing: -.01em; }
.brandbar .demo { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }
h1 { font-family: var(--display); font-weight: 700; font-stretch: 100%; font-size: clamp(24px, 3.4vw, 34px); line-height: 1.12; margin: 0; text-wrap: balance; letter-spacing: -.01em; }
h2 { font-family: var(--display); font-weight: 700; font-size: 20px; margin: 0; text-wrap: balance; }
.sku { font-family: var(--mono); font-size: 14px; color: var(--muted); }
.hero { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 28px; align-items: start; }
@media (max-width: 720px) { .hero { grid-template-columns: 1fr; } }
.photo { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 12px; display: grid; gap: 8px; }
.photo img { width: 100%; height: auto; display: block; border-radius: 3px; }
.photo figcaption { font-size: 12px; color: var(--muted); }
.gallery { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; }
.gallery img { aspect-ratio: 1; object-fit: cover; border: 1px solid var(--line); border-radius: 3px; }
.doclist { display: grid; gap: 6px; }
.doclist a { color: var(--accent); text-decoration: none; } .doclist a:hover { text-decoration: underline; }
.doclist .k { font-size: 12px; color: var(--muted); }
.buy { display: grid; gap: 14px; }
.keyspecs { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.ks { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; display: grid; gap: 2px; min-width: 0; }
.ks b { font-family: var(--display); font-size: 22px; font-variant-numeric: tabular-nums; }
.ks span { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
.marks { display: flex; flex-wrap: wrap; gap: 6px; }
.glance { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 6px 14px; font-size: 14px; }
.glance div { display: grid; border-bottom: 1px solid var(--line); padding: 3px 0; }
.glance .gk { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
.charts figure { margin: 0; background: #fff; border: 1px solid var(--line); border-radius: 6px; padding: 8px; display: grid; gap: 6px; }
.charts img { width: 100%; height: auto; display: block; }
.charts figcaption { font-size: 12px; color: var(--muted); }
.chip { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px; background: var(--accent-soft); color: var(--ink); }
.chip.mark { background: var(--mark-soft); color: var(--mark); }
.price { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.price b { font-family: var(--display); font-size: 26px; }
.price span { color: var(--muted); font-size: 14px; }
.cta { display: flex; flex-wrap: wrap; gap: 10px; }
.btn { font: inherit; font-weight: 600; font-size: 15px; padding: 10px 18px; border-radius: 6px; border: 1px solid var(--accent); cursor: pointer; text-decoration: none; display: inline-block; }
.btn.primary { background: var(--accent); color: var(--accent-ink); }
.btn.secondary { background: var(--surface); color: var(--accent); }
.btn:focus-visible, a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.lede { margin: 0; color: var(--ink); max-width: 64ch; }
.features { margin: 0; padding-left: 18px; display: grid; gap: 4px; }
section.block { display: grid; gap: 12px; }
.tbl { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 15px; }
th { text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); font-weight: 600; padding: 8px 10px 6px 0; border-bottom: 1px solid var(--ink); }
td { padding: 8px 10px 8px 0; border-bottom: 1px solid var(--line); vertical-align: top; }
td.k { color: var(--muted); width: 34%; }
td.num, .mono { font-family: var(--mono); font-variant-numeric: tabular-nums; font-size: 14px; }
td.src { font-size: 12px; color: var(--muted); white-space: nowrap; }
tr.this td { background: var(--accent-soft); }
tr.other td { color: var(--muted); }
.note { font-size: 13px; color: var(--muted); margin: 0; max-width: 72ch; }
.footnotes { font-size: 12px; color: var(--muted); display: grid; gap: 6px; border-top: 1px solid var(--line); padding-top: 12px; }
.diagram { display: grid; gap: 8px; margin: 0; }
.diagram .sheet { background: #fff; border: 1px solid var(--line); border-radius: 6px; padding: 10px; overflow-x: auto; }
.diagram img { width: 100%; height: auto; display: block; }
@media (max-width: 600px) { .diagram img { min-width: 640px; } }
.controls { display: flex; flex-wrap: wrap; gap: 14px; align-items: center; font-size: 14px; }
.controls label { display: inline-flex; gap: 6px; align-items: center; cursor: pointer; }
.item { display: inline-block; min-width: 2.2em; text-align: center; font-family: var(--mono); font-size: 13px; background: var(--soft); border-radius: 4px; padding: 1px 6px; }
.cond { font-size: 12px; color: var(--mark); font-weight: 600; }
.colour { font-size: 12px; color: var(--muted); }
td.part a { color: var(--accent); text-decoration: none; font-family: var(--mono); font-size: 14px; }
.back { font-size: 14px; }
footer { font-size: 12px; color: var(--muted); border-top: 1px solid var(--line); padding-top: 12px; }
@media (max-width: 520px) { .keyspecs { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>"""

    def header(crumb_last: str) -> str:
        cat = " › ".join(c.strip() for c in category.split("›")) if category else ""
        return f"""
<div class="brandbar"><div class="logo">Pool Geek</div><div class="demo">product page demo · data from the Pentair catalog</div></div>
<nav class="crumbs" aria-label="Breadcrumb"><a href="index.html">Pumps</a><span>›</span><span>{e(fname)}</span><span>›</span><span>{e(crumb_last)}</span></nav>"""

    # ---------- pump page ----------
    def spec_row(label, key, fmt=None):
        if key not in S:
            return ""
        vals, raws, pages = [], [], set()
        for v, unit, raw, pg in S[key]:
            vals.append(fmt(v, unit) if fmt else (", ".join(map(str, v)) if isinstance(v, list) else f"{v}{' ' + unit if unit else ''}"))
            pages.add(pg)
        src = ", ".join(f"p{PRINTED(p)}" if p else "web" for p in sorted(pages))
        return f"<tr><td class=\"k\">{e(label)}</td><td>{e('; '.join(vals))}</td><td class=\"src\">catalog {src}</td></tr>"

    ports = S.get("port_size", [([], "in", "", 0)])[0][0]
    port_text = " or ".join(f"{p} in" for p in (ports if isinstance(ports, list) else [ports]))
    certs = [v for v, *_ in S.get("certification", [])]
    programs = [v for v, *_ in S.get("program", [])]
    key = [(f"{float(thp):g}", "THP"), (S["wef"][0][0] if "wef" in S else "", "WEF"), (S["voltage"][0][0] if "voltage" in S else "", "Volts")]
    price_html = (f"<b>{money(price[0][0])}</b><span>US list · {money(price[0][1])} CAN</span>" if price and price[0][0] is not None
                  else "<b>Call for price</b><span>the catalog prints no list price for this pump</span>")
    spec_rows = "".join([
        spec_row("Total horsepower (THP)", "thp", lambda v, u: f"{float(v):g} THP"),
        spec_row("Weighted energy factor (WEF)", "wef", lambda v, u: f"{v}"),
        spec_row("Speed type", "speed_type"),
        spec_row("Voltage", "voltage", lambda v, u: f"{v} V"),
        spec_row("Frequency", "frequency", lambda v, u: f"{v} Hz"),
        spec_row("Full-load amps", "amps", lambda v, u: f"{v} A"),
        f"<tr><td class=\"k\">Port size</td><td>{e(port_text)} ({e(S['connection_type'][0][0]) if 'connection_type' in S else ''})</td><td class=\"src\">catalog p{PRINTED(S['port_size'][0][3])}</td></tr>" if "port_size" in S else "",
        spec_row("Weight", "weight", lambda v, u: f"{float(v):g} lb"),
        f"<tr><td class=\"k\">Certifications</td><td>{e(', '.join(certs))}</td><td class=\"src\">catalog p{PRINTED(S['certification'][0][3])}</td></tr>" if certs else "",
        f"<tr><td class=\"k\">Programs</td><td>{e(', '.join(programs))}</td><td class=\"src\">catalog p{PRINTED(S['program'][0][3])}</td></tr>" if programs else "",
    ])
    sib_rows = "".join(
        f"<tr class=\"{'this' if cur else ''}\"><td class=\"part\"><a href=\"index.html\">{e(m)}</a></td><td>{e(f'{float(t):g} THP' if t else '')}</td><td>{e(str(v))} V</td><td>{e(o)}</td></tr>"
        for m, t, v, o, cur in sib)
    chart_html = "".join(f"<div><b>{e(t)}</b> <span class=\"src\">catalog p{PRINTED(pg)}</span><p class=\"note\">{e(s)}</p></div>" for t, s, pg in charts
                         if hp_tag.split()[0] in t or "HP" not in t)
    accessories = [r for r in parts if r[4] != 431]
    acc_rows = "".join(
        f"<tr><td class=\"part\"><a href=\"parts.html#{e(r[0])}\">{e(r[0])}</a></td><td>{e(r[5].split(' - ', 1)[1])}"
        + (f" <span class=\"cond\">{e(r[3])}</span>" if r[3] and 'HP' in r[3] and not any(h in r[3] for h in this_hp) else "")
        + f"</td><td class=\"num\">{money(r[6]) or (r[8] or 'call')}</td></tr>" for r in accessories)
    n_parts = len({r[0] for r in parts if r[4] == 431})
    index = f"""<title>{e(short)}</title>{style}
<div class="wrap">
{header(short)}
<div class="hero">
  <figure class="photo"><img src="{data_uri(ROOT / photos[0][0]) if photos else data_uri(SCRATCH / 'p212_photo.png')}" alt="{e(photos[0][1] or short) if photos else e(short)}">
    <figcaption>{"Pentair product photo, pentair.com" if photos else f"From the Pentair Pool Product Catalog 2025-2026, page {PRINTED(page)}"}</figcaption>
    {('<div class="gallery">' + ''.join(f'<img src="{data_uri(ROOT / f)}" alt="{e(a or r)}" loading="lazy">' for f, a, r, u in photos[1:5]) + '</div>') if len(photos) > 1 else ''}
  </figure>
  <div class="buy">
    <div><div class="sku">{e(brand)} · Part No. {e(mpn)}</div><h1>{e(short)}</h1></div>
    <div class="keyspecs">{''.join(f'<div class="ks"><b>{e(str(v))}</b><span>{e(l)}</span></div>' for v, l in key)}</div>
    <div class="glance">{''.join(f'<div><span class="gk">{e(a.replace("_", " "))}</span><b>{e(v)}</b></div>' for a, v, b in derived if a not in ('certified', 'sold_as', 'warranty_note') and v != 'not stated')}</div>
    <div class="marks">{''.join(f'<span class="chip">{e(c)}</span>' for c in certs)}{''.join(f'<span class="chip mark">{e(p)}</span>' for p in programs)}</div>
    <div class="price">{price_html}</div>
    <div class="cta"><a class="btn primary" href="parts.html">Parts diagram &amp; replacement parts ({n_parts})</a><a class="btn secondary" href="#specs">Full specifications</a></div>
    <p class="lede">{e(desc)}</p>
    <ul class="features">{''.join(f'<li>{e(f)}</li>' for f in features)}</ul>
  </div>
</div>

<section class="block" id="specs"><h2>Specifications</h2>
<div class="tbl"><table><thead><tr><th>Spec</th><th>Value</th><th>Source</th></tr></thead><tbody>{spec_rows}</tbody></table></div>
<p class="note">Port sizes are the pump's inlet x outlet; the 3 in. x 3 in. option is sold separately as a union kit (see parts). THP is total horsepower, the figure Pentair rates these pumps by.</p>
</section>

<section class="block"><h2>Performance and dimensions</h2>
<div class="charts">{''.join(f'<figure><img src="{data_uri(ROOT / f)}" alt="{e(a)}"><figcaption>{e(a)}</figcaption></figure>' for f, a in chart_imgs if (hp_tag.split()[0] in a or "HP" not in a))}</div>
<p class="note">Pentair's charts as printed in the catalog (page {PRINTED(213)}); the curves aren't tabulated, so read values from the chart.</p></section>

<section class="block"><h2>Manuals and documents</h2>
<div class="doclist">{''.join(f'<div><a href="{e(u)}" target="_blank" rel="noopener">{e(t)}</a> <span class="k">{e(k)} · {e(l)} · PDF</span></div>' for t, k, l, u in sorted(docs, key=lambda d: (d[1] not in ('brochure', 'data sheet'), d[1], d[2] != 'en', d[0]))) or '<p class="note">Pentair publishes no documents for this line.</p>'}</div>
<p class="note">Pentair's own PDFs, as published on pentair.com for this product line.</p></section>

<section class="block"><h2>Other versions of this pump</h2>
<div class="tbl"><table><thead><tr><th>Part No.</th><th>THP</th><th>Voltage</th><th>Factory options</th></tr></thead><tbody>{sib_rows}</tbody></table></div>
<p class="note">Same pump, with or without a relay board and a touchscreen from the factory. Both can also be added later (see accessories).</p></section>

<section class="block"><h2>Add-ons and accessories</h2>
<div class="tbl"><table><thead><tr><th>Part No.</th><th>Item</th><th>US list</th></tr></thead><tbody>{acc_rows}</tbody></table></div>
<p class="note">Listed by Pentair for this pump line on catalog page {PRINTED(213)}. Items marked for another horsepower don't fit this {hp_tag} pump.</p></section>

<div class="footnotes">{''.join(f'<div>{e(n)}</div>' for n in notes)}</div>
<footer>Source: Pentair Pool Product Catalog 2025-2026 (Dec 2025 digital edition), pages {PRINTED(page)}–{PRINTED(page) + 1} and {', '.join(str(PRINTED(p)) for p in parts_pages)}; stored in Neon, schema mfr_catalog.</footer>
</div>"""

    # ---------- parts page ----------
    plist = [r for r in parts if r[4] == 431]
    groups = OrderedDict()  # item -> rows
    for r in plist:
        groups.setdefault(r[1] or "–", []).append(r)
    part_rows = []
    for item, rows in groups.items():
        for r in rows:
            m, _, qty, cond, pg, t, us, can, note, colour = r
            conds = [c.strip() for c in (cond or "").split(";")]
            hp = next((c for c in conds if "HP" in c), "")
            fits_this = not hp or hp in this_hp
            col = next((c for c in conds if c.lower() in ("almond", "black")), "") or (colour if colour in ("almond", "black") else "")
            price_txt = money(us) if us is not None else (note or "call")
            cls = "" if fits_this else "other"
            part_rows.append(f"""<tr class="{cls}" data-hp="{e(hp)}" data-colour="{e(col.lower())}" id="{e(m)}">
<td><span class="item">{e(item)}</span></td><td class="part"><a href="#{e(m)}">{e(m)}</a></td>
<td>{e(t.split(' - ', 1)[1])}{' <span class="cond">' + e(hp) + '</span>' if hp else ''}{(' · <span class="colour">' + e(col) + '</span>') if col else ''}{(' · qty ' + f'{qty:g}') if qty else ''}</td>
<td class="num">{e(price_txt)}</td></tr>""")
    # parts.html is served as written (only index.html gets the publish skeleton), so it carries its own head
    parts_page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(short)} parts</title>{style}<style>html, body {{ margin: 0; }} img {{ max-width: 100%; }} [hidden] {{ display: none !important; }}</style></head><body>
<div class="wrap">
{header('Replacement parts')}
<div><a class="back" href="index.html">← Back to the pump</a></div>
<div><div class="sku">Replacement parts for {e(brand)} {e(mpn)}</div><h1>{e(short)}: parts diagram and parts list</h1></div>
<figure class="diagram">{''.join(f'<div class="sheet"><img src="{data_uri(ROOT / f)}" alt="Exploded parts diagram of the IntelliFlo3 and IntelliPro3 VSF pump with numbered items 1 to 36"></div>' for f in diagram_files)}<figcaption class="note">Pentair's exploded view, catalog page {PRINTED(431)}. Item numbers match the list below; on a phone, scroll the drawing sideways.</figcaption></figure>
<div class="controls">
  <label><input type="checkbox" id="only-this" checked> Only parts for this {e(hp_tag)} pump</label>
  <label>Colour <select id="colour"><option value="">both (almond and black)</option><option value="almond">almond</option><option value="black">black</option></select></label>
  <span class="note" id="count"></span>
</div>
<div class="tbl"><table id="parts"><thead><tr><th>Item</th><th>Part No.</th><th>Description</th><th>US list</th></tr></thead><tbody>{''.join(part_rows)}</tbody></table></div>
<p class="note">One parts list covers the IntelliFlo3 (almond) and IntelliPro3 (black) pumps at 1.5 HP and 3.0 HP. Rows marked with a horsepower fit that size only; rows with a colour are that colour's part number. Items with no number sit outside the diagram (seal kits, connectors). "call" means Pentair prints no list price.</p>
<footer>Source: Pentair Pool Product Catalog 2025-2026, page {PRINTED(431)} (replacement parts) and page {PRINTED(213)} (add-ons). Prices are Pentair US list prices as printed.</footer>
</div>
<script>
const only = document.getElementById("only-this"), colour = document.getElementById("colour"), rows = [...document.querySelectorAll("#parts tbody tr")];
const THIS = {json.dumps(sorted(this_hp))};
function apply() {{
  let n = 0;
  rows.forEach((r) => {{
    const hp = r.dataset.hp, c = r.dataset.colour;
    const ok = (!only.checked || !hp || THIS.includes(hp)) && (!colour.value || !c || c === colour.value);
    r.hidden = !ok; if (ok) n++;
  }});
  document.getElementById("count").textContent = n + " of " + rows.length + " rows shown";
}}
only.addEventListener("change", apply); colour.addEventListener("change", apply); apply();
if (location.hash) {{ const t = document.getElementById(location.hash.slice(1)); if (t) {{ t.hidden = false; t.scrollIntoView(); }} }}
</script></body></html>"""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(index)
    (OUT / "parts.html").write_text(parts_page)
    print(f"index {len(index) / 1e3:.0f} KB, parts {len(parts_page) / 1e3:.0f} KB, {len(plist)} part rows, {len(accessories)} accessories")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "013075")
