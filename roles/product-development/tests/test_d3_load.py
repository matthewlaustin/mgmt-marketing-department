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


def test_normalize_spec():
    t = d3_load.normalize_spec({"attr": "x_turnover_capacity_8h", "value": "21,000", "raw": "21,000"})
    assert t["attr"] == "turnover_capacity" and t["value"] == {"hours": 8, "gallons": 21000}
    assert d3_load.normalize_spec({"attr": "x_turnover_gal_12h", "value": 30000})["value"]["hours"] == 12
    assert d3_load.normalize_spec({"attr": "x_backwash_valve_size", "value": 2})["attr"] == "backwash_valve_size"
    assert d3_load.normalize_spec({"attr": "x_description", "value": "x"}) is None
    assert d3_load.normalize_spec({"attr": "x_curve_key", "value": "A"})["attr"] == "x_curve_key"


def test_current_price():
    one = d3_load.current_price([(10.0, 12.0, "", 300)])
    assert one[:2] == (10.0, 12.0) and one[3] == "single price"
    common = d3_load.current_price([(53.69, 64.51, "", 307), (15.72, 18.89, "", 309), (15.72, 18.89, "", 311)])
    assert common[:2] == (15.72, 18.89) and common[3].startswith("most common")
    tie = d3_load.current_price([(1.0, 1.2, "", 300), (2.0, 2.4, "", 400)])
    assert tie[:2] == (2.0, 2.4) and tie[3].startswith("tie")
    assert d3_load.current_price([(None, None, "CALL", 5)])[2] == "CALL"
