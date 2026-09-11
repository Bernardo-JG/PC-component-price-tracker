"""Vinted.pt — uses the same JSON API the website frontend calls.

A first GET to the homepage establishes anonymous session cookies that the
API endpoint requires.
"""

from .base import BaseScraper


class VintedScraper(BaseScraper):
    site = "vinted"
    condition = "used"

    BASE = "https://www.vinted.pt"
    API = "https://www.vinted.pt/api/v2/catalog/items"

    def __init__(self):
        super().__init__()
        self._bootstrapped = False

    def _bootstrap(self):
        if not self._bootstrapped:
            self.get(self.BASE)  # sets anon cookies / access token
            self._bootstrapped = True

    def search(self, query: str) -> list:
        self._bootstrap()
        params = {
            "search_text": query,
            "per_page": 96,
            "order": "newest_first",
        }
        r = self.get(self.API, params=params)
        if r.status_code in (401, 403):
            # cookies expired — re-bootstrap once
            self._bootstrapped = False
            self._bootstrap()
            r = self.get(self.API, params=params)
        r.raise_for_status()
        items = r.json().get("items", [])
        out = []
        for it in items:
            price_info = it.get("price") or {}
            price = price_info.get("amount") if isinstance(price_info, dict) else price_info
            listing = self.build_listing(
                listing_id=it.get("id"),
                title=it.get("title", ""),
                price=price,
                url=f"{self.BASE}{it.get('path', '')}" if it.get("path")
                    else it.get("url"),
            )
            if listing:
                out.append(listing)
        return out
