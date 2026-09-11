"""Shared scraper plumbing."""

import logging
import random
import time

import requests

import config
import matcher

log = logging.getLogger("scrapers")


class BaseScraper:
    site = "base"
    condition = "used"  # overridden by retail scrapers

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
        })

    def throttle(self):
        time.sleep(random.uniform(*config.REQUEST_DELAY_RANGE))

    def get(self, url, **kwargs):
        kwargs.setdefault("timeout", config.REQUEST_TIMEOUT)
        return self.session.get(url, **kwargs)

    def build_listing(self, listing_id, title, price, url,
                      description: str = "", condition: str | None = None):
        """Classify and normalize one raw result. Returns dict or None."""
        if price is None:
            return None
        try:
            price = float(price)
        except (TypeError, ValueError):
            return None
        if matcher.is_junk(title, price):
            return None
        model = matcher.match_model(title)
        if model is None:
            return None
        cond = condition or self.condition
        defective = (cond == "used") and matcher.is_defective(title, description)
        # Repair-only (old) models are kept only when defective.
        if matcher.is_repair_only_model(model) and not defective:
            return None
        return {
            "site": self.site,
            "listing_id": str(listing_id),
            "title": title.strip()[:300],
            "price": price,
            "url": url,
            "model": model,
            "condition": cond,
            "is_defective": defective,
        }

    def queries(self):
        qs = list(config.MAIN_QUERIES)
        if self.site in config.SECONDHAND_SITES:
            qs += config.REPAIR_QUERIES
        return qs

    def scrape(self) -> list:
        """Run all queries; never raise — log and continue."""
        results = []
        for q in self.queries():
            try:
                found = self.search(q)
                log.info("[%s] '%s' -> %d matched", self.site, q, len(found))
                results.extend(found)
            except Exception as e:  # noqa: BLE001 - resilience by design
                log.warning("[%s] query '%s' failed: %s", self.site, q, e)
            self.throttle()
        # de-dup by listing_id within this run
        seen, unique = set(), []
        for l in results:
            key = (l["site"], l["listing_id"])
            if key not in seen:
                seen.add(key)
                unique.append(l)
        return unique

    def search(self, query: str) -> list:
        raise NotImplementedError
