#!/usr/bin/env python3
"""Replay explicitly labelled fixture listings against the actual configured models."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from classification import ClassificationPipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixtures', nargs='+', help='JSON files: list or object with cases, each containing listing')
    parser.add_argument('--out', required=True)
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    pipeline = ClassificationPipeline()
    results = []
    for name in args.fixtures:
        payload = json.loads(Path(name).read_text())
        if isinstance(payload, dict) and payload.get('fixture_kind') == 'real':
            from scrapers.olx import OlxScraper
            cases = [{'id': Path(name).stem, 'listing': OlxScraper().parse_offer(payload['source_payload']['data']),
                      'provenance': {k: payload[k] for k in ('fixture_kind', 'retrieved_at', 'source_url', 'capture_method')},
                      'expected': {'kind': payload['expected']['sale_kind'], 'eligible': False}}]
        elif isinstance(payload, dict) and payload.get('kind') == 'real_historical_search_index_evidence':
            cases = [{'id': c['listing_id'], 'listing': dict(site='vinted', listing_id=c['listing_id'], title=c['title'],
                      description=c['description_excerpt'] + '\n' + c['condition_excerpt'], price=c['price'], currency=c['currency'],
                      url=c['url'], condition='unknown', images=[]),
                      'provenance': {'type': payload['kind'], 'observed_at': payload['observed_at'], 'retrieval': payload['retrieval']},
                      'expected': {'eligible': False}} for c in payload['cases']]
        else:
            cases = payload if isinstance(payload, list) else payload['cases']
        for case in cases:
            if args.limit and len(results) >= args.limit:
                break
            listing = case['listing']
            result = pipeline.classify(listing)
            expected = case.get('expected', {})
            checks = {}
            for field, value in expected.items():
                actual = result['comparison']['eligible'] if field == 'eligible' else result.get(field)
                checks[field] = actual == value
            results.append({'fixture': name, 'case': case.get('id'), 'provenance': case.get('provenance'),
                            'url': listing.get('url'), 'result': result, 'checks': checks})
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps({'executed_at': datetime.now(timezone.utc).isoformat(),
                'mode': 'actual_model_inference', 'results': results}, ensure_ascii=False, indent=2))
            print(case.get('id'), result['comparison'], result['error'], checks, flush=True)
    return int(any(r['result']['error'] or not all(r['checks'].values()) for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
