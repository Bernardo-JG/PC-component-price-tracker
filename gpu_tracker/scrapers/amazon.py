"""Amazon.es — best effort only.

Amazon actively blocks scrapers. This module tries plain HTML parsing of the
search results page and gives up cleanly (logging a warning) when it gets a
captcha or block page. New retail prices from PCDiga are usually enough as a
market-ceiling reference, so a failed Amazon run is not a problem.
"""

import logging
import re

from bs4 import BeautifulSoup

from .base import BaseScraper

log = logging.getLogger("scrapers")


class AmazonScraper(BaseScraper):
    site = "amazon"
    condition = "new"

    SEARCH = "https://www.amazon.es/s"

    def __init__(self):
        super().__init__()
        self.session.headers.update({
            "Accept": ("text/html,application/xhtml+xml,application/xml;"
                       "q=0.9,*/*;q=0.8"),
            "Accept-Language": "es-ES,es;q=0.9,pt;q=0.8,en;q=0.7",
        })
        self._blocked = False

    def search(self, query: str) -> list:
        if self._blocked:
            return []
        r = self.get(self.SEARCH, params={"k": f"{query} tarjeta grafica"})
        if r.status_code != 200 or "captcha" in r.text.lower():
            log.warning("[amazon] blocked/captcha — skipping remaining "
                        "amazon queries this run")
            self._blocked = True
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        out = []
        for card in soup.select('div[data-component-type="s-search-result"]'):
            asin = card.get("data-asin")
            title_el = card.select_one("h2 span") or card.select_one("h2")
            whole = card.select_one("span.a-price-whole")
            frac = card.select_one("span.a-price-fraction")
            if not (asin and title_el and whole):
                continue
            try:
                price = float(
                    re.sub(r"[^\d]", "", whole.get_text())
                    + "." + re.sub(r"[^\d]", "", frac.get_text() if frac else "0"))
            except ValueError:
                continue
            listing = self.build_listing(
                listing_id=asin,
                title=title_el.get_text(strip=True),
                price=price,
                url=f"https://www.amazon.es/dp/{asin}",
            )
            if listing:
                out.append(listing)
        return out
