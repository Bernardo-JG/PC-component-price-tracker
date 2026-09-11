"""Classification of raw listing titles/descriptions into canonical models,
defective flags and junk."""

import re
import unicodedata

import config


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


# Build a flat list of (compiled_pattern, canonical_name), most specific first.
_COMPILED = []
for name, info in config.ALL_MODELS.items():
    for pat in info["patterns"]:
        _COMPILED.append((re.compile(pat, re.IGNORECASE), name, len(pat)))
# Longer patterns first so "3060 ti" wins over "3060", "7900 xtx" over "7900 xt".
_COMPILED.sort(key=lambda t: t[2], reverse=True)

_DEFECT_TERMS = [_norm(t) for t in config.DEFECT_TERMS]
_JUNK_TERMS = [_norm(t) for t in config.JUNK_TERMS]


def match_model(title: str) -> str | None:
    """Return canonical model name for a listing title, or None."""
    t = _norm(title)
    best = None
    for pattern, name, _ in _COMPILED:
        if pattern.search(t):
            best = name
            break
    return best


def is_defective(title: str, description: str = "") -> bool:
    text = _norm(f"{title} {description}")
    return any(term in text for term in _DEFECT_TERMS)


def is_junk(title: str, price: float | None) -> bool:
    t = _norm(title)
    if any(term in t for term in _JUNK_TERMS):
        return True
    if price is None:
        return True
    if not (config.MIN_PRICE <= price <= config.MAX_PRICE):
        return True
    return False


def is_repair_only_model(model: str) -> bool:
    return model in config.REPAIR_ONLY_MODELS


def is_repair_candidate(model: str, defective: bool) -> bool:
    """Defective + not too high-end = interesting to fix."""
    if not defective:
        return False
    info = config.ALL_MODELS.get(model)
    if info is None:
        return False
    return info["tier"] <= config.REPAIR_MAX_TIER
