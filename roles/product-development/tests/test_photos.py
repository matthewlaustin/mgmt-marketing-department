import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import photo_candidates  # noqa: E402
import page_images  # noqa: E402


def test_grade_tiers():
    g = photo_candidates.grade
    assert g(1200, 1000) == "ok"
    assert g(1400, 800) == "long"   # padded to a 1400 square
    assert g(800, 600) == "mid"     # Matthew 2026-10-26: 500 px cutoff when nothing larger exists
    assert g(499, 499) == "small"
    assert g(None, None) == "small"


def test_full_size_never_asks_to_enlarge():
    u = page_images.full_size("https://i8.amplience.net/i/lesl/304624_01/x?$pdpExtraLarge$")
    assert "upscale=false" in u
    assert page_images.full_size("https://cdn.shopify.com/s/files/1/x/products/a_600x600.jpg?v=1") == "https://cdn.shopify.com/s/files/1/x/products/a.jpg"
