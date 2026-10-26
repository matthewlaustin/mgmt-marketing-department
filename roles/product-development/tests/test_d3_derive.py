import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import d3_derive  # noqa: E402
import doc_mentions  # noqa: E402


def test_category_type():
    assert d3_derive.category_type("PUMPS - INGROUND › INTELLIPRO3® VSF", "model")[0] == "Pool Pump"
    assert d3_derive.category_type("PUMP PARTS - INGROUND › X", "part")[0] == "Pump Part"
    assert d3_derive.category_type("FILTERS - CARTRIDGE › CLEAN & CLEAR", "model")[0] == "Cartridge Filter"
    assert d3_derive.category_type("HEATERS AND HEAT PUMPS › MASTERTEMP", "kit")[0] == "Pool Heater Part"
    assert d3_derive.category_type("", "model") is None


def test_brochure_keys():
    assert doc_mentions.key_of("IntelliPro3® VSF Variable Speed and Flow Pool Pump") == "intellipro3 vsf"
    assert doc_mentions.key_of("MasterTemp® 125 Heater") == "mastertemp 125"
    assert doc_mentions.key_of("Tagelus® Top Mount Filters") == "tagelus"
    assert doc_mentions.key_of("C Series® Commercial Bronze") is None
    assert doc_mentions.key_of("Bronze valves") is None
