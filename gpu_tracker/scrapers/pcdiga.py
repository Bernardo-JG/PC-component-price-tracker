"""PCDiga — parses the catalog search results page.

Strategy: prefer JSON-LD structured data (robust to CSS changes), fall back
to product-card HTML parsing.
"""

import json
import re

from bs4 import BeautifulSoup

from .base import BaseScraper


class PcdigaScraper(BaseScraper):
    site = "pcdiga"
    condition = "new"

    SEARCH = "https://www.pcdiga.com/catalogsearch/result/"

    def search(self, query: str) -> list:
        r = self.get(self.SEARCH, params={"q": query})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        out = []

        # 1) JSON-LD ItemList / Product blocks
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            for prod in self._iter_products(data):
                offers = prod.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                listing = self.build_listing(
                    listing_id=prod.get("sku") or prod.get("url", ""),
                    title=prod.get("name", ""),
                    price=offers.get("price"),
                    url=prod.get("url"),
                )
                if listing:
                    out.append(listing)
        if out:
            return out

        # 2) Fallback: product cards
        for card in soup.select("li.product-item, div.product-item"):
            link = card.select_one("a.product-item-link, a[href]")
            price_el = card.select_one("[data-price-amount], span.price")
            if not link:
                continue
            title = link.get_text(strip=True)
            price = None
            if price_el is not None:
                price = price_el.get("data-price-amount")
                if price is None:
                    m = re.search(r"([\d.,]+)", price_el.get_text())
                    if m:
                        price = m.group(1).replace(".", "").replace(",", ".")
            listing = self.build_listing(
                listing_id=link.get("href", title),
                title=title,
                price=price,
                url=link.get("href"),
            )
            if listing:
                out.append(listing)
        return out

    @staticmethod
    def _iter_products(data):
        if isinstance(data, dict):
            if data.get("@type") == "Product":
                yield data
            for v in data.values():
                yield from PcdigaScraper._iter_products(v)
        elif isinstance(data, list):
            for v in data:
                yield from PcdigaScraper._iter_products(v)
