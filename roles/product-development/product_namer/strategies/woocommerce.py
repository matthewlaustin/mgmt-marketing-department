from __future__ import annotations

import logging
from collections.abc import Iterator

from ..http import Fetcher
from ..models import Product, clean

log = logging.getLogger(__name__)

API = "/wp-json/wc/store/v1/products"
PAGE_SIZE = 100
MAX_PAGES = 1000


def detect(fetcher: Fetcher) -> bool:
    data = fetcher.get_json(f"{API}?per_page=1")
    return isinstance(data, list)


def scrape(fetcher: Fetcher) -> Iterator[Product]:
    """WooCommerce's public Store API lists products (and their variations) without auth."""
    for page in range(1, MAX_PAGES + 1):
        data = fetcher.get_json(f"{API}?per_page={PAGE_SIZE}&page={page}")
        if not isinstance(data, list) or not data:
            return
        log.info("woocommerce: page %d, %d products", page, len(data))
        for item in data:
            yield from _expand(fetcher, item)


def _brand(item: dict) -> str:
    brands = item.get("brands") or []
    if brands and isinstance(brands[0], dict):
        return clean(brands[0].get("name"))
    return ""


def _expand(fetcher: Fetcher, item: dict) -> Iterator[Product]:
    name = clean(item.get("name"))
    brand = _brand(item)
    url = clean(item.get("permalink"))
    variations = item.get("variations") or []
    if not variations:
        sku = clean(item.get("sku"))
        if sku:
            yield Product(sku=sku, title=name, brand=brand, url=url, source="woocommerce")
        return
    for variation in variations:
        detail = fetcher.get_json(f"{API}/{variation.get('id')}") or {}
        sku = clean(detail.get("sku"))
        if not sku:
            continue
        options = [clean(a.get("value")) for a in variation.get("attributes") or [] if a.get("value")]
        title = f"{name} - {', '.join(options)}" if options else clean(detail.get("name")) or name
        yield Product(
            sku=sku,
            title=title,
            brand=brand,
            url=clean(detail.get("permalink")) or url,
            source="woocommerce",
        )
