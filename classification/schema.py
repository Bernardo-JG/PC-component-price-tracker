"""Versioned, closed model response contract; prices never come from a model."""
import json
import re
import unicodedata

SPEC_FIELDS = ('vram_gb', 'memory_type', 'capacity_gb', 'layout', 'speed_mts', 'form_factor')
NULL_STRING = {'type': ['string', 'null']}
SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string', 'enum': ['component', 'accessory', 'bundle', 'wanted', 'ambiguous']},
        'category': {'enum': ['GPU', 'CPU', 'RAM', None]},
        'brand': NULL_STRING, 'model': NULL_STRING,
        'specifications': {'type': 'object', 'additionalProperties': False,
                           'properties': {k: NULL_STRING for k in SPEC_FIELDS}, 'required': list(SPEC_FIELDS)},
        'functional_condition': {'enum': ['unknown', 'untested', 'working', 'defective']},
        'evidence': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                    'properties': {'field': {'type': 'string'}, 'source': {'enum': ['text', 'image']},
                                   'quote': {'type': 'string'}, 'image_index': {'type': ['integer', 'null']}},
                    'required': ['field', 'source', 'quote', 'image_index']}},
        'needs_visual': {'type': 'boolean'}, 'abstain': {'type': 'boolean'},
    },
}
SCHEMA['required'] = list(SCHEMA['properties'])


def empty_result():
    return dict(kind='ambiguous', category=None, brand=None, model=None,
                specifications=dict.fromkeys(SPEC_FIELDS), functional_condition='unknown',
                evidence=[], needs_visual=False, abstain=True)


def norm(value):
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in unicodedata.normalize('NFKD', value.lower())
                                        if not unicodedata.combining(c)))


def _check(value, schema, path='response'):
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{path}: invalid enum')
    types = schema.get('type', [])
    if isinstance(types, str):
        types = [types]
    actual = ('null' if value is None else 'boolean' if type(value) is bool else
              'integer' if type(value) is int else 'string' if isinstance(value, str) else
              'object' if isinstance(value, dict) else 'array' if isinstance(value, list) else 'invalid')
    if types and actual not in types:
        raise ValueError(f'{path}: invalid type')
    if actual == 'object':
        if set(value) != set(schema.get('required', [])):
            raise ValueError(f'{path}: missing or extra fields')
        for k, v in value.items():
            _check(v, schema['properties'][k], path + '.' + k)
    elif actual == 'array':
        if len(value) > 40:
            raise ValueError('Too much evidence')
        for v in value:
            _check(v, schema['items'], path)
    elif actual == 'string' and (not value.strip() or len(value) > 2000):
        raise ValueError(f'{path}: empty/oversize string')


def decode(raw, listing, allow_images=False):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError('Duplicate JSON key')
            out[k] = v
        return out
    result = json.loads(raw, object_pairs_hook=pairs)
    _check(result, SCHEMA)
    text = listing['title'] + '\n' + listing.get('description', '')
    claims = {k: result[k] for k in ('kind', 'category', 'brand', 'model', 'functional_condition')}
    claims.update({'specifications.' + k: v for k, v in result['specifications'].items()})
    evidence = {}
    for e in result['evidence']:
        field = e['field']
        if field not in claims:
            raise ValueError('Unknown evidence field')
        if e['source'] == 'text':
            if e['image_index'] is not None or e['quote'] not in text:
                raise ValueError('Text evidence is not an exact advertisement excerpt')
        else:
            index = e['image_index']
            if not allow_images or type(index) is not int or not 0 <= index < len(listing.get('images', [])):
                raise ValueError('Image evidence has no supplied image')
            if field == 'functional_condition':
                raise ValueError('Images cannot establish functional condition')
        evidence.setdefault(field, []).append(e)
    for field, value in claims.items():
        if value is None or value in ('unknown', 'ambiguous'):
            continue
        if field not in evidence:
            raise ValueError(f'Unsupported claim: {field}')
        if field in ('brand', 'model') or field.startswith('specifications.'):
            # Require literal identification; no knowledge-based specifications.
            def supports(quote):
                if field in ('specifications.vram_gb', 'specifications.capacity_gb', 'specifications.speed_mts'):
                    unit = r'(?:mhz|mt/s)' if field.endswith('speed_mts') else r'g(?:b)?'
                    return bool(re.fullmatch(r'\d+(?:\.\d+)?', value) and re.search(
                        r'(?<![\d.])' + re.escape(value) + r'\s*' + unit + r'\b', quote, re.I))
                if field == 'model':
                    tokens = re.findall(r'[a-z]+|[0-9]+', value.lower())
                    pattern = r'(?<![a-z0-9])' + r'\s*[- ]?\s*'.join(map(re.escape, tokens)) + r'(?![a-z0-9])'
                    pattern += r'(?!\s*(?:ti|super|xtx|xt|gre)\b)'
                    return bool(tokens and re.search(pattern, quote, re.I))
                return norm(value) in norm(quote)
            if not any(supports(e['quote']) for e in evidence[field]):
                raise ValueError(f'Value absent from evidence: {field}')
    condition = result['functional_condition']
    if condition != 'unknown':
        condition_text = ' '.join(e['quote'] for e in evidence.get('functional_condition', []) if e['source'] == 'text')
        patterns = {
            'working': r'funciona|funcionar|funcionamento|funcional|working|tested|testad|operacional|fonctionne',
            'untested': r'por testar|sem testar|n[aã]o testad|untested|not tested|non test',
            'defective': r'avariad|defeito|n[aã]o (?:(?:est[aá]|[ée]) (?:a |totalmente )?)?(?:funciona|liga|d[aá])|sem (?:sinal|imagem)|pe[çc]as|repara|artefact|artifact|broken|faulty|not working|defect|no funciona',
        }
        if not re.search(patterns[condition], condition_text, re.I):
            raise ValueError('Functional condition lacks explicit supporting wording')
        if condition == 'working' and re.search(r'n[aã]o|not |untested|por testar|avariad|broken|faulty', condition_text, re.I):
            raise ValueError('Negated/conflicting working evidence')
    return result
