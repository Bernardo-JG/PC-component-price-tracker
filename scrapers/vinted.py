"""Read-only Vinted adapter. Classification belongs to the shared pipeline.

The public web API is undocumented and can deny automated access. Fail closed
on missing detail, malformed responses, and HTTP errors; never bypass blocks.
"""
import argparse
import json
from urllib.parse import urlencode, urlparse

import config
from .base import BaseScraper


class VintedScraper(BaseScraper):
    site = 'vinted'
    API = 'https://www.vinted.pt/api/v2'

    def __init__(self, max_detail_requests=20):
        super().__init__()
        self.max_detail_requests = max_detail_requests

    def parse_offer(self, item):
        if not isinstance(item, dict):
            raise ValueError('Unexpected Vinted item format')
        if any(item.get(key) is True for key in ('is_closed', 'is_hidden', 'is_reserved', 'is_sold')):
            return None
        price = item.get('price')
        if isinstance(price, dict):
            currency = price.get('currency_code') or price.get('currency')
            price = price.get('amount')
        else:
            currency = item.get('currency')
        # No currency default: do not mislabel foreign prices as euros.
        if not currency:
            return None
        listing_id = item.get('id')
        if listing_id is None or not str(listing_id).isdigit():
            return None
        url = item.get('url') or f'https://www.vinted.pt/items/{listing_id}'
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname != 'www.vinted.pt':
            url = f'https://www.vinted.pt/items/{listing_id}'
        photos = item.get('photos') or ([item['photo']] if item.get('photo') else [])
        images = []
        for photo in photos:
            photo_url = photo.get('full_size_url') or photo.get('url') if isinstance(photo, dict) else None
            if isinstance(photo_url, str) and photo_url.startswith('https://'):
                images.append(photo_url)
        # Vinted status labels are seller claims, not proof of functionality.
        state = item.get('status')
        condition = state if isinstance(state, str) and state.strip() else 'unknown'
        return self.build_listing(
            listing_id, item.get('title') or '', price, url,
            description=item.get('description') or '', location='',
            condition=condition, images=images, currency=currency,
        )

    def search(self, query):
        seen = set()
        detail_count = fetched = emitted = 0
        for page in range(1, config.MAX_PAGES_PER_QUERY + 1):
            payload = self.get_json(self.API + '/catalog/items?' + urlencode({
                'search_text': query, 'page': page, 'per_page': config.PAGE_SIZE,
                'order': 'newest_first',
            }))
            if not isinstance(payload, dict) or not isinstance(payload.get('items'), list):
                raise ValueError('Unexpected Vinted response: expected items list')
            items = payload['items']
            ids = {str(i.get('id')) for i in items if isinstance(i, dict)}
            if items and ids <= seen:
                raise ValueError('Repeated Vinted page; pagination may be ignored')
            fetched += len(items)
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError('Unexpected Vinted item format')
                item_id = str(item.get('id'))
                if item_id in seen:
                    continue
                seen.add(item_id)
                if not item_id.isdigit():
                    continue
                if 'description' not in item:
                    if detail_count >= self.max_detail_requests:
                        self.diagnostics.append(f'{query}: DETAIL CAP reached; incomplete listings skipped')
                        return
                    detail_count += 1
                    self.throttle()
                    # Fail the query on access errors instead of repeated blocked requests.
                    detail = self.get_json(self.API + f'/items/{item_id}')
                    full = detail.get('item') if isinstance(detail, dict) else None
                    if not isinstance(full, dict) or str(full.get('id')) != item_id or 'description' not in full:
                        self.diagnostics.append(f'{query}: {item_id} missing detail; skipped')
                        continue
                    item = {**item, **full}
                listing = self.parse_offer(item)
                if listing:
                    emitted += 1
                    yield listing
            pagination = payload.get('pagination') or {}
            total_pages = pagination.get('total_pages') if isinstance(pagination, dict) else None
            if not items or (isinstance(total_pages, int) and page >= total_pages) or (total_pages is None and len(items) < config.PAGE_SIZE):
                break
            if page == config.MAX_PAGES_PER_QUERY:
                self.diagnostics.append(f'{query}: PAGE CAP reached; more listings may exist')
            else:
                self.throttle()
        self.diagnostics.append(f'{query}: {fetched} fetched, {emitted} raw listings')


def main():
    parser = argparse.ArgumentParser(description='Read-only Vinted probe; outputs raw listings, never buys anything')
    parser.add_argument('--query', default='placa grafica')
    parser.add_argument('--max-details', type=int, default=3)
    args = parser.parse_args()
    scraper = VintedScraper(max_detail_requests=max(0, args.max_details))
    try:
        for listing in scraper.search(args.query):
            print(json.dumps(listing, ensure_ascii=False))
    except Exception as exc:
        scraper.diagnostics.append(f'FAILED: {type(exc).__name__}: {exc}')
        print(json.dumps({'diagnostics': scraper.diagnostics}, ensure_ascii=False))
        return 1
    print(json.dumps({'diagnostics': scraper.diagnostics}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
