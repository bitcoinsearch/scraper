from pathlib import Path
from loguru import logger

from scrapy.crawler import CrawlerProcess
from scraper.config import get_project_root
from scraper.scrapers.base import BaseScraper
from scraper.scrapers.scrapy.spider_base import BaseSpider
from scraper.scrapers.scrapy.spider_config import SpiderConfig


class ScrapyScraper(BaseScraper):
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
        self.spider_config = self._load_configuration()

    def _load_configuration(self) -> SpiderConfig:
        """
        Load and validate spider configuration.

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration is invalid
        """
        config_path = self._get_config_path()
        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found for {self.config.name} at {config_path}. "
                f"Each scraper must have a configuration file."
            )

        try:
            config = SpiderConfig(str(config_path))
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            raise ValueError(f"Invalid configuration for {self.config.name}: {e}")

    def _get_config_path(self) -> Path:
        """Get the path to the source's configuration file."""
        return Path(
            get_project_root(),
            "scrapy_sources_configs",
            f"{self.config.name.lower()}.yaml",
        )

    async def scrape(self):
        """
        Start the scraping process.

        This method retrieves the appropriate spider class, adds it to the crawler process,
        and starts the crawling. It should be called to begin the scraping operation.
        """
        spider = self.get_spider_class()
        self.crawler_process.crawl(
            spider,
            scraper=self,
            source_config=self.config,  # Pass source config separately
            spider_config=self.spider_config,
        )
        self.crawler_process.start()

    def get_spider_class(self):
        """
        Return the spider class to be used by this scraper.
        By default, uses the BaseSpider.

        Override this method to provide a custom spider class that inherits
        from BaseSpider if source-specific logic is needed.
        """
        return BaseSpider
