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

# Older cards remain ordinary candidates, whether tested or not.
EXTRA_GPUS = ["GTX 1050", "GTX 1050 Ti", "GTX 1060", "GTX 1070", "GTX 1070 Ti",
              "GTX 1080", "GTX 1080 Ti", "GTX 1650", "GTX 1650 Super",
              "GTX 1660", "GTX 1660 Super", "GTX 1660 Ti", "RTX 2060", "RTX 3050",
              "RTX 2060 Super", "RTX 2070", "RTX 2070 Super", "RTX 2080",
              "RTX 2080 Super", "RTX 2080 Ti", "RX 570", "RX 580", "RX 590",
              "RX 5500 XT", "RX 5600 XT", "RX 5700", "RX 5700 XT",
              "RX 6400", "RX 6500 XT", "RX 6600", "RX 6600 XT", "RX 6650 XT",
              "RX 6700", "Arc A380", "Arc A580", "Arc A750", "Arc A770",
              "Arc B570", "Arc B580"]
GPU_MODELS = sorted(set(NVIDIA_MODELS) | set(AMD_MODELS) | set(EXTRA_GPUS))
AMD_CPUS = """1200 1300X 1400 1500X 1600 1600AF 1700 1700X 1800X
2200G 2400G 2600 2600X 2700 2700X 3100 3200G 3300X 3400G 3500X 3600
3600X 3600XT 3700X 3800X 3900X 3950X 4100 4500 4600G 5500 5500GT
5600 5600G 5600GT 5600X 5700 5700G 5700X 5700X3D 5800X 5800X3D 5900X
5950X 7500F 7600 7600X 7700 7700X 7800X3D 7900 7900X 7900X3D 7950X
7950X3D 8400F 8500G 8600G 8700F 8700G 9600X 9700X 9800X3D 9900X 9950X""".split()

# Broad component searches cover shorthand and descriptions; targeted queries
# improve coverage for popular models. Change these freely.
MAIN_QUERIES = ["placa grafica", "gpu", "6600", "2060", "5700", "1660",
                "rtx", "radeon", "processador", "ryzen", "intel core",
                "memoria ram", "ddr4", "ddr5"]
ENABLED_SITES = ["olx"]
SECONDHAND_SITES = {"olx"}
RETAIL_SITES = set()
DEAL_THRESHOLD = 0.80  # at least 20% below the observed asking-price median
STATS_WINDOW_DAYS = 30
MIN_SAMPLES_FOR_STATS = 4
TOP_N = 10  # cheapest per exact model/specification, not across unrelated parts
MIN_PRICE = 5.0
MAX_PRICE = 4000.0
MAX_PAGES_PER_QUERY = 10  # safety cap; report explicitly records capped searches
OLX_CATEGORY_ID = 5371  # OLX computer components; avoids phones/cars with GPU-like numbers
PAGE_SIZE = 40
REQUEST_DELAY_RANGE = (2.0, 5.0)
REQUEST_TIMEOUT = 25
USER_AGENT = "OLXComponentTracker/1.0 (personal price comparison)"
from pathlib import Path
ROOT = Path(__file__).resolve().parent
DB_PATH = str(ROOT / "gpu_tracker.db")  # retain the original database name
REPORTS_DIR = str(ROOT / "reports")
