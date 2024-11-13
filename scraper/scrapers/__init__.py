from .base import BaseScraper
from .bips import BIPsScraper
from .bitcoinops import BitcoinOpsScraper
from .bitcointranscripts import BitcoinTranscriptsScraper
from .github import GithubScraper
from .scrapy.scrapy_base import ScrapyScraper
from .scrapy.spider_base import BaseSpider
from .scrapy.bitcointalk import BitcoinTalkScraper

__all__ = [
    "BaseScraper",
    # github
    "GithubScraper",
    "BIPsScraper",
    "BitcoinOpsScraper",
    "BitcoinTranscriptsScraper",
    # scrapy
    "ScrapyScraper",
    "BaseSpider",
    "BitcoinTalkScraper",
]
