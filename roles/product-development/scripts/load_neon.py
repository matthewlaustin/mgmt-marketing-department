"""Load data/catalog.db into the Neon schema mfr_catalog (Pool Geek® Products project).

  NEON_URL=postgresql://... python3 scripts/load_neon.py

Uses Neon's HTTPS SQL endpoint (plain Postgres ports are blocked in the cloud sandbox). Replaces
the contents of mfr_catalog.products, evidence, conflicts and excluded_mpns in one transaction;
nothing outside the mfr_catalog schema is touched. The schema itself is created once by hand
(see the CREATE statements in docs/neon.md).
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/catalog.db"
EXCLUDED = ROOT / "data/work/pentair/excluded_mpns.json"
BATCH = 1000


def post(url: str, body: dict) -> dict:
    host = urlparse(url).hostname
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(body, f)
    try:
        out = subprocess.run(
            ["curl", "-sS", "-m", "300", "-X", "POST", f"https://{host}/sql",
             "-H", f"Neon-Connection-String: {url}", "-H", "Neon-Batch-Isolation-Level: Serializable",
             "-H", "Content-Type: application/json", "--data-binary", f"@{f.name}"],
            check=True, capture_output=True, text=True).stdout
    finally:
        os.unlink(f.name)
    res = json.loads(out)
    if "message" in res and "results" not in res and "rows" not in res:
        raise SystemExit(f"Neon error: {res['message']}")
    return res


def rows(con: sqlite3.Connection, table: str) -> list[dict]:
    cur = con.execute(f"SELECT * FROM {table}")
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur]


def main() -> int:
    url = os.environ.get("NEON_URL")
    if not url:
        print("set NEON_URL to the Pool Geek® Products connection string", file=sys.stderr)
        return 1
    con = sqlite3.connect(DB)
    products = rows(con, "products")
    for p in products:
        p["needs_review"] = bool(p["needs_review"])
    evidence = rows(con, "evidence")
    conflicts = [dict(c, values_by_page=json.loads(c["values_by_page"])) for c in rows(con, "conflicts")]
    excluded = [{"mpn": m, "status": s} for m, s in json.loads(EXCLUDED.read_text()).items()]

    queries = [{"query": "DELETE FROM mfr_catalog.conflicts"}, {"query": "DELETE FROM mfr_catalog.evidence"},
               {"query": "DELETE FROM mfr_catalog.products"}, {"query": "DELETE FROM mfr_catalog.excluded_mpns"}]
    for table, data in (("products", products), ("evidence", evidence), ("conflicts", conflicts),
                        ("excluded_mpns", excluded)):
        for i in range(0, len(data), BATCH):
            queries.append({"query": f"INSERT INTO mfr_catalog.{table} SELECT * FROM "
                                     f"json_populate_recordset(null::mfr_catalog.{table}, $1::json)",
                            "params": [json.dumps(data[i:i + BATCH], ensure_ascii=False)]})
    post(url, {"queries": queries})
    counts = post(url, {"query": "SELECT (SELECT count(*) FROM mfr_catalog.products) p, "
                                 "(SELECT count(*) FROM mfr_catalog.evidence) e, "
                                 "(SELECT count(*) FROM mfr_catalog.conflicts) c, "
                                 "(SELECT count(*) FROM mfr_catalog.excluded_mpns) x", "params": []})["rows"][0]
    print(f"loaded: products {counts['p']}, evidence {counts['e']}, conflicts {counts['c']}, excluded {counts['x']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
