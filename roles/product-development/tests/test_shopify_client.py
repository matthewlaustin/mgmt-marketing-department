import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import shopify_client as sc  # noqa: E402


def test_auth_mode_prefers_permanent_token():
    assert sc.auth_mode({"SHOPIFY_ADMIN_TOKEN": "shpat_x", "SHOPIFY_CLIENT_ID": "a", "SHOPIFY_CLIENT_SECRET": "b"}) == "token"
    assert sc.auth_mode({"SHOPIFY_CLIENT_ID": "a", "SHOPIFY_CLIENT_SECRET": "b"}) == "client_credentials"
    assert sc.auth_mode({"SHOPIFY_CLIENT_ID": "a"}) == "none"
    assert sc.auth_mode({}) == "none"
