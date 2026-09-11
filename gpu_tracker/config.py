"""Central configuration for the GPU deal tracker."""

# ---------------------------------------------------------------------------
# Canonical GPU models
# Each entry: canonical name -> list of regex patterns matched against titles.
# Patterns are matched longest/most-specific first automatically.
# "tier" is a rough performance class used to exclude high-end cards from the
# repair-candidates section.
# ---------------------------------------------------------------------------

NVIDIA_MODELS = {
    "RTX 3060":        {"patterns": [r"rtx\s*3060(?!\s*ti)"], "tier": 1},
    "RTX 3060 Ti":     {"patterns": [r"rtx\s*3060\s*ti"], "tier": 2},
    "RTX 3070":        {"patterns": [r"rtx\s*3070(?!\s*ti)"], "tier": 2},
    "RTX 3070 Ti":     {"patterns": [r"rtx\s*3070\s*ti"], "tier": 3},
    "RTX 3080":        {"patterns": [r"rtx\s*3080(?!\s*ti)"], "tier": 3},
    "RTX 3080 Ti":     {"patterns": [r"rtx\s*3080\s*ti"], "tier": 4},
    "RTX 3090":        {"patterns": [r"rtx\s*3090(?!\s*ti)"], "tier": 5},
    "RTX 3090 Ti":     {"patterns": [r"rtx\s*3090\s*ti"], "tier": 5},
    "RTX 4060":        {"patterns": [r"rtx\s*4060(?!\s*ti)"], "tier": 1},
    "RTX 4060 Ti":     {"patterns": [r"rtx\s*4060\s*ti"], "tier": 2},
    "RTX 4070":        {"patterns": [r"rtx\s*4070(?!\s*(ti|super))"], "tier": 3},
    "RTX 4070 Super":  {"patterns": [r"rtx\s*4070\s*super"], "tier": 3},
    "RTX 4070 Ti":     {"patterns": [r"rtx\s*4070\s*ti(?!\s*super)"], "tier": 4},
    "RTX 4070 Ti Super": {"patterns": [r"rtx\s*4070\s*ti\s*super"], "tier": 4},
    "RTX 4080":        {"patterns": [r"rtx\s*4080(?!\s*super)"], "tier": 5},
    "RTX 4080 Super":  {"patterns": [r"rtx\s*4080\s*super"], "tier": 5},
    "RTX 4090":        {"patterns": [r"rtx\s*4090"], "tier": 6},
    "RTX 5060":        {"patterns": [r"rtx\s*5060(?!\s*ti)"], "tier": 2},
    "RTX 5060 Ti":     {"patterns": [r"rtx\s*5060\s*ti"], "tier": 2},
    "RTX 5070":        {"patterns": [r"rtx\s*5070(?!\s*ti)"], "tier": 3},
    "RTX 5070 Ti":     {"patterns": [r"rtx\s*5070\s*ti"], "tier": 4},
    "RTX 5080":        {"patterns": [r"rtx\s*5080"], "tier": 5},
    "RTX 5090":        {"patterns": [r"rtx\s*5090"], "tier": 6},
}

AMD_MODELS = {
    "RX 6700 XT":  {"patterns": [r"rx\s*6700\s*xt", r"6700\s*xt"], "tier": 2},
    "RX 6750 XT":  {"patterns": [r"rx\s*6750\s*xt", r"6750\s*xt"], "tier": 2},
    "RX 6800":     {"patterns": [r"rx\s*6800(?!\s*xt)"], "tier": 3},
    "RX 6800 XT":  {"patterns": [r"rx\s*6800\s*xt", r"6800\s*xt"], "tier": 4},
    "RX 6900 XT":  {"patterns": [r"rx\s*6900\s*xt", r"6900\s*xt"], "tier": 4},
    "RX 6950 XT":  {"patterns": [r"rx\s*6950\s*xt", r"6950\s*xt"], "tier": 5},
    "RX 7600":     {"patterns": [r"rx\s*7600(?!\s*xt)"], "tier": 1},
    "RX 7600 XT":  {"patterns": [r"rx\s*7600\s*xt"], "tier": 1},
    "RX 7700 XT":  {"patterns": [r"rx\s*7700\s*xt"], "tier": 2},
    "RX 7800 XT":  {"patterns": [r"rx\s*7800\s*xt"], "tier": 3},
    "RX 7900 GRE": {"patterns": [r"rx\s*7900\s*gre", r"7900\s*gre"], "tier": 4},
    "RX 7900 XT":  {"patterns": [r"rx\s*7900\s*xt(?!x)", r"7900\s*xt(?!x)"], "tier": 4},
    "RX 7900 XTX": {"patterns": [r"rx\s*7900\s*xtx", r"7900\s*xtx"], "tier": 5},
    "RX 9060 XT":  {"patterns": [r"rx\s*9060\s*xt"], "tier": 2},
    "RX 9070":     {"patterns": [r"rx\s*9070(?!\s*xt)"], "tier": 3},
    "RX 9070 XT":  {"patterns": [r"rx\s*9070\s*xt"], "tier": 4},
}

