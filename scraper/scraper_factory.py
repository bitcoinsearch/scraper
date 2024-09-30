from loguru import logger

from scraper.scrapers import BaseScraper
from scraper.models import SourceConfig
from scraper.config import settings
from scraper.registry import output_registry, scraper_registry


class ScraperFactory:
    """
    The ScraperFactory is responsible for creating the appropriate scraper for each source:
    1. It looks up the appropriate scraper from the registry based on the source name.
    2. The selected output method is created from the output registry.

    This design allows for easy addition of new scrapers without modifying existing code.
    """

    @staticmethod
    def create_scraper(source: SourceConfig, output_type: str) -> BaseScraper:
        """
        Creates and returns an instance of the appropriate scraper for the given source.

        Args:
            source: The configuration for the source to be scraped
            output_type: The output handler for the scraped data

        Returns:
            BaseScraper: An instance of the appropriate scraper for the source
        """
        try:
            scraper_class = scraper_registry.get(source.name)

            # Create the output handler
            output_class = output_registry.get(output_type)
            output = output_class(
                index_name=settings.DEFAULT_INDEX,
                batch_size=settings.config.getint("batch_size", 100),
            )

            scraper = scraper_class(source, output)
            logger.debug(
                f"Scrapping {source.name} ({source.domain}) to {output.__class__.__name__} using {scraper.__class__.__name__}..."
            )
            return scraper
        except Exception as e:
            raise ValueError(
                f"Could not create scraper for source {source.name} ({source.domain}): {e}"
            )
