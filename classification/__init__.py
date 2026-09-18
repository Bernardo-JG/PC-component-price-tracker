"""Shared rules → text → optional visual pipeline; conservative price eligibility."""
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import matcher
from .schema import decode, empty_result
from .client import ModelClient

VERSION = '1'


def candidates(listing):
    text = listing['title'] + '\n' + listing.get('description', '')
    found = set()
    for part in (listing['title'], *re.split(r'[\n.;]', text)):
        result = matcher.classify(part)
        if result:
            found.add(result)
    return [{'category': category, 'model': model} for category, model in sorted(found)]


def guards(listing):
    title = matcher._norm(listing['title'])
    text = matcher._norm(listing['title'] + '\n' + listing.get('description', ''))
    if re.search(r'\b(procuro|compro|busco|wanted|looking for)\b', title):
        return 'wanted'
    if re.search(r'\b(cooler|ventoinha|dissipador|waterblock|backplate|caixa)\s+(?:para|de|da|do)\s+(?:uma?\s+)?(?:rtx|rx|gtx|grafica)', text) or re.search(r'\b(apenas|so|somente)\s+(?:a\s+)?caixa\b|\bcaixa vazia\b', text):
        return 'accessory'
    if re.search(r'\b(bundle|combo|lote|pc completo|computador completo)\b', text):
        return 'bundle'
    if re.search(r'\bnao\s+(?:(?:esta|e|ficou|estava)\s+)?(?:a\s+|totalmente\s+)?(?:funciona\w*|operacional)\b', text):
        return 'defective'
    if re.search(r'\b(?:nao sei se|desconheco se|sem saber se|talvez)\s+(?:esta a |esta |e )?(?:funciona\w*|operacional)\b', text):
        return 'uncertain_condition'
    if matcher.is_defective(listing['title'], listing.get('description', '')):
        return 'defective'
    if re.search(r'\b(por testar|nao testad\w*|sem testar|untested)\b', text):
        return 'untested'
    return None


def comparison(result, listing, guard=None):
    reason = None
    if result['abstain']:
        reason = 'model_abstained'
    elif guard:
        reason = 'explicit_' + guard
    elif result['kind'] != 'component':
        reason = result['kind']
    elif not result['model'] or not result['category']:
        reason = 'identity_unknown'
    elif result['functional_condition'] != 'working':
        reason = 'condition_' + result['functional_condition']
    elif listing.get('condition') not in ('new', 'used'):
        reason = 'sale_condition_unknown'
    elif listing.get('currency') != 'EUR' or type(listing.get('price')) not in (float, int) or not math.isfinite(listing['price']) or listing['price'] <= 0:
        reason = 'invalid_observed_price'
    else:
        required = {'GPU': ['vram_gb'], 'CPU': [], 'RAM': ['memory_type', 'capacity_gb', 'layout', 'speed_mts', 'form_factor']}[result['category']]
        if any(result['specifications'][key] is None for key in required):
            reason = 'comparison_specifications_unknown'
    key = None
    if reason is None:
        # Separate platforms, currency, sale and functional condition; never pool unknown variants.
        key = json.dumps([listing['site'], listing['currency'], result['category'],
                          re.sub(r'\s+', ' ', result['model'].strip().casefold()),
                          {k: v.casefold().strip() if v else None for k, v in result['specifications'].items()},
                          listing['condition'], result['functional_condition']], sort_keys=True)
    return {'eligible': reason is None, 'exclusion_reason': reason, 'key': key}


class ClassificationPipeline:
    def __init__(self, client=None):
        self.client = client if client is not None else ModelClient()

    def classify(self, listing):
        result = empty_result()
        error = None
        visual_status = 'not_needed'
        extracted = candidates(listing)
        guard = guards(listing)
        try:
            if len(listing['title']) + len(listing.get('description', '')) > 18000:
                raise ValueError('Advertisement exceeds input limit; manual review required')
            result = decode(self.client.text(listing, extracted), listing)
            required = {'GPU': ['vram_gb'], 'CPU': [], 'RAM': ['memory_type', 'capacity_gb', 'layout', 'speed_mts', 'form_factor']}.get(result['category'], [])
            missing = not result['model'] or not result['category'] or any(result['specifications'][k] is None for k in required)
            if result['needs_visual'] and missing and result['kind'] in ('component', 'ambiguous') and not guard:
                visual_status = 'unavailable'
                if self.client.visual_enabled and listing.get('images'):
                    # Pass only actually supplied image indices to validation.
                    visual_listing = dict(listing, images=listing['images'][:2])
                    visual = decode(self.client.visual(visual_listing, result), visual_listing, allow_images=True)
                    if visual['abstain']:
                        visual_status = 'abstained'
                    else:
                        merged = copy.deepcopy(result)
                        for field in ('category', 'brand', 'model'):
                            if result[field] is None and visual[field] is not None:
                                merged[field] = visual[field]
                                merged['evidence'].extend(e for e in visual['evidence'] if e['field'] == field)
                            elif visual[field] is not None and result[field] != visual[field]:
                                raise ValueError('Visual identity contradicts explicit text')
                        for field, value in visual['specifications'].items():
                            if result['specifications'][field] is None and value is not None:
                                merged['specifications'][field] = value
                                merged['evidence'].extend(e for e in visual['evidence'] if e['field'] == 'specifications.' + field)
                            elif value is not None and result['specifications'][field] != value:
                                raise ValueError('Visual specification contradicts explicit text')
                        # Visual may supplement identity, never promote ambiguous sales or change condition.
                        result = decode(json.dumps(merged), visual_listing, allow_images=True)
                        visual_status = 'supplemented'
            cmp = comparison(result, listing, guard)
        except Exception as exc:
            error = f'{type(exc).__name__}: {exc}'
            cmp = {'eligible': False, 'exclusion_reason': 'classification_error', 'key': None}
        result.update(schema_version=VERSION, comparison=cmp, error=error, rule_candidates=extracted,
                      rule_guard=guard, visual_status=visual_status,
                      text_model=getattr(self.client, 'model', 'test-double'),
                      classified_at=datetime.now(timezone.utc).isoformat(),
                      input_sha256=hashlib.sha256(json.dumps(listing, sort_keys=True, ensure_ascii=False).encode()).hexdigest())
        return result


def enrich(listing, result):
    return dict(listing, classification=result, category=result['category'] or '', model=result['model'] or 'Unknown',
                is_defective=result['functional_condition'] == 'defective' or result.get('rule_guard') == 'defective')
