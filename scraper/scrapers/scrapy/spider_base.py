from abc import ABC
import json
from pathlib import Path
import re
from typing import Generator, List, Optional, Dict, Any, Set
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Tag
from loguru import logger

import scrapy
from scrapy import signals
from twisted.internet import task, defer
from scrapy.http import Response

from scraper.config import get_project_root
from scraper.models import ScrapedDocument
from scraper.scrapers.base import BaseScraper
from scraper.scrapers.scrapy.spider_config import SpiderConfig
from scraper.scrapers.scrapy.selector_types import ItemConfig
from scraper.scrapers.scrapy.selector_extractor import SelectorExtractor
from scraper.scrapers.utils import parse_standard_date_formats
from scraper.utils import slugify
from scraper.models import SourceConfig


class BaseSpider(scrapy.Spider, SelectorExtractor, ABC):
    name = "base_spider"
    """
    A configurable spider that uses YAML configuration files to define scraping behavior.
    Supports author filtering and differentiates between first and subsequent pages.
    Maintains thread context and generates URL-based IDs.

    This spider implements a three-level scraping pattern:
    1. Index pages (listing pages)
    2. Resource pages (individual resources)
    3. Items within resources

    The spider's behavior is primarily driven by configuration, with the ability to
    override methods for custom behavior when needed.
    """

    def __init__(
        self,
        scraper: BaseScraper,
        source_config: SourceConfig,
        spider_config: SpiderConfig,
        *args,
        **kwargs,
    ):
        """
        Initialize the spider with scraper instance and configurations.

        Args:
            scraper: The BaseScraper instance that created this spider
            source_config: The SourceConfig instance containing source metadata
            spider_config: The SpiderConfig instance containing scraping selectors
        """
        super().__init__(*args, **kwargs)
        self.scraper = scraper
        self.source_config = source_config
        self.spider_config = spider_config

        # Initialize spider settings from source config
        self.name = self.source_config.name.lower()
        self.allowed_domains = [str(self.source_config.domain.host)]
        self.test_resources = self.source_config.test_resources
        self.start_urls = self._get_start_urls()

        # Author filtering
        self.filter_by_author = self._should_filter_by_author()
        self.authors_of_interest = set(self._load_authors_of_interest())

        # Statistics
        self.total_items_scraped = 0
        self.total_items_queued = 0
        self.log_interval = 15

        logger.info(
            f"Initializing spider {self.name} in "
            f"{'test' if self.test_resources else 'full'} mode. "
            f"Author filtering: {'enabled' if self.filter_by_author else 'disabled'}"
        )

    def _should_filter_by_author(self) -> bool:
        """Determine if author filtering should be enabled."""
        return self.source_config.filter_by_author

    def _load_authors_of_interest(self) -> Set[str]:
        """
        Load and process the list of authors to track.
        Supports both direct configuration and loading from a JSON file.
        """
        authors = set()

        # Try loading from JSON file
        file_path = Path(get_project_root()) / "people_of_interest.json"
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            # Extract usernames based on source-specific key
            username_key = f"{self.name}_username"
            usernames = [
                person[username_key].lower()
                for person in data
                if username_key in person
            ]
            authors.update(usernames)

            logger.info(f"Loaded {len(authors)} authors of interest")

        except FileNotFoundError:
            logger.warning(f"Authors of interest file not found at {file_path}")
        except json.JSONDecodeError:
            logger.error(f"Error parsing authors of interest file at {file_path}")
        except Exception as e:
            logger.error(f"Error loading authors of interest: {e}")

        return authors

    def _get_start_urls(self) -> List[str]:
        """Get start URLs based on configuration or test mode."""
        if self.test_resources:
            logger.info(f"Running in test mode with resources: {self.test_resources}")
            return self.test_resources
        return [str(self.source_config.url)]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(BaseSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_opened(self, spider):
        """Initialize spider logging and monitoring."""
        self.log_status_task = task.LoopingCall(self.log_status)
        self.log_status_task.start(self.log_interval)
        logger.info(f"Spider opened: {self.name}")

    def spider_closed(self, spider):
        """Clean up resources when spider closes."""
        if hasattr(self, "log_status_task") and self.log_status_task.running:
            self.log_status_task.stop()
        logger.info(f"Spider closed: {self.name}")

    def log_status(self):
        """Log current scraping statistics."""
        logger.info(
            f"Status for {self.name}: Scraped: {self.total_items_scraped}, "
            f"Queued: {self.total_items_queued}, Indexed: {self.scraper.total_documents_processed}"
        )

    def parse(self, response: Response) -> Generator:
        """
        Main entry point for parsing responses.

        In test mode, treats all URLs as resource pages.
        In normal mode, starts with index page parsing.
        """
        if self.test_resources:
            yield from self.parse_resource(response)
        else:
            yield from self.parse_index(response)

    def parse_index(self, response: Response) -> Generator:
        """Parse index page to find resource links."""
        if not self.spider_config.scraping_config:
            raise ValueError("No scraping configuration found")

        soup = BeautifulSoup(response.text, "html.parser")
        item_selector = (
            self.spider_config.scraping_config.index_page.items.item_selector
        )
        resource_links = self._extract_links(soup, item_selector)
        logger.info(f"Found {len(resource_links)} resource links")

        for link in resource_links:
            yield response.follow(link, callback=self.parse_resource)

        # Handle pagination if configured
        if self.spider_config.scraping_config.index_page.next_page:
            next_page = self._extract_next_page(
                soup, self.spider_config.scraping_config.index_page.next_page
            )
            if next_page:
                logger.info("Following next index page")
                yield response.follow(next_page, self.parse_index)

    def parse_resource(
        self, response: Response, is_first_page: bool = True
    ) -> Generator:
        """
        Parse a resource page and its items.

        Args:
            response: The response to parse
            is_first_page: Whether this is the first page of the resource
        """
        if not self.spider_config.scraping_config:
            raise ValueError("No scraping configuration found")

        resource_config = self.spider_config.scraping_config.resource_page
        soup = BeautifulSoup(response.text, "html.parser")

        # Get the thread URL (resource URL without pagination parameters)
        thread_url = self._get_thread_url(response.url)

        # Extract items using configured selector
        items = self._extract_items(soup, resource_config.items.item_selector)
        logger.debug(f"Found {len(items)} items on page {response.url}")

        # Process items
        for index, item in enumerate(items):
            try:
                # First item is the original post only on the first page
                is_original_post = is_first_page and index == 0
                item_data = self._parse_item(
                    item,
                    response.url,
                    thread_url,
                    resource_config.items,
                    is_original_post,
                )

                if item_data:  # Skip items that failed to parse
                    document = ScrapedDocument(**item_data)
                    self.total_items_scraped += 1
                    yield scrapy.Request(
                        url=item_data["url"],
                        callback=self.process_document,
                        cb_kwargs={"document": document},
                        dont_filter=True,
                    )
            except Exception as e:
                logger.error(f"Error processing item {index} from {thread_url}: {e}")
                logger.exception("Full traceback:")

        # Handle pagination if configured
        if not self.test_resources and resource_config.next_page:
            next_page = self._extract_next_page(soup, resource_config.next_page)
            if next_page:
                logger.info("Following pagination")
                yield response.follow(
                    next_page,
                    callback=self.parse_resource,
                    cb_kwargs={"is_first_page": False},
                )

    def _get_thread_url(self, url: str) -> str:
        """
        Extract the base thread URL by removing pagination parameters.
        Override this method for source-specific URL cleaning if needed.
        """
        # Default implementation: remove common pagination parameters
        parsed = urlparse(url)

        # Remove common pagination parameters
        params = parsed.query.split("&")
        clean_params = []

        pagination_params = {"page", "p", "start", "msg", "pagination"}
        for param in params:
            if "=" in param:
                name = param.split("=")[0].lower()
                if name not in pagination_params:
                    clean_params.append(param)

        # Reconstruct URL without pagination parameters
        clean_query = "&".join(clean_params)
        thread_url = parsed._replace(query=clean_query).geturl()

        return thread_url

    def _parse_item(
        self,
        item: Tag,
        current_url: str,
        thread_url: str,
        item_config: ItemConfig,
        is_original_post: bool,
    ) -> Optional[Dict[str, Any]]:
        """Parse an individual item using configured selectors."""
        try:
            author = None
            if item_config.author:
                author = self._extract_field(item, item_config.author)

            if not author and self.source_config.default_author:
                author = self.source_config.default_author

            if self.filter_by_author and not author:
                return None

            if self.filter_by_author and author.lower() not in self.authors_of_interest:
                return None

            # Handle URL extraction based on configuration
            item_url = None
            if item_config.url:
                # Try to extract URL using selector
                item_url = self._extract_field(item, item_config.url)

            # If URL selector is not configured or extraction failed
            if not item_url:
                # For single-item pages (multiple=False), use the response URL
                if not item_config.item_selector.multiple:
                    item_url = current_url
                else:
                    logger.warning(
                        "Could not extract item URL and page has multiple items"
                    )
                    return None

            # Build item data
            data = {
                "id": self.generate_id_from_url(item_url),
                "title": self._extract_field(item, item_config.title),
                "body": self._extract_field(item, item_config.content)
                or "",  # We currently remove quotes from BitcoinTalk forum posts. Empty string covers an edge case with BitcoinTalk forum posts where the post only contains quotes.
                "body_type": "raw",
                "url": item_url,
                "domain": str(self.source_config.domain),
                "authors": [author] if author else None,
                "type": "original_post" if is_original_post else "reply",
            }

            # Only set thread_url for multi-item resources
            if item_config.item_selector.multiple:
                data["thread_url"] = thread_url

            # Extract date
            if item_config.date:
                date_str = self._extract_field(item, item_config.date)
                if date_str:
                    data["created_at"] = self.parse_date(date_str)

            return data

        except Exception as e:
            logger.error(f"Error parsing item: {e}")
            logger.exception("Full traceback:")
            return None

    def generate_id_from_url(self, url: str) -> str:
        """
        Generate a unique ID from the item's URL.
        Override this method for source-specific ID generation if needed.
        """
        # Default implementation: use domain name and unique part of URL
        parsed = urlparse(url)

        # Extract unique identifier from URL
        # Look for common patterns like post IDs, message IDs, etc.
        patterns = [
            r"msg(\d+)",  # Message ID
            r"post-(\d+)",  # Post ID
            r"#(\d+)",  # Fragment ID
            r"[#/]([a-zA-Z0-9-]+)$",  # General ending identifier
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                identifier = match.group(1)
                return f"{self.name}-{identifier}"

        # Fallback: use slugified last part of path
        path_parts = parsed.path.strip("/").split("/")
        if path_parts:
            identifier = slugify(path_parts[-1])
            return f"{self.name}-{identifier}"

        # Last resort: use hash of full URL
        return f"{self.name}-{hash(url)}"

    def parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse date string to ISO format. Tries default parsing methods first,
        then falls back to subclass implementation if they fail.

        Override this method in subclasses to handle custom date formats.
        """
        if not date_str:
            return None

        # Try standard date formats
        parsed_date = parse_standard_date_formats(date_str)
        if parsed_date:
            return parsed_date

        # If default parsing fails, raise NotImplementedError
        raise NotImplementedError(
            f"Could not parse date format: {date_str}. "
            "Implement parse_date in a subclass to handle this format."
        )

    @defer.inlineCallbacks
    def process_document(self, response: Response, document: ScrapedDocument):
        """Process and index a document using the parent scraper."""
        logger.info(f"Processing document: {document.id}")
        yield self.scraper.process_and_index_document(document)
