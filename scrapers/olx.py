"""OLX adapter. Paginated collection; reports errors and coverage limits."""
from urllib.parse import urlencode
from .base import BaseScraper
import config


class OlxScraper(BaseScraper):
    API = 'https://www.olx.pt/api/v1/offers/'

    def parse_offer(self, item):
        if item.get('status', 'active') != 'active':
            return None
        params = {p.get('key'): p.get('value') for p in item.get('params', [])}
        value = params.get('price') or {}
        if not isinstance(value, dict) or value.get('currency', 'EUR') != 'EUR':
            return None
        # Exchange/free/placeholder prices do not describe a normal cash sale.
        if value.get('type') in {'exchange', 'free'}:
            return None
        loc = item.get('location') or {}
        names = [loc.get(k, {}).get('name') for k in ('city','district','region') if isinstance(loc.get(k), dict)]
        location = ', '.join(dict.fromkeys(n for n in names if n))
        state = params.get('state') or {}
        key = state.get('key') if isinstance(state, dict) else state
        return self.build_listing(item.get('id'), item.get('title',''), value.get('value'),
                                  item.get('url') or f"https://www.olx.pt/{item.get('id')}/",
                                  item.get('description') or '', location,
                                  'new' if key == 'new' else 'used')

    def search(self, query):
        fetched = matched = 0
        seen = set()
        for page in range(config.MAX_PAGES_PER_QUERY):
            url = self.API + '?' + urlencode(dict(offset=page*config.PAGE_SIZE, limit=config.PAGE_SIZE,
                                                  query=query, category_id=config.OLX_CATEGORY_ID, sort_by='created_at:desc'))
            payload = self.get_json(url)
            if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
                raise ValueError('Unexpected response: expected a data list')
            data = payload['data']
            ids = {str(i.get('id')) for i in data if isinstance(i, dict)}
            if data and ids <= seen:
                raise ValueError('Repeated page: pagination may be ignored')
            seen.update(ids)
            fetched += len(data)
            for item in data:
                if not isinstance(item, dict):
                    raise ValueError('Unexpected offer format')
                listing = self.parse_offer(item)
                if listing:
                    matched += 1
                    yield listing
            total = payload.get('metadata', {}).get('total_elements')
            if not data or (isinstance(total, int) and (page+1)*config.PAGE_SIZE >= total) or (total is None and len(data) < config.PAGE_SIZE):
                break
            if page == config.MAX_PAGES_PER_QUERY-1:
                self.diagnostics.append(f'{query}: PAGE CAP reached; more listings may exist')
            else:
                self.throttle()
        self.diagnostics.append(f'{query}: {fetched} fetched, {matched} recognised')
        if fetched and not matched:
            self.diagnostics.append(f'{query}: WARNING no components recognised; check results/query support')
