"""Shopify Admin API client for the development store.

Credentials come from the environment only (never from chat or the repo):
  SHOPIFY_SHOP            your-dev-store.myshopify.com
  SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET   (Dev Dashboard app: exchanged for a 24 h token, client credentials grant)
  or SHOPIFY_ADMIN_TOKEN  (legacy custom app created in the store admin: permanent shpat_ token)

Usage:
  python3 scripts/shopify_client.py check     # read-only: shop name, plan, primary domain, granted scopes
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

API_VERSION = "2025-10"
_token_cache: dict = {}


class ShopifyError(RuntimeError):
    pass


def shop() -> str:
    s = os.environ.get("SHOPIFY_SHOP", "").strip().removeprefix("https://").rstrip("/")
    if not s:
        raise ShopifyError("SHOPIFY_SHOP is not set in the environment")
    return s


def auth_mode(env: dict | None = None) -> str:
    env = os.environ if env is None else env
    if env.get("SHOPIFY_ADMIN_TOKEN"):
        return "token"
    if env.get("SHOPIFY_CLIENT_ID") and env.get("SHOPIFY_CLIENT_SECRET"):
        return "client_credentials"
    return "none"


def access_token() -> str:
    mode = auth_mode()
    if mode == "token":
        return os.environ["SHOPIFY_ADMIN_TOKEN"]
    if mode == "none":
        raise ShopifyError("no Shopify credentials in the environment (SHOPIFY_ADMIN_TOKEN, or SHOPIFY_CLIENT_ID and SHOPIFY_CLIENT_SECRET)")
    if _token_cache.get("expires", 0) > time.time() + 60:
        return _token_cache["token"]
    body = json.dumps({"client_id": os.environ["SHOPIFY_CLIENT_ID"], "client_secret": os.environ["SHOPIFY_CLIENT_SECRET"],
                       "grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(f"https://{shop()}/admin/oauth/access_token", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise ShopifyError(f"token exchange failed: HTTP {e.code} {e.read()[:300]!r}") from None
    _token_cache.update(token=data["access_token"], expires=time.time() + int(data.get("expires_in", 86400)))
    return data["access_token"]


def graphql(query: str, variables: dict | None = None, retries: int = 3) -> dict:
    """One GraphQL call against the Admin API. Raises ShopifyError on transport, GraphQL or throttle failures."""
    req = urllib.request.Request(f"https://{shop()}/admin/api/{API_VERSION}/graphql.json",
                                 data=json.dumps({"query": query, "variables": variables or {}}).encode(),
                                 headers={"Content-Type": "application/json", "X-Shopify-Access-Token": access_token()})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise ShopifyError(f"HTTP {e.code}: {e.read()[:300]!r}") from None
        errs = data.get("errors")
        if errs:
            if any("THROTTLED" in json.dumps(x) for x in errs) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise ShopifyError(json.dumps(errs)[:500])
        return data["data"]
    raise ShopifyError("gave up after retries")


def check() -> dict:
    data = graphql("""{ shop { name myshopifyDomain primaryDomain { host } plan { partnerDevelopment shopifyPlus } currencyCode }
                       currentAppInstallation { accessScopes { handle } } }""")
    s = data["shop"]
    return {"shop": s["name"], "domain": s["myshopifyDomain"], "primary": s["primaryDomain"]["host"], "currency": s["currencyCode"],
            "development_store": s["plan"]["partnerDevelopment"], "auth": auth_mode(),
            "scopes": sorted(x["handle"] for x in data["currentAppInstallation"]["accessScopes"])}


def main(argv: list[str]) -> int:
    if argv[1:2] == ["check"]:
        try:
            print(json.dumps(check(), indent=1))
        except ShopifyError as e:
            print("Shopify:", e, file=sys.stderr)
            return 1
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
