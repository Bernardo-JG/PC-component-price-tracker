"""Synthetic model doubles: validate safeguards, never claim real inference accuracy."""
import copy
import json
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from classification import ClassificationPipeline, enrich
from classification.schema import empty_result, decode
from classification.client import ModelClient
from db import Database


def listing(**overrides):
    return dict(dict(site='olx', listing_id='1', title='Sapphire RX 6600 8GB',
        description='Placa gráfica usada, testada e a funcionar sem problemas.',
        price=100.,currency='EUR',condition='used',images=[],url='https://www.olx.pt/1/'), **overrides)


def response():
    r=empty_result()
    r.update(kind='component',category='GPU',brand='Sapphire',model='RX 6600',functional_condition='working',abstain=False)
    r['specifications']['vram_gb']='8'
    for field, quote in [('kind','Placa gráfica'),('category','Placa gráfica'),('brand','Sapphire'),('model','RX 6600'),('specifications.vram_gb','8GB'),('functional_condition','testada e a funcionar sem problemas')]:
        r['evidence'].append(dict(field=field,source='text',quote=quote,image_index=None))
    return r


class FakeClient:
    model='synthetic-double'
    visual_enabled=False
    def __init__(self,result=None): self.result=result if result is not None else response(); self.visual_calls=0
    def text(self,*args): return json.dumps(self.result)
    def visual(self,*args): self.visual_calls+=1; return json.dumps(self.visual_result)


