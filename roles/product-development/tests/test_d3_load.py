import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import d3_load  # noqa: E402


def test_load_merges_families_and_drops_inactive(tmp_path):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE products (mpn TEXT, status TEXT)")
    con.executemany("INSERT INTO products VALUES (?,?)", [("A1", "active"), ("P1", "active"), ("X1", "discontinued")])
    out = {
        "batch": "d001",
        "families": [{"id": "fam", "name": "Fam", "page": 10, "features": ["a"],
                      "links": [{"kind": "replacement_parts", "printed_page": 427}]},
                     {"id": "fam", "name": "Fam", "page": 11, "features": ["a", "b"]}],
        "products": [{"mpn": "A1", "page": 10, "family": "fam", "role": "model",
                      "specs": [{"attr": "thp", "value": 3, "unit": "hp", "raw": "3"},
                                {"attr": "port_size", "value": "2 x 2", "unit": "in", "raw": "2\" x 2\""}],
                      "prices": {"us_list": 10.5}},
                     {"mpn": "X1", "page": 10, "family": "fam", "role": "model", "specs": []}],
        "fitment": [{"part": "P1", "page": 11, "fits": {"family": ["fam", "fam2"]}, "item": 7, "qty": 2}],
        "references": [{"page": 11, "kind": "table", "title": "T", "columns": ["a"], "rows": [["1"]]}],
        "issues": [{"page": 10, "question": "?"}],
    }
    (tmp_path / "d001.json").write_text(json.dumps(out))
    counts = d3_load.load(con, tmp_path)
    assert counts["dropped_not_active"] == 1
    fam = con.execute("SELECT features, parts_pages, pages FROM families").fetchone()
    assert json.loads(fam[0]) == ["a", "b"] and json.loads(fam[1]) == [429] and json.loads(fam[2]) == [10, 11]
    assert con.execute("SELECT value, value_num FROM specs WHERE attr='thp'").fetchone() == ("3", 3.0)
    assert con.execute("SELECT value_num FROM specs WHERE attr='port_size'").fetchone() == (None,)
    assert con.execute("SELECT family_ids, item, qty FROM fitment").fetchone() == ('["fam", "fam2"]', "7", 2.0)
    assert counts["prices"] == 1 and counts["reference_tables"] == 1 and counts["data_issues"] == 1
