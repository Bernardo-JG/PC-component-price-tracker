"""Text-only recognition. Ambiguous bare numbers are left unclassified."""
import re
import unicodedata
import config


def _norm(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text or '')
                   if not unicodedata.combining(c)).lower()


def is_junk(title, price):
    t = _norm(title)
    return (price is None or not config.MIN_PRICE <= price <= config.MAX_PRICE
            or bool(re.search(r'\b(procuro|compro|busco|portatil|laptop|notebook)\b', t))
            or bool(re.search(r'\b(pc|computador|desktop|torre|setup)\b', t)
                    and not re.search(r'\b(para|p/)\s*(pc|computador|desktop)\b', t))
            or bool(re.search(r'\b(bundle|combo|lote|motherboard|placa mae)\b', t))
            or bool(re.search(r'\bkit\b', t) and not re.search(r'\b(ram|ddr[345]|memoria)\b', t))
            or bool(re.match(r'\s*(ventoinhas?|fans?|cooler|dissipador|cabo|suporte|bateria|battery)\b', t))
            or bool(re.search(r'\b(?:[bhz][1-8]\d{2}|[abx][34568]\d{2})[a-z]?\b', t))
            or bool(re.search(r'\b(so caixa|apenas caixa|caixa vazia|empty box|cooler para|waterblock|backplate|suporte para)\b', t)))


def is_defective(title, description=''):
    t = _norm(title + ' ' + description)
    t = re.sub(r'\b(sem|nenhum|nenhuns|nao tem)\s+(defeitos?|problemas?|artefactos?)\b', '', t)
    return bool(re.search(r'\b(avariad\w*|para pecas|para piezas|para reparacao|reparar|n/funcional|nao funcional|nao funciona|nao liga|sem sinal|no signal|artefactos|artifacts|faulty|broken|not working|no funciona)\b', t))


# Full suffix first; all endings have boundaries so 6600 cannot match 6600 XT.
_GPU = []
for name in sorted(config.GPU_MODELS, key=len, reverse=True):
    suffix = re.sub(r'^(RX|RTX|GTX|Arc)\s+', '', name, flags=re.I)
    pattern = r'(?<![a-z0-9])' + r'\s*'.join(map(re.escape, suffix.lower().split())) + r'(?![a-z0-9]|\s*(?:xtx|xt|ti|super|gre)\b)'
    _GPU.append((re.compile(pattern), name))
_AMD = re.compile(r'(?<![a-z0-9])(' + '|'.join(sorted(config.AMD_CPUS, key=len, reverse=True)) + r')(?![a-z0-9])', re.I)


def classify(title, description=''):
    """Return (category, comparison key), or None; never infer from query text."""
    t, d = _norm(title), _norm(description)
    t = re.sub(r'\b(rx|rtx|gtx)(?=\d)', r'\1 ', t)
    d = re.sub(r'\b(rx|rtx|gtx)(?=\d)', r'\1 ', d)
    t = re.sub(r'\bintelcore\b', 'intel core', t)
    text = t + ' ' + d
    gpu_cue = bool(re.search(r'\b(rx|rtx|gtx|radeon|geforce|grafica|gpu|arc)\b', t))
    cpu_cue = bool(re.search(r'\b(ryzen|processador|cpu|intel|core|i[3579]|r[3579])\b', t))
    # A CPU + GPU in the title usually means a PC/bundle, even without "PC".
    if gpu_cue and cpu_cue:
        return None
    if cpu_cue or (not gpu_cue and re.fullmatch(r'\s*\d{4}[a-z0-9]*\s*', t) and re.search(r'\b(ryzen|processador|cpu)\b', d)):
        intel = list(re.finditer(r'\b(i[3579])\s*[- ]?\s*(\d{4,5}\s*(?:kf|ks|k|f|t|s)?)(?![a-z0-9])', t))
        if len(intel)>1:
            return None
        m = intel[0] if intel else None
        if m:
            return 'CPU', 'Intel ' + m[1] + '-' + re.sub(r'\s+', '', m[2]).upper()
        amd = list(_AMD.finditer(t))
        if len(amd)>1:
            return None
        m = amd[0] if amd else None
        if m and ('ryzen' in text or 'intel' not in text):
            return 'CPU', 'Ryzen ' + m[1].upper()
        return None
    # RAM speed numbers (e.g. DDR5 7600) must not become GPU names.
    if re.search(r'\b(ddr[345]|ram|dimm|sodimm)\b', t):
        gen = re.search(r'\bddr\s*([345])\b', text)
        kit = re.search(r'\b(\d{1,2})\s*x\s*(\d{1,3})\s*g(?:b)?\b', t)
        capacity = re.search(r'\b(\d{1,3})\s*g(?:b)?\b', t)
        if not gen or not (kit or capacity):
            return None
        spaced_count = re.search(r'\b(\d{1,2})\s*x\s+mem', t)
        total = int(kit[1])*int(kit[2]) if kit else int(capacity[1]) * (int(spaced_count[1]) if spaced_count else 1)
        layout = f'{kit[1]}x{kit[2]}GB' if kit else (f'{spaced_count[1]}x{capacity[1]}GB' if spaced_count else 'layout unknown')
        speed = re.search(r'\b(1[0368]\d{2}|2[14689]\d{2}|3[026]\d{2}|[45678]\d{3})\s*(?:mhz|mt/s)\b', text)
        if not speed:
            speed = re.search(r'\bddr[345]\s*[- ]\s*([2-8]\d{3})\b', text)
        form = 'SODIMM' if re.search(r'so[- ]?dimm|portatil|laptop', text) else ('DIMM' if re.search(r'\bdimm\b|desktop', text) else 'form unknown')
        return 'RAM', f'DDR{gen[1]} {total}GB {layout} {speed[1] if speed else "speed unknown"} {form}'
    matches = [(pattern, name) for pattern, name in _GPU if pattern.search(t)]
    if len(matches) > 1:
        return None  # Multiple GPU models usually indicate a bundle or seller inventory.
    for pattern, name in matches:
        if pattern.search(t):
            number = re.search(r'\d+', name)[0]
            # 5600/7600/6600 etc. overlap other hardware; only 6600/2060-style
            # GPU shorthand defaults are allowed outside known ambiguous families.
            ambiguous = number in {'5600','5700','6400','6500','6700','6800','7600','7700','7900'} and not re.search(r' (XT|XTX|Ti|Super)$', name)
            if (name.startswith('RX ') and re.search(r'\b(nvidia|geforce|gtx|rtx|intel)\b', t)) or (name.startswith(('RTX ','GTX ')) and re.search(r'\b(radeon|rx)\b', t)):
                return None
            if ambiguous and not gpu_cue and not re.search(r'\b(rx|radeon|grafica|gpu|geforce|rtx|gtx)\b', d):
                return None
            memory = re.search(r'\b(\d{1,2})\s*g(?:b)?\b', t) or re.search(r'\b(\d{1,2})\s*g(?:b)?\b', d)
            # Split models with common memory variants; unknown is a separate cohort.
            variable = {'GTX 1060','RTX 2060','RTX 3060','RTX 3050','RTX 3080','RTX 4060 Ti','RTX 5060 Ti','RX 580','RX 5500 XT','RX 9060 XT','Arc A770'}
            if name in variable:
                name += ' ' + (memory[1] + 'GB' if memory else '(VRAM unknown)')
            return 'GPU', name
    return None


def match_model(title, description=''):
    result = classify(title, description)
    return result[1] if result else None