# Older models tracked ONLY as repair candidates (cheap, fixable cards).
REPAIR_ONLY_MODELS = {
    "GTX 1060":    {"patterns": [r"gtx\s*1060"], "tier": 0},
    "GTX 1070":    {"patterns": [r"gtx\s*1070(?!\s*ti)", r"gtx\s*1070\s*ti"], "tier": 0},
    "GTX 1080":    {"patterns": [r"gtx\s*1080(?!\s*ti)"], "tier": 1},
    "GTX 1080 Ti": {"patterns": [r"gtx\s*1080\s*ti"], "tier": 1},
    "GTX 1660":    {"patterns": [r"gtx\s*1660"], "tier": 0},
    "RTX 2060":    {"patterns": [r"rtx\s*2060"], "tier": 1},
    "RTX 2070":    {"patterns": [r"rtx\s*2070"], "tier": 1},
    "RTX 2080":    {"patterns": [r"rtx\s*2080"], "tier": 2},
    "RX 580":      {"patterns": [r"rx\s*580"], "tier": 0},
    "RX 5600 XT":  {"patterns": [r"rx\s*5600"], "tier": 0},
    "RX 5700":     {"patterns": [r"rx\s*5700(?!\s*xt)"], "tier": 1},
    "RX 5700 XT":  {"patterns": [r"rx\s*5700\s*xt", r"5700\s*xt"], "tier": 1},
}

ALL_MODELS = {**NVIDIA_MODELS, **AMD_MODELS, **REPAIR_ONLY_MODELS}

# Repair candidates: anything matched + defective, as long as tier <= this.
# Tier 4+ (e.g. 4080, 7900 XTX, 3090) excluded - too risky/expensive to fix.
REPAIR_MAX_TIER = 3

# ---------------------------------------------------------------------------
# Search queries
# ---------------------------------------------------------------------------

MAIN_QUERIES = [
    "rtx 3060", "rtx 3070", "rtx 3080", "rtx 3090",
    "rtx 4060", "rtx 4070", "rtx 4080", "rtx 4090",
    "rtx 5060", "rtx 5070", "rtx 5080", "rtx 5090",
    "rx 6700", "rx 6750", "rx 6800", "rx 6900", "rx 6950",
    "rx 7600", "rx 7700", "rx 7800", "rx 7900",
    "rx 9060", "rx 9070",
]

# Extra queries run only on second-hand sites, to surface repair candidates.
REPAIR_QUERIES = [
    "gráfica avariada", "gpu avariada", "gráfica para peças",
    "gtx 1080", "rtx 2070", "rx 5700",
]

# ---------------------------------------------------------------------------
# Text classification
# ---------------------------------------------------------------------------

DEFECT_TERMS = [
    "avariad", "para peças", "para pecas", "p/ peças", "nao liga", "não liga",
    "no signal", "sem sinal", "artefactos", "artefatos", "artifacts",
    "defeito", "defekt", "faulty", "for parts", "not working", "broken",
    "ecrã preto", "ecra preto", "black screen", "reparar", "precisa reparação",
    "averiada", "no funciona", "para piezas", "estropeada",
]

# Listings containing these are discarded entirely.
JUNK_TERMS = [
    "procuro", "compro", "busco", "caixa vazia", "só caixa", "so caixa",
    "empty box", "apenas caixa", "backplate", "cabo ", "suporte",
    "water block", "waterblock", "cooler para", "ventoinha",
    "pc gaming completo", "pc completo", "setup completo", "torre completa",
    "portátil", "portatil", "laptop", "notebook",
]

# Prices outside this range are ignored (junk / scams / bundles).
MIN_PRICE = 30.0
MAX_PRICE = 4000.0

# ---------------------------------------------------------------------------
# Deal logic
# ---------------------------------------------------------------------------

DEAL_THRESHOLD = 0.80      # deal if price <= 80% of median used price
STATS_WINDOW_DAYS = 45     # rolling window for median computation
MIN_SAMPLES_FOR_STATS = 4  # minimum used listings before medians are trusted

# ---------------------------------------------------------------------------
# Scraper behaviour
# ---------------------------------------------------------------------------

ENABLED_SITES = ["vinted", "olx", "wallapop", "pcdiga", "amazon"]
SECONDHAND_SITES = {"vinted", "olx", "wallapop"}
RETAIL_SITES = {"pcdiga", "amazon"}

REQUEST_DELAY_RANGE = (2.0, 5.0)   # random delay between requests, seconds
REQUEST_TIMEOUT = 25

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

DB_PATH = "gpu_tracker.db"
REPORTS_DIR = "reports"
