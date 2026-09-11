"""Standard-library HTTP and explicit scan diagnostics."""
import json
import random
import time
import urllib.request
import config
import matcher


class BaseScraper:
    site = 'olx'

    def __init__(self):
        self.diagnostics = []
        self.failed = 0
        self.successful = 0

    def throttle(self):
        time.sleep(random.uniform(*config.REQUEST_DELAY_RANGE))

    def get_json(self, url):
        req = urllib.request.Request(url, headers={'User-Agent': config.USER_AGENT, 'Accept': 'application/json', 'Accept-Language': 'pt-PT,pt;q=0.9'})
        with urllib.request.urlopen(req, timeout=config.REQUEST_TIMEOUT) as response:
            return json.load(response)

    def build_listing(self, listing_id, title, price, url, description='', location='', condition='used'):
        try:
            price = float(price)
        except (TypeError, ValueError):
            return None
        if listing_id is None or matcher.is_junk(title, price):
            return None
        parsed = matcher.classify(title, description)
        if not parsed:
            return None
        category, model = parsed
        return dict(site=self.site, listing_id=str(listing_id), title=title.strip()[:300],
                    price=price, url=url, category=category, model=model, condition=condition,
                    is_defective=matcher.is_defective(title, description), location=location,
                    description=description)

    def scrape(self, queries=None):
        results = {}
        for query in (queries if queries is not None else config.MAIN_QUERIES):
            print(f'OLX: {query}', flush=True)
            try:
                # Generator preserves earlier pages when a later page fails.
                for item in self.search(query):
                    results[item['listing_id']] = item
                self.successful += 1
            except Exception as exc:
                self.failed += 1
                self.diagnostics.append(f'{query}: FAILED ({type(exc).__name__}: {exc})')
            self.throttle()
        return list(results.values())
