import unittest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch
import config
import matcher
from db import Database, SCHEMA
from scrapers.olx import OlxScraper
import report


def item(id='123',price=100,title='Radeon XFX 6600 8GB',location='Espinho, Aveiro'):
    return OlxScraper().build_listing(id,title,price,f'https://www.olx.pt/{id}/',location=location)


class Matching(unittest.TestCase):
    def test_shorthand_and_cpu_context(self):
        for title,expected in [('6600','RX 6600'),('RX6600','RX 6600'),('RTX2060 6G','RTX 2060 6GB'),('Radeon XFX 6600 8GB','RX 6600'),
                               ('6600 XT','RX 6600 XT'),('5600 XT','RX 5600 XT'),('2060','RTX 2060 (VRAM unknown)'),
                               ('2060 Super 8GB','RTX 2060 Super'),('Ryzen 5 5600','Ryzen 5600'),
                               ('Processador AMD 7600','Ryzen 7600'),('RX 7600','RX 7600'),
                               ('i5 6600','Intel i5-6600'),('i5-9600K','Intel i5-9600K')]:
            with self.subTest(title=title): self.assertEqual(matcher.match_model(title),expected)
        for title in ['5600','7600','Nokia BV6600','RX 66000','NVIDIA Geforce 6600 LE 256 MB','Intelcore 2 duo 6600 2.4ghz']:
            self.assertIsNone(matcher.match_model(title))

    def test_ram_not_gpu_or_cpu(self):
        result=matcher.classify('Kit RAM DDR5 2x16GB 7600MHz','Compativel com Ryzen CPU')
        self.assertEqual(result[0],'RAM')
        self.assertIn('32GB 2x16GB 7600',result[1])
        self.assertIsNotNone(item(title='Kit RAM DDR4 2x8GB 3200MHz'))

    def test_skip_pc_keep_old_and_untested(self):
        for title in ['PC gaming completo RTX 2060','Ryzen 3600 + RTX 2060','kit Ryzen 5600 motherboard','Ventoinha RTX 2060','RTX 2060 + RX 6600','Bateria HP 6600 mAh','MSI X370 Gaming Plus Ryzen 5000']:
            self.assertIsNone(item(title=title))
        self.assertIsNotNone(item(title='GTX 1060 6GB por testar'))
        self.assertFalse(matcher.is_defective('RTX 2060 sem defeitos'))
        self.assertTrue(matcher.is_defective('6600 avariada'))
        self.assertTrue(matcher.is_defective('RTX 2060 - Para reparação ou peças'))
        self.assertTrue(matcher.is_defective('N/Funcional RX6600'))
        self.assertIsNone(matcher.classify('Processador T9400', 'Alternativas: i3-2100 e Ryzen 5600'))


class Storage(unittest.TestCase):
    def setUp(self): self.db=Database(':memory:')
    def tearDown(self): self.db.conn.close()

    def test_repeat_id_and_price_history(self):
        r=self.db.start_run()
        self.assertEqual(self.db.upsert_listing(item(),r),'new')
        self.assertEqual(self.db.upsert_listing(item(),r),'unchanged')
        changed=item(price=90,location='Porto');changed['url']='https://www.olx.pt/d/anuncio/example.html'
        self.assertEqual(self.db.upsert_listing(changed,r),'changed')
        self.assertEqual(self.db.conn.execute('SELECT COUNT(*) FROM listings').fetchone()[0],1)
        self.assertEqual(self.db.conn.execute('SELECT COUNT(*) FROM price_history').fetchone()[0],2)
        saved=self.db.active_listings()[0]
        self.assertEqual(saved['location'],'Porto');self.assertEqual(saved['previous_price'],100)

    def test_median_unique_ads_condition_and_flags(self):
        for i,price in enumerate([100,150,160,170]):
            self.db.upsert_listing(item(str(i),price))
        for _ in range(5): self.db.upsert_listing(item('0',100))
        broken=item('broken',20);broken['is_defective']=True;self.db.upsert_listing(broken)
        new=item('new',400);new['condition']='new';self.db.upsert_listing(new)
        stats=self.db.model_stats()[('RX 6600','used')]
        self.assertEqual(stats,{'median':155,'count':4})
        self.assertEqual([d['listing_id'] for d in self.db.find_deals()],['0'])

    def test_report_without_median_and_escaping(self):
        self.db.upsert_listing(item(title='6600 <script>alert(1)</script>'))
        with tempfile.TemporaryDirectory() as d:
            text=Path(report.generate(self.db,d)).read_text()
        self.assertIn('Espinho, Aveiro',text)
        self.assertIn('Cheapest 10',text)
        self.assertIn('&lt;script&gt;',text)
        self.assertNotIn('<script>alert(1)',text)

    def test_legacy_migration(self):
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/'legacy.db');c=sqlite3.connect(path);c.executescript(SCHEMA)
            c.execute("INSERT INTO listings (site,listing_id,title,price,model,condition,first_seen,last_seen) VALUES ('olx','old','RTX 2060',100,'RTX 2060','used','2026-09-11','2026-09-11')")
            c.commit();c.close();db=Database(path)
            self.assertEqual(db.conn.execute("SELECT category FROM listings").fetchone()[0],'GPU')
            db.conn.close()


class Scraping(unittest.TestCase):
    def offer(self,id):
        return {'id':id,'title':'Radeon XFX 6600 8GB','params':[{'key':'price','value':{'value':100,'currency':'EUR'}}],
                'location':{'city':{'name':'Espinho'},'region':{'name':'Aveiro'}}}

    def test_location_and_bad_currency(self):
        scraper=OlxScraper();raw=self.offer(1)
        self.assertEqual(scraper.parse_offer(raw)['location'],'Espinho, Aveiro')
        raw['params'][0]['value']['currency']='USD';self.assertIsNone(scraper.parse_offer(raw))

    def test_failed_page_preserves_earlier_results(self):
        scraper=OlxScraper()
        with patch.object(config,'PAGE_SIZE',1),patch.object(config,'MAX_PAGES_PER_QUERY',2),patch.object(scraper,'throttle'),patch.object(scraper,'get_json',side_effect=[{'data':[self.offer(1)]},ValueError('bad page')]):
            results=scraper.scrape(['6600'])
        self.assertEqual(len(results),1);self.assertEqual(scraper.failed,1)

    def test_repeat_page_not_success(self):
        scraper=OlxScraper()
        with patch.object(config,'PAGE_SIZE',1),patch.object(config,'MAX_PAGES_PER_QUERY',2),patch.object(scraper,'throttle'),patch.object(scraper,'get_json',return_value={'data':[self.offer(1)]}):
            results=scraper.scrape(['6600'])
        self.assertEqual(len(results),1);self.assertEqual(scraper.failed,1)
        self.assertIn('Repeated page',' '.join(scraper.diagnostics))


if __name__=='__main__': unittest.main()
