from __future__ import annotations

import re
from dataclasses import asdict, dataclass, fields


@dataclass
class Product:
    """One sellable SKU found on a brand's website."""

    sku: str
    title: str
    brand: str = ""
    mpn: str = ""
    gtin: str = ""
    url: str = ""
    source: str = ""  # which strategy found it: shopify, woocommerce, json-ld, microdata, page-text

    @classmethod
    def field_names(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


_WS = re.compile(r"\s+")


def clean(value: object) -> str:
    """Collapse whitespace and coerce to a string; None/empty become ''."""
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        value = str(value)
    if not isinstance(value, str):
        return ""
    return _WS.sub(" ", value).strip()


def brand_matches(product_brand: str, wanted: str) -> bool:
    """Loose comparison so 'Hayward Pool Products' matches 'Hayward'."""
    a = re.sub(r"[^a-z0-9]", "", product_brand.lower())
    b = re.sub(r"[^a-z0-9]", "", wanted.lower())
    return bool(a and b) and (a in b or b in a)
