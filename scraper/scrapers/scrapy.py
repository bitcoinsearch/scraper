from abc import ABC, abstractmethod
import scrapy
from scrapy import signals
from twisted.internet import task, defer
from typing import List, Dict, Any, Optional, Generator
from bs4 import BeautifulSoup
from loguru import logger

from scraper.models import ScrapedDocument
from scrapy.crawler import CrawlerProcess
from scraper.config import SourceConfig
from scraper.scrapers.base import BaseScraper


class ScrapyBasedScraper(BaseScraper):
    """
    A base class for scrapers that use Scrapy.
    This class extends BaseScraper and provides the necessary setup for using Scrapy
    within the scraper framework.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crawler_process = CrawlerProcess(
            settings={
                "COOKIES_ENABLED": False,
                "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
                "DOWNLOAD_DELAY": 1,
            }
        )

    async def scrape(self):
        """
        Start the scraping process.

        This method retrieves the appropriate spider class, adds it to the crawler process,
        and starts the crawling. It should be called to begin the scraping operation.
        """
        spider = self.get_spider_class()
        self.crawler_process.crawl(spider, scraper=self, config=self.config)
        self.crawler_process.start()

    def get_spider_class(self):
        """Return the spider class to be used by this scraper."""
        raise NotImplementedError("Subclasses must implement get_spider_class()")


class BaseSpider(scrapy.Spider, ABC):
    """
    Abstract base spider that implements a three-level scraping pattern:
    1. Index pages (listing pages)
    2. Resource pages (individual resources)
    3. Items within resources

    This spider handles pagination at both index and resource levels.
    """

    def __init__(self, scraper: BaseScraper, config: SourceConfig, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scraper = scraper
        self.config = config
        self.test_resources = self.config.test_resources

        # Set up domains and start URLs
        self.allowed_domains = [config.domain.host]
        self.start_urls = self._get_start_urls()

        # Statistics
        self.total_items_scraped = 0
        self.total_items_queued = 0
        self.total_items_indexed = 0
        self.log_interval = 15  # Log status every 15 seconds

        logger.info(
            f"Initializing spider {self.name} in "
            f"{'test' if self.test_resources else 'full'} mode"
        )

    def _get_start_urls(self) -> List[str]:
        """Get start URLs based on configuration."""
        if self.test_resources:
            logger.info(f"Running in test mode with resources: {self.test_resources}")
            return self.test_resources
        return [str(self.config.url)]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(BaseSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_opened(self, spider):
        self.log_status_task = task.LoopingCall(self.log_status)
        self.log_status_task.start(self.log_interval)
        logger.info(f"Spider opened: {self.name}")

    def spider_closed(self, spider):
        if hasattr(self, "log_status_task") and self.log_status_task.running:
            self.log_status_task.stop()
        logger.info(f"Spider closed: {self.name}")

    def log_status(self):
        logger.info(
            f"Status for {self.name}: Scraped: {self.total_items_scraped}, "
            f"Queued: {self.total_items_queued}, Indexed: {self.total_items_indexed}"
        )

    def increment_scraped(self):
        self.total_items_scraped += 1
        self.total_items_queued += 1

    def increment_indexed(self):
        self.total_items_indexed += 1
        self.total_items_queued -= 1

    def parse(self, response) -> Generator:
        """
        Parse response based on mode (test or full).
        In test mode, treats all URLs as resource pages.
        In full mode, processes as index pages.
        """
        if self.test_resources:
            # In test mode, treat all URLs as resource pages
            yield from self.parse_resource(response)
        else:
            # In full mode, process index pages
            resource_links = self.get_resource_links(response)
            logger.info(f"Found {len(resource_links)} resource links")

            for link in resource_links:
                yield response.follow(link, callback=self.parse_resource)

            next_page = self.get_next_index_page(response)
            if next_page:
                logger.info("Following next index page")
                yield response.follow(next_page, self.parse)

    def parse_resource(self, response) -> Generator:
        """Parse a resource page containing individual items."""
        resource_id = self.get_resource_id(response)
        logger.debug(f"Parsing resource {resource_id}")

        soup = BeautifulSoup(response.text, "html.parser")
        items = self.get_items(soup)

        logger.debug(f"Found {len(items)} items in resource {resource_id}")

        for item in items:
            try:
                item_data = self.parse_item(item, response.url)
                if item_data:
                    document = ScrapedDocument(**item_data)
                    yield scrapy.Request(
                        url=item_data["url"],
                        callback=self.process_document,
                        cb_kwargs={"document": document},
                        dont_filter=True,
                    )
            except Exception as e:
                logger.error(f"Error processing item in resource {resource_id}: {e}")
                logger.exception("Full traceback:")

        if not self.test_resources:  # Only follow pagination in full mode
            next_page = self.get_next_resource_page(soup)
            if next_page:
                logger.debug(f"Moving to next page of resource {resource_id}")
                yield response.follow(next_page["href"], self.parse_resource)

    @abstractmethod
    def get_resource_links(self, response) -> List[Any]:
        """Extract resource links from the index page."""
        raise NotImplementedError

    @abstractmethod
    def get_next_index_page(self, response) -> Optional[str]:
        """Get the URL of the next index page."""
        raise NotImplementedError

    @abstractmethod
    def get_resource_id(self, response) -> str:
        """Extract the resource ID from the response."""
        raise NotImplementedError

    @abstractmethod
    def get_items(self, soup: BeautifulSoup) -> List[Any]:
        """Extract items from the resource page."""
        raise NotImplementedError

    @abstractmethod
    def get_next_resource_page(self, soup: BeautifulSoup) -> Optional[Any]:
        """Get the next page link for a resource."""
        raise NotImplementedError

    @abstractmethod
    def parse_item(self, item: Any, resource_url: str) -> Optional[Dict[str, Any]]:
        """Parse an individual item and return a dictionary of its data."""
        raise NotImplementedError

    @defer.inlineCallbacks
    def process_document(self, response, document: ScrapedDocument):
        """Process and index a document."""
        logger.info(f"Processing document: {document.id}")
        yield self.scraper.process_and_index_document(document)
        self.increment_indexed()
        logger.info(
            f"Indexed document: {document.id}. "
            f"Scraped: {self.total_items_scraped}, "
            f"Queued: {self.total_items_queued}, "
            f"Indexed: {self.total_items_indexed}"
        )
