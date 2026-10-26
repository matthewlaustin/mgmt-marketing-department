# Manufacturer SKU Catalog: Plan

Goal: for each brand Pool Geek carries, build a complete list of the brand's **SKUs, each with a
title Pool Geek can use**, taken **only from manufacturer data** (the brand's own website, its
PDF catalogs, price lists and spec sheets). Retailer and distributor sites are out of scope.

## Phases

### 0. Workspace (done in this commit, except the network setting)
- `.claude/settings.json`: allow rules so routine commands run without prompts.
- `.claude/hooks/session-start.sh`: installs dependencies in every new cloud container.
- `CLAUDE.md`: the operating rules a session follows when working unattended.
- **Blocked, needs Matthew:** the environment's network policy blocks manufacturer sites
  (hayward.com, pentair.com, jandy.com all refused). See "What I need from you".

### 1. Collector toolkit (`product_namer/`)
One command per brand: `product-namer collect --brand Hayward --website hayward.com`.
Sources, tried in order of reliability, each record tagged with where it came from:
1. **Store APIs**: Shopify `/products.json`, WooCommerce Store API (some brands sell direct).
2. **Sitemaps + product pages**: robots.txt and sitemap discovery, then each product page's
   JSON-LD / microdata (`sku`, `mpn`, `name`, variants), then labelled text
   ("Part #", "Model #", "SKU", spec tables).
3. **JavaScript-rendered sites**: Playwright (already installed) for catalogs that only appear
   after scripts run.
4. **PDFs**: find catalogs, price lists and spec sheets linked from the site; extract part-number
   tables with `pdfplumber` / `pdftotext`. Price lists are usually the most complete SKU source.
5. **Reading pages myself** when markup is irregular: I read samples of a site, then write a
   per-brand adapter (`product_namer/brands/<brand>.py`) so the rest of the site runs mechanically.

Polite crawling: obey robots.txt, about 1 request/second, retries with backoff, cache raw
downloads so a re-run doesn't hit the site again.

### 2. Database
SQLite file (`data/catalog.db`) committed to the repo, plus a CSV export per brand
(`data/exports/<brand>.csv`) so changes show up as readable diffs on GitHub.
- `products`: brand, sku, manufacturer_title, **pg_title**, mpn, gtin/UPC, category, url,
  first_seen, last_seen, status (active / discontinued).
- `evidence`: every place a SKU was seen (URL or PDF + page) and the raw text: proof for audits.
- `runs`: what was crawled, when, counts, errors.
Because the container is wiped when idle, I commit and push after every brand, and at least
every ~30 minutes during a long crawl.

### 3. Titles that work for us
Manufacturer titles are inconsistent ("SP2610X15 Super Pump 1.5HP"). I keep the raw title and
generate a normalized `pg_title` from a written convention, e.g.
`{Brand} {Product Line} {Key spec(s)} {Product type}` → "Hayward Super Pump 1.5 HP Pool Pump".
The convention lives in `docs/title-rules.md` once you approve it; every title is checked
against it (length limit, no SKU inside the title, units consistent, brand first).

### 4. Quality checks, run on every brand
- SKU format consistent within the brand; flag outliers.
- Duplicates and near-duplicates (`SP2610X15` vs `SP-2610X15`) merged into one record.
- Coverage: compare counts against the brand's price list / sitemap; record the gaps.
- A short report per brand: `reports/<brand>.md` with counts, sources, anything unsure.

### 5. Working unattended
- Work through a queue (`data/brands.csv`: brand, website, priority, status).
- Each brand: probe the site → pick strategies → collect → build titles → QA → commit/push →
  next brand. Problems that need a human (login walls, bot blocks, unclear titles) go into
  `reports/needs-attention.md` instead of stopping the whole run.
- Long jobs run in the background; I schedule check-ins on myself so work continues across
  hours without you prompting.

## What I need from you
1. **Network access (blocking).** Environment settings → Network access: choose full access, or
   Limited with each manufacturer domain added under Allowed domains (keep "Allow package
   managers" ticked). Full access is simpler since PDFs often live on CDNs (e.g. `*.cloudfront.net`).
   Steps: https://code.claude.com/docs/en/cloud-environments#network-access
2. **Permission mode: Auto** (dropdown next to the prompt box) so commands run without asking.
3. **The brand list**: names + websites, in priority order.
4. **Title convention**: 3–5 titles you like from your current store, so I can write the rules.
5. **Database choice**: SQLite in this repo (default), or a Neon Postgres database
   (you have Neon connected; I'd create a project only with your OK).
