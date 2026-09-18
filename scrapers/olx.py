"""OLX adapter. Paginated collection; reports errors and coverage limits."""
from urllib.parse import urlencode, urlsplit
from .base import BaseScraper
import config


class OlxScraper(BaseScraper):
    site = 'olx'
    API = 'https://www.olx.pt/api/v1/offers/'

    @staticmethod
    def image_urls(item):
        """Expand OLX photo templates using reported dimensions, capped at 1024px."""
        images = []
        for photo in item.get('photos') or []:
            if not isinstance(photo, dict):
                continue
            link = photo.get('link')
            if not isinstance(link, str):
                continue
            try:
                width = max(1, int(photo.get('width') or 1024))
                height = max(1, int(photo.get('height') or 1024))
                scale = min(1, 1024 / max(width, height))
                link = link.replace('{width}', str(max(1, round(width * scale))))
                link = link.replace('{height}', str(max(1, round(height * scale))))
                parsed = urlsplit(link)
                if parsed.scheme != 'https' or not parsed.hostname or '{' in link:
                    continue
            except (TypeError, ValueError):
                continue
            if link not in images:
                images.append(link)
        return images

    def parse_offer(self, item):
        if item.get('status', 'active') != 'active':
            return None
        params = {p.get('key'): p.get('value') for p in item.get('params') or [] if isinstance(p, dict)}
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
                                  key if key in {'new', 'used'} else 'unknown',
                                  images=self.image_urls(item), currency=value.get('currency', 'EUR'))

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
        self.diagnostics.append(f'{query}: {fetched} fetched, {matched} collected for classification')
        if fetched and not matched:
            self.diagnostics.append(f'{query}: WARNING no valid cash listings collected; check results/query support')
