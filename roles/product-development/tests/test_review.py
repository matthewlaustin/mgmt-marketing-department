from product_namer.review import is_candidate, page_tokens, validate

WORDS = "Product Description 263056 3-Way CPVC 2.5 in. (3 in. slip outside) 263059 270119Z P/N 200174.A 28W 120V C-7469 PH6".split()


def record(mpn, title, **kw):
    return {"mpn": mpn, "brand": "Pentair", "title": title, "kind": "whole_good", "status": "active", **kw}


def ok_review():
    return {
        "records": [
            record("263056", "Pentair 263056 - FullFloXF® 3-Way CPVC 2.5 in Diverter"),
            record("263059", "Pentair 263059 - FullFloXF® 2-Way CPVC 2.5 in Diverter"),
            record("270119Z", "Pentair 270119Z - FullFloXF® Check Valve Rebuild Kit", kind="part"),
        ],
        "dismissed": [
            {"token": "200174.A", "reason": "document_code"},
            {"token": "C-7469", "reason": "cross_reference"},
            {"token": "PH6", "reason": "other", "note": "test"},
        ],
    }


def test_candidates():
    assert is_candidate("263056")
    assert is_candidate("270119Z")
    assert is_candidate("PH6")
    assert is_candidate("C-7469")
    for not_sku in ["28W", "120V", "2.5", "2003-2012", "198", "52.15", "3-Way"]:
        assert not is_candidate(not_sku), not_sku


def test_valid_review_passes():
    assert validate(ok_review(), WORDS) == []


def test_invented_mpn_rejected():
    review = ok_review()
    review["records"].append(record("263057", "Pentair 263057 - FullFloXF® Thing"))
    assert any("not found verbatim" in e for e in validate(review, WORDS))


def test_missed_token_reported():
    review = ok_review()
    review["records"].pop(1)
    assert any("unaccounted" in e and "263059" in e for e in validate(review, WORDS))


def test_title_cleanup_enforced():
    review = ok_review()
    review["records"][0]["title"] = "Pentair 263056 - FullFloXF® 3-Way CPVC 2.5 in. (3 in. slip outside) Diverter"
    errors = validate(review, WORDS)
    assert any("parenthesis" in e for e in errors)
    assert any("unit with period" in e for e in errors)


def test_title_prefix_enforced():
    review = ok_review()
    review["records"][0]["title"] = "FullFloXF® 3-Way CPVC 2.5 in Diverter"
    assert any("must start with" in e for e in validate(review, WORDS))


def test_page_tokens_strip_footnote_marks():
    _, cands = page_tokens(["PCC60*", "ULTRA-A4", "602186,"])
    assert {"PCC60", "ULTRA-A4", "602186"} <= cands


def test_all_caps_family_rejected():
    review = ok_review()
    review["records"][0]["title"] = "Pentair 263056 - FULLFLOXF® 3-Way CPVC 2.5 in Diverter"
    assert any("all caps" in e for e in validate(review, WORDS))


def test_duplicate_titles_rejected():
    review = ok_review()
    review["records"][1]["title"] = "Pentair 263059 - FullFloXF® 3-Way CPVC 2.5 in Diverter"
    assert any("identical" in e for e in validate(review, WORDS))


def test_parts_must_be_pentair():
    review = ok_review()
    review["records"][2]["brand"] = "Sta-Rite"
    review["records"][2]["title"] = "Sta-Rite 270119Z - Check Valve Rebuild Kit"
    assert any("always brand Pentair" in e for e in validate(review, WORDS))


def test_fused_token_accepted_but_not_partial_invention():
    words = WORDS + ["ULTRA-A5-PAK4Pentair"]
    review = ok_review()
    review["records"][0]["replaced_by"] = "ULTRA-A5-PAK4"
    review["dismissed"].append({"token": "ULTRA-A5-PAK4", "reason": "other", "note": "replacement"})
    assert validate(review, words) == []
    review["records"][0]["replaced_by"] = "ULTRA-A5-PAK"
    assert any("replaced_by" in e for e in validate(review, words))


def test_discontinued_list_allows_empty_title_but_checks_status():
    words = ["PA100", "ULTRA-D1"]
    review = {"page_type": "discontinued_list", "records": [
        {"mpn": "PA100", "brand": "Pleatco", "title": "", "kind": "part", "status": "discontinued", "replaced_by": "ULTRA-D1"}],
        "dismissed": [{"token": "ULTRA-D1", "reason": "other", "note": "replacement only"}]}
    assert validate(review, words) == []
    review["records"][0]["status"] = "active"
    assert any("must have status discontinued" in e for e in validate(review, words))


def test_uppercase_dimension_x_rejected():
    review = ok_review()
    review["records"][0]["title"] = "Pentair 263056 - FullFloXF® Diverter 7 in X 14 in"
    assert any("lowercase 'x'" in e for e in validate(review, WORDS))


def test_multi_word_mpn():
    words = WORDS + ["PKG", "188Z", "Union", "x", "2", "in."]
    review = ok_review()
    review["records"].append(record("PKG 188Z", "Pentair PKG 188Z - Union x 2 in Slip Adapter, Set of 2", kind="part"))
    assert validate(review, words) == []
    review["records"][-1]["mpn"] = "PKG 189Z"
    review["records"][-1]["title"] = "Pentair PKG 189Z - Union x 2 in Slip Adapter, Set of 2"
    assert any("multi-word MPN" in e for e in validate(review, words))
