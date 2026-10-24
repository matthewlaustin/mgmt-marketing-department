import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "consolidate", Path(__file__).resolve().parents[1] / "scripts/consolidate.py")
consolidate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(consolidate)


def test_canonical_trademarks():
    c = consolidate.canonical
    assert c("System 3® SM Filter") == "System:3® SM Filter"
    assert c("Valve for System 3 Mod DE") == "Valve for System:3® Mod DE"
    assert c("System 2™ PLM Module") == "System:2™ PLM Module"
    assert c("Hi-Flow™ Valve") == "HiFlow™ Valve"
    assert c("ThermalFlo™ Heat Pump") == "ThermalFlo® Heat Pump"
    assert c("IntelliProXF VS Pump") == "IntelliProXF® VS Pump"
    assert c("IntelliProXF® VS Pump") == "IntelliProXF® VS Pump"
    assert c("3/8-16 S/S Nut") == "3/8-16 SS Nut"


def test_canonical_leaves_unmarked_lookalikes():
    c = consolidate.canonical
    assert c("IntelliChem® Commercial System 2 Pumps Controller") == "IntelliChem® Commercial System 2 Pumps Controller"
    assert c("BioShield® UV System 2.5 in x 1 in Reducer Tee") == "BioShield® UV System 2.5 in x 1 in Reducer Tee"
