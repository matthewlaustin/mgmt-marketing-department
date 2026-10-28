import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from v2_check import v2_problems  # noqa: E402


def test_good_titles_pass():
    assert v2_problems("Pentair", "350091Z", "Pentair 350091Z - Lid") == []
    assert v2_problems("Pentair/Sta-Rite", "354545S", "Pentair/Sta-Rite 354545S - 5/8 in Mechanical Seal") == []
    assert v2_problems("Pentair", "460734", "Pentair 460734 - MasterTemp® 300K BTU Natural Gas Heater") == []


def test_rejects_v2_banned_words():
    assert v2_problems("Pentair", "1", "Pentair 1 - MasterTemp® High Performance Heater")
    assert v2_problems("Pentair", "1", "Pentair 1 - 2 in Top Valve Assy")
    assert v2_problems("Pentair", "1", "Pentair 1 - No. 2 pH Test Solution, Display Box")
    assert v2_problems("Pentair", "1", "Pentair 1 - Drive 525-600 VAC")
    assert v2_problems("Pentair", "1", "Pentair 1 - 24 Sq Ft Filter Tank Lid")


def test_rejects_bad_brand_and_prefix():
    assert v2_problems("Hayward", "1", "Hayward 1 - Lid")
    assert v2_problems("Pentair", "1", "Pentair 2 - Lid")
