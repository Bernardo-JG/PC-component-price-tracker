"""Adapter tests: real captured API data and explicitly synthetic transport cases."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import config
from scrapers.olx import OlxScraper

FIXTURES = Path(__file__).parent / 'fixtures' / 'olx'


class OlxAdapter(unittest.TestCase):
    def setUp(self):
        self.scraper = OlxScraper()

    def capture(self, offer):
        # Test only the platform-to-common-interface boundary. The shared base
        # and classification pipeline have their own tests; this isn't inference.
        with patch.object(self.scraper, 'build_listing', return_value={'raw': True}) as build:
            result = self.scraper.parse_offer(offer)
        return result, build

    def test_real_api_fixtures_keep_description_price_and_images(self):
        for path in FIXTURES.glob('*.json'):
            with self.subTest(path=path.name):
                fixture = json.loads(path.read_text())
                self.assertEqual(fixture['fixture_kind'], 'real')
                offer = fixture['source_payload']['data']
                result, build = self.capture(offer)
                self.assertIsNotNone(result)
                args, kwargs = build.call_args
                self.assertEqual(args[0], offer['id'])
                self.assertEqual(args[1], offer['title'])
                price = next(p['value']['value'] for p in offer['params'] if p['key'] == 'price')
                self.assertEqual(args[2], price)
                self.assertEqual(args[4], offer['description'])
                self.assertEqual(kwargs['currency'], 'EUR')
                self.assertTrue(kwargs['images'])
                self.assertTrue(all(u.startswith('https://') and '{' not in u for u in kwargs['images']))

    def test_synthetic_unknown_condition_is_not_used(self):
        offer = {'id': 'synthetic', 'title': 'Gráfica', 'params': [
            {'key': 'price', 'value': {'value': 30, 'currency': 'EUR'}}]}
        _, build = self.capture(offer)
        self.assertEqual(build.call_args.args[6], 'unknown')

    def test_synthetic_unsafe_or_invalid_images_are_ignored(self):
        offer = {'photos': [{'link': 'file:///tmp/a'}, {'link': 'http://example.org/a'},
                            {'link': 'https://example.org/{width}x{height}', 'width': 4000, 'height': 2000},
                            {'link': 'https://example.org/{width}x{height}', 'width': 4000, 'height': 2000},
                            None, {'link': 'https://example.org/{bad}'}]}
        self.assertEqual(self.scraper.image_urls(offer), ['https://example.org/1024x512'])

    def test_synthetic_non_cash_or_inactive_offers_rejected(self):
        for price in [{'value': 100, 'currency': 'USD'}, {'value': 100, 'type': 'exchange'}, {'value': 0, 'type': 'free'}]:
            result, build = self.capture({'id': 1, 'params': [{'key': 'price', 'value': price}]})
            self.assertIsNone(result)
            build.assert_not_called()
        result, build = self.capture({'status': 'inactive'})
        self.assertIsNone(result)
        build.assert_not_called()

    def test_synthetic_accessories_are_forwarded_for_shared_classification(self):
        for title in ['cooler para RTX 3080', 'caixa de RTX 2060', 'procuro RX 6600', 'kit Ryzen e RAM', 'RTX 2060 avariada']:
            _, build = self.capture({'id': 1, 'title': title, 'params': [{'key': 'price', 'value': {'value': 50}}]})
            self.assertEqual(build.call_args.args[1], title)

    def test_synthetic_search_yields_raw_not_classified_offers(self):
        offer = json.loads((FIXTURES / 'cooler_accessory.json').read_text())['source_payload']['data']
        with patch.object(self.scraper, 'build_listing', return_value={'listing_id': str(offer['id'])}), patch.object(self.scraper, 'get_json', return_value={'data': [offer], 'metadata': {'total_elements': 1}}):
            results = list(self.scraper.search('RTX 3080'))
        self.assertEqual(len(results), 1)
        self.assertIn('collected for classification', self.scraper.diagnostics[-1])


if __name__ == '__main__':
    unittest.main()
