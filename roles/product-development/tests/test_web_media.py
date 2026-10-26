import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import web_media  # noqa: E402


def test_classify_documents():
    c = web_media.classify
    assert c("IntelliFlo3 VSF Installation Guide - Spanish", "x/install-guide-sp.pdf") == ("installation guide", "es")
    assert c("Prowler Family Brochure French Canadian", "x/brochure-fc.pdf") == ("brochure", "fr")
    assert c("Download", "https://www.pentair.com/content/dam/x/parts-sheets/pool-pumps/Booster_Pump.pdf") == ("parts sheet", "en")
    assert c("Download", "x/manuals/superflo-vs-pump-manual-english.pdf")[0] == "user guide"
    assert c("Product Registration Card", "x/documents/warranty-registration-card.pdf")[0] == "form"
    assert c("Pleatco DE Grids Data Sheet", "x/pleatco-de-grids-data-sheet.pdf") == ("data sheet", "en")
