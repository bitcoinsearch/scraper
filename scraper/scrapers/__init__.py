from .base import BaseScraper
from .bips import BIPsScraper
from .blips import BLIPsScraper
from .bitcoinops import BitcoinOpsScraper
from .bitcointranscripts import BitcoinTranscriptsScraper
from .pr_review_club import PRReviewClubScraper
from .github import GithubScraper
from .scrapy.scrapy_base import ScrapyScraper
from .scrapy.spider_base import BaseSpider
from .scrapy.bitcointalk import BitcoinTalkScraper

__all__ = [
    "BaseScraper",
    # github
    "GithubScraper",
    "BIPsScraper",
    "BLIPsScraper",
    "BitcoinOpsScraper",
    "BitcoinTranscriptsScraper",
    "PRReviewClubScraper",
    # scrapy
    "ScrapyScraper",
    "BaseSpider",
    "BitcoinTalkScraper",
]
