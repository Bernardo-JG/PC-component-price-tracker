"""Synthetic transport/contract tests; historical evidence checks are explicit."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scrapers.vinted import VintedScraper


class VintedAdapterTests(unittest.TestCase):
    def setUp(self):
        self.scraper = VintedScraper()
        self.scraper.throttle = lambda: None

    def item(self, **updates):
        item = {'id': 123, 'title': 'cooler para RTX 3080', 'price': {'amount': '19.00', 'currency_code': 'EUR'}, 'description': 'Só o cooler.'}
        return {**item, **updates}

    def test_raw_contract_preserves_accessory_for_shared_classifier(self):
        with patch.object(self.scraper, 'build_listing', return_value={'raw': True}) as build:
            self.assertEqual(self.scraper.parse_offer(self.item()), {'raw': True})
            self.assertEqual(build.call_args.args[1], 'cooler para RTX 3080')
            self.assertEqual(build.call_args.kwargs['condition'], 'unknown')
            self.assertEqual(build.call_args.kwargs['description'], 'Só o cooler.')
            self.assertEqual(build.call_args.kwargs['currency'], 'EUR')

    def test_no_price_or_currency_invention(self):
        with patch.object(self.scraper, 'build_listing') as build:
            self.assertIsNone(self.scraper.parse_offer(self.item(price=None)))
            build.assert_not_called()

    def test_https_photos_and_foreign_currency_preserved(self):
        item = self.item(price={'amount': '10', 'currency_code': 'PLN'}, photos=[{'url': 'https://images.vinted.net/a.jpg'}, {'url': 'http://bad/a.jpg'}])
        with patch.object(self.scraper, 'build_listing') as build:
            self.scraper.parse_offer(item)
            self.assertEqual(build.call_args.kwargs['images'], ['https://images.vinted.net/a.jpg'])
            self.assertEqual(build.call_args.kwargs['currency'], 'PLN')

    def test_sold_and_reserved_skipped(self):
        for key in ('is_sold', 'is_closed', 'is_hidden', 'is_reserved'):
            self.assertIsNone(self.scraper.parse_offer(self.item(**{key: True})))

    def test_detail_description_is_used(self):
        catalog = self.item()
        del catalog['description']
        self.scraper.get_json = lambda url: {'items': [catalog]} if '/catalog/' in url else {'item': self.item(description='Apenas caixa vazia.')}
        with patch.object(self.scraper, 'build_listing', return_value={'listing_id': '123'}) as build:
            self.assertEqual(len(list(self.scraper.search('rtx'))), 1)
            self.assertEqual(build.call_args.kwargs['description'], 'Apenas caixa vazia.')

    def test_missing_detail_is_not_yielded(self):
        item = self.item()
        del item['description']
        self.scraper.get_json = lambda url: {'items': [item]} if '/catalog/' in url else {'item': {'id': 123}}
        self.assertEqual(list(self.scraper.search('rtx')), [])
        self.assertTrue(any('missing detail' in d for d in self.scraper.diagnostics))

    def test_detail_cap_is_explicit(self):
        self.scraper.max_detail_requests = 0
        item = self.item()
        del item['description']
        self.scraper.get_json = lambda url: {'items': [item]}
        self.assertEqual(list(self.scraper.search('rtx')), [])
        self.assertIn('DETAIL CAP', self.scraper.diagnostics[0])

    def test_repeated_page_detected(self):
        self.scraper.get_json = lambda url: {'items': [self.item()], 'pagination': {'total_pages': 3}}
        with patch.object(self.scraper, 'build_listing', return_value={'listing_id': '123'}):
            with self.assertRaisesRegex(ValueError, 'Repeated'):
                list(self.scraper.search('rtx'))

    def test_bad_payload_and_access_error_propagate(self):
        self.scraper.get_json = lambda url: {'error': 'blocked'}
        with self.assertRaises(ValueError):
            list(self.scraper.search('rtx'))
        with patch.object(self.scraper, 'get_json', side_effect=PermissionError('403')):
            with self.assertRaises(PermissionError):
                list(self.scraper.search('rtx'))

    def test_real_indexed_fixture_provenance_and_missing_data(self):
        # Evidence integrity only. This does not claim a live API/model test.
        data = json.loads((Path(__file__).parent / 'fixtures/vinted/real_indexed.json').read_text())
        self.assertEqual(data['kind'], 'real_historical_search_index_evidence')
        self.assertEqual(data['cases'][0]['price'], 80)
        self.assertIn('defeito', data['cases'][0]['title'])
        self.assertIsNone(data['cases'][1]['price'])
        self.assertFalse(data['cases'][1]['expected']['eligible_for_working_median'])


if __name__ == '__main__':
    unittest.main()
