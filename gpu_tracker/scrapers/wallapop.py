"""Wallapop — internal search API. Coordinates default to Porto so results
are biased to nearby sellers; shipping-enabled items appear regardless.

Note: Wallapop changes this API occasionally. If results go empty, inspect
the network tab on wallapop.com/app/search and update API/params here.
"""

from .base import BaseScraper

PORTO = {"latitude": "41.1496", "longitude": "-8.6109"}


class WallapopScraper(BaseScraper):
    site = "wallapop"
    condition = "used"

    API = "https://api.wallapop.com/api/3/general/search"

    def __init__(self):
        super().__init__()
        self.session.headers.update({
            "X-DeviceOS": "0",
            "Accept": "application/json",
        })

    def search(self, query: str) -> list:
        params = {
            "keywords": query,
            "order_by": "newest",
            **PORTO,
        }
        r = self.get(self.API, params=params)
        r.raise_for_status()
        data = r.json()
        items = (data.get("search_objects")
                 or data.get("data", {}).get("section", {})
                       .get("payload", {}).get("items", [])
                 or [])
        out = []
        for it in items:
            price = it.get("price")
            if isinstance(price, dict):  # newer API shape
                price = price.get("amount")
            slug = it.get("web_slug") or it.get("slug")
            url = f"https://pt.wallapop.com/item/{slug}" if slug else None
            listing = self.build_listing(
                listing_id=it.get("id"),
                title=it.get("title", ""),
                price=price,
                url=url,
                description=(it.get("description") or "")[:500],
            )
            if listing:
                out.append(listing)
        return out
