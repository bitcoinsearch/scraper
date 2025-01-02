from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from loguru import logger

from scraper.models import RunStats, ScraperRunDocument, ScrapedDocument, SourceConfig
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
        self.resources_to_process = None
        self.total_documents_processed = 0
        self._error: Optional[str] = None
        self._success = True
        self._started_at: Optional[str] = None

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
        self._started_at = datetime.now().isoformat()
        async with self.output:
            try:
                await self.scrape()
            except Exception as e:
                self._success = False
                self._error = str(e)
                raise
            finally:
                await self.record_run()

    async def get_last_successful_run(self) -> Optional[ScraperRunDocument]:
        """
        Retrieve the most recent successful run for the source.
        """
        return await self.output.get_last_successful_run(self.config.name)

    async def record_run(self) -> None:
        """
        Record statistics for the current scraper run.
        """
        try:
            stats = RunStats(
                resources_to_process=self.resources_to_process,
                documents_indexed=self.total_documents_processed,
            )

            run_document = ScraperRunDocument(
                scraper=self.__class__.__name__,
                source=self.config.name,
                domain=str(self.config.domain),
                stats=stats,
                last_commit_hash=getattr(self, "current_commit_hash", None),
                started_at=self._started_at,
                success=self._success,
                error_message=self._error,
            )

            await self.output.record_run(run_document)
            logger.debug(
                f"Recorded run statistics: {run_document.model_dump(exclude_none=True)}"
            )

        except Exception as e:
            logger.error(f"Error recording run statistics: {e}")
