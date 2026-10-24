from __future__ import annotations

import logging
from collections.abc import Iterator
from urllib.parse import urljoin

from ..http import Fetcher
from ..models import Product, clean

log = logging.getLogger(__name__)

PAGE_SIZE = 250
MAX_PAGES = 400  # 100k products; a safety stop against endless pagination


def detect(fetcher: Fetcher) -> bool:
    data = fetcher.get_json("/products.json?limit=1")
    return isinstance(data, dict) and isinstance(data.get("products"), list)


def scrape(fetcher: Fetcher) -> Iterator[Product]:
    """Shopify stores expose their whole public catalog at /products.json."""
    for page in range(1, MAX_PAGES + 1):
        data = fetcher.get_json(f"/products.json?limit={PAGE_SIZE}&page={page}")
        products = (data or {}).get("products") or []
        if not products:
            return
        log.info("shopify: page %d, %d products", page, len(products))
        for item in products:
            yield from _variants(fetcher, item)


def _variants(fetcher: Fetcher, item: dict) -> Iterator[Product]:
    title = clean(item.get("title"))
    url = urljoin(fetcher.base_url, f"/products/{item.get('handle', '')}")
    for variant in item.get("variants") or []:
        sku = clean(variant.get("sku"))
        if not sku:
            continue
        variant_title = clean(variant.get("title"))
        full_title = title
        if variant_title and variant_title.lower() != "default title":
            full_title = f"{title} - {variant_title}"
        yield Product(
            sku=sku,
            title=full_title,
            brand=clean(item.get("vendor")),
            gtin=clean(variant.get("barcode")),
            url=f"{url}?variant={variant.get('id')}" if len(item.get("variants")) > 1 else url,
            source="shopify",
        )
