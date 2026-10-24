from product_namer.review import is_candidate, page_tokens, validate

WORDS = "Product Description 263056 3-Way CPVC 2.5 in. (3 in. slip outside) 263059 270119Z P/N 200174.A 28W 120V C-7469 PH6".split()


def record(mpn, title, **kw):
    return {"mpn": mpn, "brand": "Pentair", "title": title, "kind": "whole_good", "status": "active", **kw}


def ok_review():
    return {
        "records": [
            record("263056", "Pentair 263056 - FULLFLOXF® 3-Way CPVC 2.5 in Diverter"),
            record("263059", "Pentair 263059 - FULLFLOXF® 2-Way CPVC 2.5 in Diverter"),
            record("270119Z", "Pentair 270119Z - FULLFLOXF® Check Valve Rebuild Kit", kind="part"),
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
    review["records"].append(record("263057", "Pentair 263057 - FULLFLOXF® Thing"))
    assert any("not found verbatim" in e for e in validate(review, WORDS))


def test_missed_token_reported():
    review = ok_review()
    review["records"].pop(1)
    assert any("unaccounted" in e and "263059" in e for e in validate(review, WORDS))


def test_title_cleanup_enforced():
    review = ok_review()
    review["records"][0]["title"] = "Pentair 263056 - FULLFLOXF® 3-Way CPVC 2.5 in. (3 in. slip outside) Diverter"
    errors = validate(review, WORDS)
    assert any("parenthesis" in e for e in errors)
    assert any("unit with period" in e for e in errors)


def test_title_prefix_enforced():
    review = ok_review()
    review["records"][0]["title"] = "FULLFLOXF® 3-Way CPVC 2.5 in Diverter"
    assert any("must start with" in e for e in validate(review, WORDS))


def test_page_tokens_strip_footnote_marks():
    _, cands = page_tokens(["PCC60*", "ULTRA-A4", "602186,"])
    assert {"PCC60", "ULTRA-A4", "602186"} <= cands
