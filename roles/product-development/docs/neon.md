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

## Phase-3 tables (product data, `scripts/d3_load.py`)

    CREATE TABLE mfr_catalog.families (id text PRIMARY KEY, name text NOT NULL, brand text, parent text,
      category text, description text, features jsonb NOT NULL, notes jsonb NOT NULL, parts_pages jsonb NOT NULL, pages jsonb NOT NULL);
    CREATE TABLE mfr_catalog.product_families (mpn text NOT NULL, family_id text, role text NOT NULL,
      band text, pdf_page integer NOT NULL);
    CREATE TABLE mfr_catalog.specs (mpn text NOT NULL, attr text NOT NULL, value text NOT NULL,
      value_num double precision, unit text, raw text, pdf_page integer NOT NULL);
    CREATE TABLE mfr_catalog.prices (mpn text NOT NULL, us_list numeric, can_list numeric, price_note text,
      pdf_page integer NOT NULL);
    CREATE TABLE mfr_catalog.fitment (part_mpn text NOT NULL, family_ids jsonb NOT NULL, models jsonb NOT NULL,
      mpns jsonb NOT NULL, item text, qty double precision, condition text, raw text, pdf_page integer NOT NULL);
    CREATE TABLE mfr_catalog.reference_tables (id integer PRIMARY KEY, kind text NOT NULL, family_ids jsonb NOT NULL, title text,
      columns jsonb, rows jsonb, summary text, pdf_page integer NOT NULL);
    CREATE TABLE mfr_catalog.data_issues (batch text NOT NULL, pdf_page integer, mpn text, question text NOT NULL);
    CREATE INDEX specs_mpn_idx ON mfr_catalog.specs (mpn);
    CREATE INDEX specs_attr_idx ON mfr_catalog.specs (attr, value_num);
    CREATE INDEX fitment_part_idx ON mfr_catalog.fitment (part_mpn);
    CREATE INDEX fitment_family_idx ON mfr_catalog.fitment USING gin (family_ids);
    CREATE INDEX product_families_idx ON mfr_catalog.product_families (family_id);

Load order: `consolidate.py`, then `d3_load.py`, then `load_neon.py`.
