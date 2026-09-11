"""OLX.pt — uses the public /api/v1/offers endpoint."""

from .base import BaseScraper


class OlxScraper(BaseScraper):
    site = "olx"
    condition = "used"

    API = "https://www.olx.pt/api/v1/offers/"

    def search(self, query: str) -> list:
        out = []
        for offset in (0, 40):  # two pages of 40
            params = {"offset": offset, "limit": 40, "query": query,
                      "sort_by": "created_at:desc"}
            r = self.get(self.API, params=params)
            r.raise_for_status()
            data = r.json().get("data", [])
            if not data:
                break
            for it in data:
                price = None
                for p in it.get("params", []):
                    if p.get("key") == "price":
                        v = (p.get("value") or {})
                        price = v.get("value")
                        break
                desc = it.get("description", "") or ""
                listing = self.build_listing(
                    listing_id=it.get("id"),
                    title=it.get("title", ""),
                    price=price,
                    url=it.get("url"),
                    description=desc[:500],
                )
                if listing:
                    out.append(listing)
            if len(data) < 40:
                break
            self.throttle()
        return out
