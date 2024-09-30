from abc import ABC, abstractmethod

from scraper.models import MetadataDocument, ScrapedDocument, SourceConfig
from scraper.outputs.abstract_output import AbstractOutput


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers in the system.

    This class defines the common interface and shared functionality
    for all concrete scraper implementations. It handles basic operations
    like interfacing with the output handler.

    Attributes:
        config (SourceConfig): Configuration for the scraper.
        output (AbstractOutput): Handler for outputting scraped data.
    """

    def __init__(
        self,
        config: SourceConfig,
        output: AbstractOutput,
    ):
        """
        Initialize the BaseScraper with configuration and output handler.

        Args:
            config: Configuration for the scraper.
            output (AbstractOutput): Handler for outputting scraped data.
        """
        self.config = config
        self.output = output

    @abstractmethod
    async def scrape(self):
        """
        Abstract method to be implemented by concrete scrapers.
        This method should contain the main scraping logic.

        """
        pass

    async def index_document(self, document: ScrapedDocument):
        """
        Index the scraped documents using the output handler.

        Args:
            documents (List[ScrapedDocument]): List of documents to index.
        """
        await self.output.index_document(document)

    async def run(self):
        async with self.output:
            await self.scrape()

    async def get_metadata(self, source: SourceConfig) -> MetadataDocument:
        """
        Retrieve metadata for a given source using the output handler.

        Args:
            source (SourceConfig): The source for which to retrieve metadata.

        Returns:
            MetadataDocument: The metadata for the specified source.
        """
        return await self.output.get_metadata(source)

    async def update_metadata(self, metadata: MetadataDocument):
        """
        Update metadata for the source using the output handler.

        Args:
            metadata (MetadataDocument): The new metadata to store.
        """
        await self.output.update_metadata(metadata)
