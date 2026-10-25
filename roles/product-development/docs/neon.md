# Neon copy of the catalog

The catalog database (`data/catalog.db`) is mirrored to Neon, project **Pool Geek® Products**
(`nameless-heart-80832994`), database `neondb`, in its own schema **`mfr_catalog`**. Nothing
outside that schema is touched, and drizzle (which manages `public`) doesn't know about it.

| table | rows | what |
|---|---|---|
| `mfr_catalog.products` | one per active SKU | brand, title, kind, product line, source page, `needs_review` + `review_notes` |
| `mfr_catalog.evidence` | one per printed row | every catalog/pentair.com row each SKU was read from |
| `mfr_catalog.conflicts` | one per disagreement | pages that disagree on a SKU's title or brand (`values_by_page` jsonb) |
| `mfr_catalog.excluded_mpns` | one per left-out number | discontinued, not for USA, or not sold separately |

## Reload after a change

    python3 scripts/consolidate.py
    NEON_URL='<connection string>' python3 scripts/load_neon.py

`load_neon.py` replaces the four tables' contents in one transaction over Neon's HTTPS SQL
endpoint. Get the connection string from the Neon console (never commit it).

## Schema (created once)

    CREATE SCHEMA mfr_catalog;
    CREATE TABLE mfr_catalog.products (mpn text PRIMARY KEY, brand text NOT NULL, title text NOT NULL,
      kind text NOT NULL, status text NOT NULL, replaced_by text, product_line text, parent_product text,
      fits text, title_pdf_page integer NOT NULL, pages text NOT NULL, needs_review boolean NOT NULL,
      review_notes text, source text NOT NULL);
    CREATE TABLE mfr_catalog.evidence (mpn text NOT NULL REFERENCES mfr_catalog.products(mpn) ON DELETE CASCADE,
      pdf_page integer NOT NULL, printed_page text, page_type text, brand text, title text, kind text,
      status text, source_row text, context text, confidence text, notes text);
    CREATE INDEX evidence_mpn_idx ON mfr_catalog.evidence (mpn);
    CREATE TABLE mfr_catalog.conflicts (mpn text NOT NULL REFERENCES mfr_catalog.products(mpn) ON DELETE CASCADE,
      field text NOT NULL, values_by_page jsonb NOT NULL);
    CREATE TABLE mfr_catalog.excluded_mpns (mpn text PRIMARY KEY, status text NOT NULL);
