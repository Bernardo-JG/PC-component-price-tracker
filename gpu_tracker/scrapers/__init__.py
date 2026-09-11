from .vinted import VintedScraper
from .olx import OlxScraper
from .wallapop import WallapopScraper
from .pcdiga import PcdigaScraper
from .amazon import AmazonScraper

SCRAPERS = {
    "vinted": VintedScraper,
    "olx": OlxScraper,
    "wallapop": WallapopScraper,
    "pcdiga": PcdigaScraper,
    "amazon": AmazonScraper,
}
