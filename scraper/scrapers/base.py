from abc import ABC, abstractmethod

from loguru import logger

from scraper.config import SourceConfig
from scraper.models import MetadataDocument, ScrapedDocument
from scraper.outputs import AbstractOutput
from scraper.processors import ProcessorManager


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers in the system.

    This class defines the common interface and shared functionality
    for all concrete scraper implementations. It handles basic operations
    like interfacing with the output handler.
    """

    def __init__(
        self,
        config: SourceConfig,
        output: AbstractOutput,
        processor_manager: ProcessorManager,
    ):
        """
        Initialize the BaseScraper with configuration and output handler.

        Args:
            config (SourceConfig): Configuration for the scraper.
            output (AbstractOutput): Handler for outputting scraped data.
            processor_manager (ProcessorManager): Manager for processors.
        """
        self.config = config
        self.output = output
        self.processor_manager = processor_manager
        self.total_documents_processed = 0

    @abstractmethod
    async def scrape(self):
        """
        Abstract method to be implemented by concrete scrapers.
        This method should contain the main scraping logic.

        """
        pass

    async def process_and_index_document(self, document: ScrapedDocument):
        """
        Process a single document through the processor manager and index it.

        This method applies all registered processors to the document and then
        indexes the processed document using the output handler.

        Args:
            document (ScrapedDocument): The document to process and index.
        """
        processed_doc = await self.processor_manager.process_document(document)
        await self.output.index_document(processed_doc)
        self.total_documents_processed += 1
        logger.info(
            f"Processed post {processed_doc.id} by {processed_doc.authors}. Total documents processed: {self.total_documents_processed}"
        )

    async def run(self):
        """
        Run the scraper within the context of the output handler.

        This method sets up the output context and calls the scrape method.
        It ensures that the output handler is properly initialized and cleaned up,
        even if an exception occurs during scraping.
        """
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