class PipelineTests(unittest.TestCase):
    def test_working_exact_evidence(self):
        r=ClassificationPipeline(FakeClient()).classify(listing())
        self.assertTrue(r['comparison']['eligible'],r)
        self.assertNotIn('price',r)

    def test_invalid_json_and_extra_fields_fail_closed(self):
        for bad in ('{}','not json',json.dumps(dict(response(),price=10))):
            client=FakeClient()
            client.text=lambda *args: bad
            r=ClassificationPipeline(client).classify(listing())
            self.assertFalse(r['comparison']['eligible']); self.assertIsNotNone(r['error'])

    def test_hallucinated_quote_or_value_rejected(self):
        for field,value in [('model','RTX 4090'),('brand','ASUS')]:
            r=response(); r[field]=value
            with self.assertRaises(ValueError): decode(json.dumps(r),listing())
        r=response();r['evidence'][0]['quote']='Invented quotation'
        with self.assertRaises(ValueError):decode(json.dumps(r),listing())

    def test_guards_override_false_positive_model(self):
        for text in ['cooler para RTX 3080', 'caixa de RTX 2060','procuro RX 6600','bundle','avariada','por testar']:
            with self.subTest(text=text):
                l=listing(title=text+' '+listing()['title'])
                r=ClassificationPipeline(FakeClient()).classify(l)
                self.assertFalse(r['comparison']['eligible']); self.assertIsNotNone(r['rule_guard'])

    def test_unknown_untested_defective_not_pooled(self):
        for condition in ['unknown','untested','defective']:
            r=response();r['functional_condition']=condition
            r['evidence']=[e for e in r['evidence'] if e['field']!='functional_condition']
            if condition!='unknown':
                r['evidence'].append(dict(field='functional_condition',source='text',quote='untested' if condition=='untested' else 'avariada',image_index=None))
            l=listing(description=listing()['description']+' untested avariada')
            out=ClassificationPipeline(FakeClient(r)).classify(l)
            self.assertFalse(out['comparison']['eligible'])

    def test_spec_number_cannot_come_from_model_digits(self):
        r=response();r['evidence'][-2]['quote']='RX 6600';r['specifications']['vram_gb']='6'
        with self.assertRaises(ValueError):decode(json.dumps(r),listing())

    def test_short_quote_cannot_hide_portuguese_negation(self):
        r=response();r['evidence'][-1]['quote']='funcionar'
        l=listing(description='Placa gráfica. Não está a funcionar.')
        out=ClassificationPipeline(FakeClient(r)).classify(l)
        self.assertFalse(out['comparison']['eligible'])

    def test_model_suffix_cannot_be_dropped(self):
        r=response();r['evidence'][3]['quote']='RX 6600 XT'
        with self.assertRaises(ValueError):decode(json.dumps(r),listing(title='Sapphire RX 6600 XT 8GB'))

    def test_missing_specs_excluded(self):
        r=response();r['specifications']['vram_gb']=None
        out=ClassificationPipeline(FakeClient(r)).classify(listing())
        self.assertEqual(out['comparison']['exclusion_reason'],'comparison_specifications_unknown')

    def test_visual_only_when_necessary_and_no_text_override(self):
        client=FakeClient();client.visual_enabled=True
        out=ClassificationPipeline(client).classify(listing(images=['https://images.olxcdn.com/a.jpg']))
        self.assertEqual(client.visual_calls,0)
        r=response();r['needs_visual']=True;r['specifications']['vram_gb']=None
        client=FakeClient(r);client.visual_enabled=True
        client.visual_result=copy.deepcopy(r);client.visual_result['model']='RTX 4090'
        client.visual_result['evidence']=[e for e in r['evidence'] if e['field']!='model']+[dict(field='model',source='image',quote='RTX 4090',image_index=0)]
        out=ClassificationPipeline(client).classify(listing(images=['https://images.olxcdn.com/a.jpg']))
        self.assertFalse(out['comparison']['eligible']);self.assertIn('contradicts',out['error'])

    def test_visual_abstention_does_not_fill_unknown(self):
        r=response();r['needs_visual']=True;r['specifications']['vram_gb']=None
        client=FakeClient(r);client.visual_enabled=True;client.visual_result=empty_result()
        out=ClassificationPipeline(client).classify(listing(images=['https://images.olxcdn.com/a.jpg']))
        self.assertEqual(out['visual_status'],'abstained');self.assertFalse(out['comparison']['eligible'])

    def test_visual_supplement_preserves_text_and_condition(self):
        r=response();r['needs_visual']=True;r['specifications']['vram_gb']=None
        client=FakeClient(r);client.visual_enabled=True;v=copy.deepcopy(r)
        v['specifications']['vram_gb']='8'
        v['evidence']=[e for e in v['evidence'] if e['field']!='specifications.vram_gb']+[dict(field='specifications.vram_gb',source='image',quote='8GB',image_index=0)]
        client.visual_result=v
        out=ClassificationPipeline(client).classify(listing(images=['https://images.olxcdn.com/a.jpg']))
        self.assertTrue(out['comparison']['eligible'],out);self.assertEqual(out['visual_status'],'supplemented')

    def test_queue_across_client_instances(self):
        active=maximum=0
        def run():
            nonlocal active,maximum
            with ModelClient().slot():
                active+=1;maximum=max(maximum,active);time.sleep(.02);active-=1
        # Use an isolated lock path so a live evaluation cannot block unit tests.
        lock = tempfile.NamedTemporaryFile()
        self.addCleanup(lock.close)
        env = patch.dict('os.environ', {'TRACKER_INFERENCE_LOCK': lock.name})
        env.start(); self.addCleanup(env.stop)
        threads=[threading.Thread(target=run) for _ in range(4)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(maximum,1)

    def test_text_always_unloads_even_on_failure(self):
        client=ModelClient()
        with tempfile.NamedTemporaryFile() as lock:
            client.lock_path = lock.name
        with patch.object(client,'visual_running',return_value=False),patch('classification.client.request_json',side_effect=[{'models':[]},TimeoutError('timeout'),{}, {'models':[]}]) as req:
            with self.assertRaises(TimeoutError):client.text(listing(),[])
        self.assertTrue(req.call_args_list[2].args[0].endswith('/api/generate'))
        self.assertEqual(req.call_args_list[2].args[1]['keep_alive'],0)

    def test_medians_require_classification_and_separate_cohorts(self):
        db=Database(':memory:')
        try:
            p=ClassificationPipeline(FakeClient())
            for i,price in enumerate([100,150,160,170]):
                l=listing(listing_id=str(i),price=price);db.upsert_listing(enrich(l,p.classify(l)))
            db.upsert_listing(listing(listing_id='legacy',price=5))
            other=listing(site='vinted',listing_id='v',price=10);db.upsert_listing(enrich(other,p.classify(other)))
            stats=db.model_stats()
            self.assertEqual(sorted(v['count'] for v in stats.values()),[1,4])
            self.assertEqual([d['listing_id'] for d in db.find_deals()],['0'])
            db.upsert_listing(listing(listing_id='0',price=100))
            self.assertFalse(db.find_deals())
        finally:db.conn.close()
